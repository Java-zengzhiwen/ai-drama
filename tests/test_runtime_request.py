from pathlib import Path
import json
import shutil

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.request import build_runtime_request
from ai_drama_runtime.runtime import RuntimeErrorBase
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"


def test_normalized_request_contains_skill_context_and_excludes_reference_and_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_API_KEY", "secret-key")
    package = load_skill_package(SKILL_ROOT)
    request = build_runtime_request(package, ACCEPTANCE_ROOT, "mock", "mock-model", timeout_seconds=31)
    payload = request.to_dict()
    serialized = request.to_json()

    assert payload["request_format_version"]
    assert payload["skill"]["execution_profile"] == "markdown-script-mvp-v1"
    assert payload["skill_instruction"]["relative_path"] == "SKILL.md"
    assert "AI Drama Script Adaptation Skill" in payload["skill_instruction"]["content"]
    assert {item["relative_path"] for item in payload["context_files"]} >= {
        "references/adaptation-rules.md",
        "contracts/script-revision-presentation-contract-v2.md",
    }
    assert {item["logical_type"] for item in payload["inputs"]} == {
        "source_chapter",
        "series_canon",
        "characters",
        "production_brief",
    }
    assert "approved-script.md" not in serialized
    assert "secret-key" not in serialized
    assert request.sha256 == build_runtime_request(package, ACCEPTANCE_ROOT, "mock", "mock-model", timeout_seconds=31).sha256


def test_request_hash_changes_for_context_or_input_changes(tmp_path):
    skill_copy = tmp_path / "skill"
    case_copy = tmp_path / "case"
    shutil.copytree(SKILL_ROOT, skill_copy)
    shutil.copytree(ACCEPTANCE_ROOT, case_copy)
    package = load_skill_package(skill_copy)
    original = build_runtime_request(package, case_copy, "mock", "m").sha256

    (skill_copy / "references" / "adaptation-rules.md").write_text("changed", encoding="utf-8")
    assert build_runtime_request(load_skill_package(skill_copy), case_copy, "mock", "m").sha256 != original

    shutil.rmtree(skill_copy)
    shutil.copytree(SKILL_ROOT, skill_copy)
    (case_copy / "source-chapter.md").write_text("changed", encoding="utf-8")
    assert build_runtime_request(load_skill_package(skill_copy), case_copy, "mock", "m").sha256 != original


def test_persisted_request_snapshot_is_actual_adapter_input(tmp_path):
    service = RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))
    result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-model")
    snapshot = json.loads(service.store.read_text(result.run.request_object_id))

    assert snapshot["skill_instruction"]["relative_path"] == "SKILL.md"
    assert snapshot == json.loads(result.adapter_request_json)
    service.store.close()


def test_env_model_is_resolved_before_request_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DRAMA_API_KEY", "secret")
    monkeypatch.setenv("AI_DRAMA_MODEL", "env-model")
    monkeypatch.setattr(
        "ai_drama_runtime.runtime._run_openai_compatible",
        lambda runtime_request, started: (_ for _ in ()).throw(RuntimeErrorBase("RUNTIME_PROVIDER_ERROR", "fake provider")),
    )
    service = RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))

    result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "openai-compatible", "")

    snapshot = json.loads(service.store.read_text(result.run.request_object_id))
    assert snapshot["runtime_config"]["model"] == "env-model"
    assert result.run.error_code != "CONFIG_MISSING_MODEL"
    assert "secret" not in service.store.read_text(result.run.request_object_id)
    service.store.close()
