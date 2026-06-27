from pathlib import Path

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))


def test_usage_and_stable_error_codes_are_persisted(tmp_path, monkeypatch):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    ok = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock")
    run = service.store.get_run(ok.run.run_id)
    assert run.usage_status == "PROVIDED"
    assert run.prompt_tokens >= 0
    assert run.total_tokens >= run.prompt_tokens

    monkeypatch.delenv("AI_DRAMA_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    missing_key = service.run_acceptance(package, ACCEPTANCE_ROOT, "openai-compatible", "model")
    assert missing_key.run.status == "RUNTIME_FAILED"
    assert missing_key.run.error_code == "CONFIG_MISSING_API_KEY"

    monkeypatch.setenv("AI_DRAMA_API_KEY", "secret")
    missing_model = service.run_acceptance(package, ACCEPTANCE_ROOT, "openai-compatible", "")
    assert missing_model.run.error_code == "CONFIG_MISSING_MODEL"
    service.store.close()


def test_compare_includes_input_and_request_hash_diffs(tmp_path):
    service = _service(tmp_path)
    package = load_skill_package(SKILL_ROOT)
    first = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "a")
    second = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "b")
    diff = service.compare_revisions(first.revision.revision_id, second.revision.revision_id)

    assert "input_hash_diff:" in diff
    assert "request_hash_diff:" in diff
    assert "source_chapter" in diff
    service.store.close()
