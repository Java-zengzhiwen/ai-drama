import sqlite3

import pytest

import ai_drama_runtime.shot_prompt_migration as migration
from ai_drama_runtime.shot_prompt_migration import (
    APPROVAL_ACTIONS,
    REVISION_APPROVAL_STATUSES,
    preview_phase3_store_migration,
)
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import (
    create_phase2_legacy_db,
    index_sql,
    normalized_schema_snapshot,
    seed_phase3_store,
    snapshot_database,
    table_columns,
    table_sql,
)
from tests.test_storyboard_legacy_migration import (
    _create_planning_baseline_legacy_db as create_real_phase2_legacy_db,
)


EXPECTED_PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES = (
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)
EXPECTED_REVISION_OUTPUT_LOGICAL_TYPES = (
    "rendered_positive_prompt",
    "rendered_negative_prompt",
    "rendered_markdown",
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)


def test_phase3a_migration_exports_only_owned_schema_constants():
    assert (
        migration.PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
        == EXPECTED_PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
    )
    assert (
        migration.REVISION_OUTPUT_LOGICAL_TYPES
        == EXPECTED_REVISION_OUTPUT_LOGICAL_TYPES
    )
    review_exports = [name for name in vars(migration) if name.startswith("REVIEW_")]
    assert review_exports == []


def test_phase3a_support_creates_phase2_legacy_database(tmp_path):
    db_path = tmp_path / "runtime.db"
    real_db_path = tmp_path / "real-runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)
    create_real_phase2_legacy_db(real_db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    real_conn = sqlite3.connect(real_db_path)
    real_conn.row_factory = sqlite3.Row
    try:
        artifact_columns = set(table_columns(conn, "artifacts"))
        assert {
            "artifact_id",
            "artifact_type",
            "project_id",
            "chapter_id",
            "created_at",
        } <= artifact_columns
        assert "business_key_type" not in artifact_columns
        assert "business_key_value" not in artifact_columns
        snapshot = snapshot_database(conn)
        assert snapshot["tables"]["artifacts"]["row_count"] == 1
        assert snapshot["foreign_key_check"] == []
        assert snapshot["transient_tables"] == []
        assert normalized_schema_snapshot(conn) == normalized_schema_snapshot(real_conn)
    finally:
        conn.close()
        real_conn.close()

    with RuntimeStore(db_path, objects_root) as store:
        assert store.get_revision("legacy-revision").revision_id == "legacy-revision"


def test_phase3_preview_reports_each_contract_check_without_mutation(tmp_path):
    db_path = tmp_path / "runtime.db"
    create_phase2_legacy_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    before = snapshot_database(conn)
    conn.close()

    preview = preview_phase3_store_migration(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    after = snapshot_database(conn)
    conn.close()

    assert before == after
    assert preview["status"] == "NEEDS_MIGRATION"
    assert preview["checks"]["artifact_business_key"]["status"] == "MISSING"
    assert preview["checks"]["revision_outputs_check"]["status"] == "MISSING"
    assert preview["checks"]["revision_status_check"]["status"] == "MISSING"
    assert preview["checks"]["approval_action_check"]["status"] == "MISSING"
    assert preview["checks"]["approval_evidence_columns"]["status"] == "MISSING"
    assert "review_tables" not in preview["checks"]
    assert "review_indexes" not in preview["checks"]


def test_phase3_preview_reports_fresh_a1_store_current(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root):
        pass

    preview = preview_phase3_store_migration(db_path)

    assert preview["status"] == "CURRENT"
    assert set(preview["checks"]) == {
        "artifact_business_key",
        "revision_outputs_check",
        "revision_status_check",
        "approval_action_check",
        "approval_evidence_columns",
        "foreign_key_check",
    }
    assert all(item["status"] == "OK" for item in preview["checks"].values())


def test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        first = store.ensure_shot_prompt_artifact(
            project_id="project-1",
            chapter_id="chapter-1",
            source_storyboard_revision_id="storyboard-revision-1",
        )
        second = store.ensure_shot_prompt_artifact(
            project_id="project-1",
            chapter_id="chapter-1",
            source_storyboard_revision_id="storyboard-revision-1",
        )
        assert first["artifact_id"] == second["artifact_id"]
        assert first["artifact_id"] != "storyboard-revision-1"
        assert (
            store.artifact_by_business_key(
                "shot_prompt_set",
                "source_storyboard_revision_id",
                "storyboard-revision-1",
            )["artifact_id"]
            == first["artifact_id"]
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO artifacts
                (artifact_id, artifact_type, project_id, chapter_id,
                 business_key_type, business_key_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "dup",
                    "shot_prompt_set",
                    "project-1",
                    "chapter-1",
                    "source_storyboard_revision_id",
                    "storyboard-revision-1",
                    "2026-07-03T00:00:00Z",
                ),
            )
        assert {"business_key_type", "business_key_value"} <= set(
            table_columns(store.conn, "artifacts")
        )
        artifact_index = index_sql(store.conn, "artifacts")[
            "one_shot_prompt_set_per_source_storyboard_revision"
        ]
        assert artifact_index["columns"] == [
            "artifact_type",
            "business_key_type",
            "business_key_value",
        ]
        assert {
            "artifact_type",
            "'shot_prompt_set'",
            "business_key_type",
            "'source_storyboard_revision_id'",
        } <= set(artifact_index["predicate_tokens"])


def test_revision_outputs_accept_exact_logical_types_and_preserve_schema(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        object_id = store.write_text_object("{}")
        revision = store.get_revision("legacy-revision")
        rows = [
            {
                "revision_id": revision.revision_id,
                "logical_type": logical_type,
                "object_id": object_id,
                "content_hash": object_id,
                "media_type": "application/json",
                "generator": "test",
                "generator_version": "1.0.0",
            }
            for logical_type in EXPECTED_PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
        ]
        inserted = store.insert_revision_outputs_transaction(rows)
        assert [item.logical_type for item in inserted] == list(
            EXPECTED_PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
        )
        with pytest.raises(sqlite3.IntegrityError):
            store.insert_revision_outputs_transaction([dict(rows[0], logical_type="unknown")])
        sql = table_sql(store.conn, "revision_outputs")
        for logical_type in EXPECTED_REVISION_OUTPUT_LOGICAL_TYPES:
            assert logical_type in sql
        indexes = index_sql(store.conn, "revision_outputs")
        assert "revision_outputs_content_hash_idx" in indexes
        assert "revision_outputs_object_id_idx" in indexes


def test_revision_status_check_preserves_schema_and_approved_index(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        for status in REVISION_APPROVAL_STATUSES:
            store.conn.execute(
                "UPDATE revisions SET approval_status = ? WHERE revision_id = ?",
                (status, "legacy-revision"),
            )
            store.conn.commit()
            assert store.get_revision("legacy-revision").approval_status == status
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                "UPDATE revisions SET approval_status = 'unknown' "
                "WHERE revision_id = 'legacy-revision'"
            )
        sql = table_sql(store.conn, "revisions")
        assert "approval_status TEXT NOT NULL CHECK" in sql
        assert "FOREIGN KEY(run_id) REFERENCES runs(run_id)" in sql
        approved_index = index_sql(store.conn, "revisions")["one_current_approved_revision"]
        assert approved_index["columns"] == ["artifact_id"]
        assert {"approval_status", "'approved'"} <= set(approved_index["predicate_tokens"])


def test_approval_actions_accept_old_and_phase3_values_only(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    with RuntimeStore(db_path, objects_root) as store:
        seed_phase3_store(store)
        for action in APPROVAL_ACTIONS:
            store.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "record-" + action,
                    "legacy-revision",
                    "artifact-1",
                    action,
                    "tester",
                    "",
                    "2026-07-03T00:00:00Z",
                ),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES ('bad', 'legacy-revision', 'artifact-1', 'unknown', 'tester', '',
                        '2026-07-03T00:00:00Z')
                """
            )
        assert "shot_prompt_approval_revoked" in table_sql(store.conn, "approval_records")
