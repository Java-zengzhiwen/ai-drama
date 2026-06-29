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
