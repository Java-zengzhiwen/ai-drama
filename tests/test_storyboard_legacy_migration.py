import hashlib
import sqlite3
from pathlib import Path

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService, WorkflowGateError
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import CONTENT_PROFILE, parse_canonical_json


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_LEGACY_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.1.0"
SCRIPT_ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"), repo_root=REPO_ROOT)


def _revision_output_columns(store):
    return {row["name"]: row for row in store.conn.execute("PRAGMA table_info(revision_outputs)").fetchall()}


def _export_columns(store):
    return {row["name"]: row for row in store.conn.execute("PRAGMA table_info(export_records)").fetchall()}


def _legacy_storyboard(service):
    script = service.run_acceptance(load_skill_package(SCRIPT_SKILL_ROOT), SCRIPT_ACCEPTANCE_ROOT, "mock", "mock-script")
    service.approve_revision(script.revision.revision_id, "tester")
    storyboard = service.run_storyboard(
        load_skill_package(STORYBOARD_LEGACY_SKILL_ROOT),
        script.revision.revision_id,
        "mock",
        "mock-storyboard-v1",
    )
    service.approve_revision(storyboard.revision.revision_id, "tester")
    return storyboard.revision


def test_legacy_migration_preview_writes_candidate_without_revision(tmp_path):
    with _service(tmp_path) as service:
        legacy = _legacy_storyboard(service)
        before = [item.revision_id for item in service.store.revisions_for_artifact(legacy.artifact_id)]

        preview = service.preview_legacy_storyboard_migration(legacy.revision_id, tmp_path / "preview")

        after = [item.revision_id for item in service.store.revisions_for_artifact(legacy.artifact_id)]
        assert after == before
        assert preview["status"] == "PREVIEW"
        assert preview["candidate_hash"]
        assert Path(preview["canonical_candidate_path"]).exists()
        assert Path(preview["rendered_markdown_path"]).exists()


def test_legacy_migration_confirm_creates_pending_canonical_revision_same_artifact(tmp_path):
    with _service(tmp_path) as service:
        legacy = _legacy_storyboard(service)
        approved_before = service.current_approved(legacy.artifact_id).revision_id
        legacy_bytes_before = service.store.read_text(legacy.content_object_id)
        preview = service.preview_legacy_storyboard_migration(legacy.revision_id, tmp_path / "preview")

        result = service.confirm_legacy_storyboard_migration(
            legacy.revision_id,
            preview["candidate_hash"],
            tmp_path / "confirm",
        )

        revision = service.store.get_revision(result["revision_id"])
        assert result["status"] == "PENDING_CANONICAL_REVISION"
        assert revision.artifact_id == legacy.artifact_id
        assert revision.content_profile == CONTENT_PROFILE
        assert revision.derivation_type == "legacy_migration"
        assert revision.approval_status == "pending"
        assert service.current_approved(legacy.artifact_id).revision_id == approved_before
        assert service.store.latest_approval(revision.revision_id) is None
        assert service.store.read_text(legacy.content_object_id) == legacy_bytes_before
        canonical = parse_canonical_json(service.store.read_text(revision.content_object_id))
        assert canonical["source"]["script_revision_id"] == service.revision_source_revision_id(legacy.revision_id)


def test_legacy_migration_requires_matching_candidate_hash(tmp_path):
    with _service(tmp_path) as service:
        legacy = _legacy_storyboard(service)
        service.preview_legacy_storyboard_migration(legacy.revision_id, tmp_path / "preview")

        with pytest.raises(WorkflowGateError) as exc:
            service.confirm_legacy_storyboard_migration(legacy.revision_id, "0" * 64, tmp_path / "confirm")

        assert exc.value.code == "LEGACY_MIGRATION_REQUIRES_REVIEW"


def test_legacy_migration_fails_closed_when_required_legacy_fields_are_missing(tmp_path):
    with _service(tmp_path) as service:
        legacy = _legacy_storyboard(service)
        incomplete = service.store.write_text_object("# Storyboard\n\n## 场次：1-1\n\n### 镜头 1\n- duration_seconds: 8\n")
        broken = service.store.insert_revision(
            artifact_id=legacy.artifact_id,
            artifact_type="storyboard",
            project_id=legacy.project_id,
            chapter_id=legacy.chapter_id,
            run_id=legacy.run_id,
            skill_id=legacy.skill_id,
            skill_version=legacy.skill_version,
            skill_package_hash=legacy.skill_package_hash,
            runtime_provider="test",
            runtime_model="test",
            content_object_id=incomplete,
            content_hash="incomplete",
            raw_response_object_id=incomplete,
            parser_version=legacy.parser_version,
            content_profile="storyboard-markdown-mvp-v1",
        )
        dep = service.store.revision_dependencies(legacy.revision_id)[0]
        service.store.insert_revision_dependency(
            child_revision_id=broken.revision_id,
            parent_revision_id=dep.parent_revision_id,
            relation_type=dep.relation_type,
            parent_content_hash=dep.parent_content_hash,
            parent_approval_record_id=dep.parent_approval_record_id,
        )

        with pytest.raises(WorkflowGateError) as exc:
            service.preview_legacy_storyboard_migration(broken.revision_id, tmp_path / "preview")

        assert exc.value.code == "LEGACY_MIGRATION_REQUIRES_REVIEW"


def test_revision_outputs_schema_matches_frozen_ddl(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        columns = _revision_output_columns(store)
        assert list(columns) == [
            "revision_output_id",
            "revision_id",
            "logical_type",
            "object_id",
            "content_hash",
            "media_type",
            "generator",
            "generator_version",
            "created_at",
        ]
        assert columns["revision_output_id"]["pk"] == 1
        assert columns["revision_id"]["notnull"] == 1
        assert columns["logical_type"]["notnull"] == 1
        assert columns["object_id"]["notnull"] == 1
        assert columns["content_hash"]["notnull"] == 1

        table_sql = store.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'revision_outputs'"
        ).fetchone()["sql"]
        assert "logical_type IN ('rendered_positive_prompt', 'rendered_negative_prompt', 'rendered_markdown', 'bundle_manifest')" in table_sql

        index_names = {
            row["name"]
            for row in store.conn.execute("SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'revision_outputs'")
        }
        assert "sqlite_autoindex_revision_outputs_1" in index_names
        assert "sqlite_autoindex_revision_outputs_2" in index_names
        assert "revision_outputs_content_hash_idx" in index_names
        assert "revision_outputs_object_id_idx" in index_names
        foreign_keys = [dict(row) for row in store.conn.execute("PRAGMA foreign_key_list(revision_outputs)").fetchall()]
        assert foreign_keys == [
            {
                "id": 0,
                "seq": 0,
                "table": "revisions",
                "from": "revision_id",
                "to": "revision_id",
                "on_update": "NO ACTION",
                "on_delete": "RESTRICT",
                "match": "NONE",
            }
        ]


def test_revision_outputs_public_api_is_append_only(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        data = b"exact markdown bytes"
        object_id = store.write_bytes_object(data)
        assert object_id == hashlib.sha256(data).hexdigest()
        assert store.read_bytes_object(object_id) == data

        revision = _insert_minimal_revision(store, content_object_id=object_id, content_hash=object_id)
        records = store.insert_revision_outputs_transaction(
            [
                {
                    "revision_id": revision.revision_id,
                    "logical_type": "rendered_markdown",
                    "object_id": object_id,
                    "content_hash": object_id,
                    "media_type": "text/markdown",
                    "generator": "storyboard-canonical-markdown-renderer",
                    "generator_version": "1.0.0",
                }
            ]
        )

        assert len(records) == 1
        assert records[0].revision_output_id
        assert records[0].content_hash == object_id
        assert store.get_revision_output(revision.revision_id, "rendered_markdown") == records[0]
        assert store.revision_outputs(revision.revision_id) == records
        with pytest.raises(sqlite3.IntegrityError):
            store.insert_revision_outputs_transaction(
                [
                    {
                        "revision_id": revision.revision_id,
                        "logical_type": "rendered_markdown",
                        "object_id": object_id,
                        "content_hash": object_id,
                        "media_type": "text/markdown",
                        "generator": "storyboard-canonical-markdown-renderer",
                        "generator_version": "1.0.0",
                    }
                ]
            )
        public_methods = {name for name in dir(store) if "revision_output" in name}
        assert "insert_revision_outputs_transaction" in public_methods
        assert "revision_outputs" in public_methods
        assert "get_revision_output" in public_methods
        assert not any(name.startswith("update_revision_output") for name in public_methods)
        assert not any(name.startswith("delete_revision_output") for name in public_methods)
        assert not any(name.startswith("upsert_revision_output") for name in public_methods)


def test_export_records_legacy_rows_receive_frozen_defaults(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        object_id = store.write_text_object("legacy content")
        revision = _insert_minimal_revision(store, content_object_id=object_id, content_hash=object_id)
        export = store.record_export(
            artifact_id=revision.artifact_id,
            revision_id=revision.revision_id,
            run_id=revision.run_id,
            content_hash=revision.content_hash,
            destination=str(tmp_path / "legacy-export.md"),
            provenance_object_id=object_id,
        )

        assert export.export_kind == "legacy_single"
        assert export.diagnostic_only is False
        assert export.not_an_execution_package is True
        assert export.execution_ready is False
        assert export.freshness_status == ""
        assert export.bundle_manifest_hash == ""
        assert export.error_code == ""
        assert store.get_export_record(export.export_id) == export

        columns = _export_columns(store)
        assert "status" not in columns
        assert columns["export_kind"]["dflt_value"] == "'legacy_single'"
        assert columns["freshness_status"]["dflt_value"] == "''"
        assert columns["diagnostic_only"]["dflt_value"] == "0"
        assert columns["not_an_execution_package"]["dflt_value"] == "1"
        assert columns["execution_ready"]["dflt_value"] == "0"
        assert columns["bundle_manifest_hash"]["dflt_value"] == "''"
        assert columns["error_code"]["dflt_value"] == "''"


def test_phase2_migration_replay_is_idempotent(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    _create_planning_baseline_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        first_export = store.get_export_record("legacy-export")
        first_revision = store.get_revision("legacy-revision")
        first_columns = sorted(_export_columns(store))
        assert sorted(_revision_output_columns(store)) == [
            "content_hash",
            "created_at",
            "generator",
            "generator_version",
            "logical_type",
            "media_type",
            "object_id",
            "revision_id",
            "revision_output_id",
        ]
        assert first_revision.content_hash == "legacy-content-hash"
        assert first_export.export_kind == "legacy_single"
        assert first_export.not_an_execution_package is True

    with RuntimeStore(db_path, objects_root) as store:
        second_export = store.get_export_record("legacy-export")
        second_revision = store.get_revision("legacy-revision")
        second_columns = sorted(_export_columns(store))
        assert second_revision == first_revision
        assert second_export == first_export
        assert second_columns == first_columns


def _insert_minimal_revision(store, *, content_object_id, content_hash):
    store.ensure_artifact("artifact-1", "storyboard", "project-1", "chapter-1")
    run = store.create_run(
        run_id="run-1",
        artifact_id="artifact-1",
        project_id="project-1",
        chapter_id="chapter-1",
        skill_id="ai-drama-storyboard-design-skill",
        skill_version="v0.2.0",
        skill_hash="skill-hash",
        runtime="test-runtime",
        provider="mock",
        model="mock",
        status="COMPLETED",
        request_object_id=content_object_id,
        response_object_id=content_object_id,
        input_hash=content_hash,
    )
    return store.insert_revision(
        revision_id="legacy-revision",
        artifact_id="artifact-1",
        artifact_type="storyboard",
        project_id="project-1",
        chapter_id="chapter-1",
        run_id=run.run_id,
        skill_id="ai-drama-storyboard-design-skill",
        skill_version="v0.2.0",
        skill_package_hash="skill-hash",
        runtime_provider="mock",
        runtime_model="mock",
        content_object_id=content_object_id,
        content_hash=content_hash,
        raw_response_object_id=content_object_id,
        parser_version="storyboard-canonical-json-v1",
        content_profile=CONTENT_PROFILE,
    )


def _create_planning_baseline_legacy_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE artifacts (
          artifact_id TEXT PRIMARY KEY,
          artifact_type TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE runs (
          run_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          skill_id TEXT NOT NULL,
          skill_version TEXT NOT NULL,
          skill_hash TEXT NOT NULL,
          runtime TEXT NOT NULL,
          provider TEXT NOT NULL,
          model TEXT NOT NULL,
          status TEXT NOT NULL,
          request_object_id TEXT NOT NULL,
          response_object_id TEXT NOT NULL,
          input_hash TEXT NOT NULL,
          request_hash TEXT NOT NULL,
          usage_status TEXT NOT NULL,
          prompt_tokens INTEGER NOT NULL,
          completion_tokens INTEGER NOT NULL,
          total_tokens INTEGER NOT NULL,
          usage_raw_object_id TEXT NOT NULL,
          error_code TEXT NOT NULL,
          error_message TEXT NOT NULL,
          started_at TEXT NOT NULL,
          completed_at TEXT NOT NULL,
          duration_ms INTEGER NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE revisions (
          revision_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          artifact_type TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          run_id TEXT NOT NULL,
          skill_id TEXT NOT NULL,
          skill_version TEXT NOT NULL,
          skill_package_hash TEXT NOT NULL,
          runtime_provider TEXT NOT NULL,
          runtime_model TEXT NOT NULL,
          number INTEGER NOT NULL,
          content_object_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          raw_response_object_id TEXT NOT NULL,
          parser_version TEXT NOT NULL,
          content_profile TEXT NOT NULL DEFAULT '',
          derivation_type TEXT NOT NULL DEFAULT 'model_generation',
          supersedes_revision_id TEXT NOT NULL,
          approval_status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        CREATE TABLE approval_records (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id TEXT NOT NULL UNIQUE,
          revision_id TEXT NOT NULL,
          artifact_id TEXT NOT NULL,
          action TEXT NOT NULL,
          reviewer TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        );
        CREATE TABLE export_records (
          export_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          revision_id TEXT NOT NULL,
          run_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          destination TEXT NOT NULL,
          provenance_object_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        );
        CREATE TABLE validation_results (
          validation_id TEXT PRIMARY KEY,
          revision_id TEXT NOT NULL,
          validator_id TEXT NOT NULL,
          validator_name TEXT NOT NULL,
          status TEXT NOT NULL,
          required INTEGER NOT NULL,
          exit_code INTEGER NOT NULL,
          error_code TEXT NOT NULL,
          duration_ms INTEGER NOT NULL,
          stdout_object_id TEXT NOT NULL,
          stderr_object_id TEXT NOT NULL,
          report_object_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        );
        CREATE TABLE revision_dependencies (
          child_revision_id TEXT NOT NULL,
          parent_revision_id TEXT NOT NULL,
          relation_type TEXT NOT NULL,
          parent_content_hash TEXT NOT NULL,
          parent_approval_record_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          PRIMARY KEY(child_revision_id, parent_revision_id, relation_type),
          FOREIGN KEY(child_revision_id) REFERENCES revisions(revision_id),
          FOREIGN KEY(parent_revision_id) REFERENCES revisions(revision_id)
        );
        CREATE TABLE workflow_gate_records (
          gate_id TEXT PRIMARY KEY,
          run_id TEXT NOT NULL,
          target_skill_id TEXT NOT NULL,
          target_skill_version TEXT NOT NULL,
          target_artifact_id TEXT NOT NULL,
          source_revision_id TEXT NOT NULL,
          request_reference TEXT NOT NULL,
          error_code TEXT NOT NULL,
          error_message TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX one_current_approved_revision
          ON revisions(artifact_id)
          WHERE approval_status = 'approved';
        INSERT INTO artifacts VALUES ('artifact-1', 'storyboard', 'project-1', 'chapter-1', '2026-06-30T00:00:00Z');
        INSERT INTO runs VALUES (
          'run-1', 'artifact-1', 'project-1', 'chapter-1',
          'ai-drama-storyboard-design-skill', 'v0.2.0', 'skill-hash',
          'test-runtime', 'mock', 'mock', 'COMPLETED',
          'request-object', 'response-object', 'input-hash', 'request-hash',
          'NOT_PROVIDED', 0, 0, 0, '', '', '',
          '2026-06-30T00:00:00Z', '2026-06-30T00:00:00Z', 0, '2026-06-30T00:00:00Z'
        );
        INSERT INTO revisions VALUES (
          'legacy-revision', 'artifact-1', 'storyboard', 'project-1', 'chapter-1',
          'run-1', 'ai-drama-storyboard-design-skill', 'v0.2.0', 'skill-hash',
          'mock', 'mock', 1, 'content-object', 'legacy-content-hash',
          'response-object', 'storyboard-canonical-json-v1',
          'storyboard-canonical-v1', 'model_generation', '', 'pending',
          '2026-06-30T00:00:00Z'
        );
        INSERT INTO export_records VALUES (
          'legacy-export', 'artifact-1', 'legacy-revision', 'run-1',
          'legacy-content-hash', '/tmp/legacy-export.md', 'provenance-object',
          '2026-06-30T00:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()
