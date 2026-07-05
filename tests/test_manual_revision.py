import json
from pathlib import Path

import pytest

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.storyboard_canonical import CONTENT_PROFILE, parse_canonical_json


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.2.1"
SCRIPT_ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"), repo_root=REPO_ROOT)


def _generated_script_revision(service):
    return service.run_acceptance(
        load_skill_package(SCRIPT_SKILL_ROOT),
        SCRIPT_ACCEPTANCE_ROOT,
        "mock",
        "mock-script",
    ).revision


def _generated_storyboard_revision(service):
    script = _generated_script_revision(service)
    service.approve_revision(script.revision_id, "tester")
    return service.run_storyboard(
        load_skill_package(STORYBOARD_SKILL_ROOT),
        script.revision_id,
        "mock",
        "mock-storyboard-canonical-v1",
    ).revision


def test_manual_revision_supersedes_generated_script_revision(tmp_path):
    with _service(tmp_path) as service:
        generated = _generated_script_revision(service)

        edited = service.create_manual_revision(
            source_revision_id=generated.revision_id,
            content="# 第一场\n修改后的剧本",
            actor="local-user",
        )

        assert edited.artifact_id == generated.artifact_id
        assert edited.derivation_type == "manual_edit"
        assert edited.supersedes_revision_id == generated.revision_id
        assert edited.number == generated.number + 1
        assert edited.approval_status == "pending"
        assert service.store.read_text(edited.content_object_id) == "# 第一场\n修改后的剧本"


def test_manual_storyboard_revision_requires_valid_canonical_json(tmp_path):
    with _service(tmp_path) as service:
        generated = _generated_storyboard_revision(service)

        with pytest.raises(ValueError):
            service.create_manual_revision(
                source_revision_id=generated.revision_id,
                content='{"schema_version":"storyboard-canonical-v1"}',
                actor="local-user",
            )


def test_manual_storyboard_revision_uses_canonical_hash(tmp_path):
    with _service(tmp_path) as service:
        generated = _generated_storyboard_revision(service)
        canonical = parse_canonical_json(service.store.read_text(generated.content_object_id))
        canonical["shots"][0]["visual_composition"]["subject_focus"] = "手工修改后的主体焦点"
        content = json.dumps(canonical, ensure_ascii=False, sort_keys=True)

        edited = service.create_manual_revision(
            source_revision_id=generated.revision_id,
            content=content,
            actor="local-user",
        )

        assert edited.content_profile == CONTENT_PROFILE
        assert edited.content_hash != generated.content_hash
        assert edited.derivation_type == "manual_edit"
        assert service.revision_source_revision_id(edited.revision_id) == service.revision_source_revision_id(
            generated.revision_id
        )
        assert service.revision_source_approval_record(edited.revision_id) == service.revision_source_approval_record(
            generated.revision_id
        )


def test_manual_storyboard_revision_rejects_source_metadata_mismatch(tmp_path):
    with _service(tmp_path) as service:
        generated = _generated_storyboard_revision(service)
        canonical = parse_canonical_json(service.store.read_text(generated.content_object_id))
        canonical["source"]["script_revision_id"] = "fake-script-revision"

        with pytest.raises(ValueError):
            service.create_manual_revision(
                source_revision_id=generated.revision_id,
                content=json.dumps(canonical, ensure_ascii=False, sort_keys=True),
                actor="local-user",
            )
