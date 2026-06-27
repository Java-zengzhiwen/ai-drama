from pathlib import Path
import json

from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.request import build_runtime_request
from ai_drama_runtime.runtime import RuntimeErrorBase, run_runtime
from ai_drama_runtime.services import RuntimeService
from ai_drama_runtime.store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"))


def test_usage_and_stable_error_codes_are_persisted(tmp_path, monkeypatch):
    package = load_skill_package(SKILL_ROOT)
    with _service(tmp_path) as service:
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

        empty = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock", mock_mode="empty_response")
        assert empty.run.status == "PARSE_FAILED"
        assert empty.run.error_code == "PARSER_EMPTY_OUTPUT"
        assert service.store.get_run(empty.run.run_id).usage_status == "PROVIDED"

        invalid = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock", mock_mode="parse_failure")
        assert invalid.run.error_code == "PARSER_INVALID_OUTPUT"


def test_runtime_reads_provider_and_timeout_from_request(monkeypatch):
    package = load_skill_package(SKILL_ROOT)
    request = build_runtime_request(package, ACCEPTANCE_ROOT, "mock", "model", timeout_seconds=7)

    assert run_runtime(request).provider == "mock"
    assert request.to_dict()["runtime_config"]["timeout_seconds"] == 7

    bad = build_runtime_request(package, ACCEPTANCE_ROOT, "missing-provider", "model", timeout_seconds=7)
    try:
        run_runtime(bad)
    except RuntimeErrorBase as exc:
        assert exc.code == "RUNTIME_PROVIDER_ERROR"
    else:
        raise AssertionError("missing provider should fail")


def test_runtime_timeout_error_code_is_stable(monkeypatch):
    package = load_skill_package(SKILL_ROOT)
    request = build_runtime_request(package, ACCEPTANCE_ROOT, "openai-compatible", "model", timeout_seconds=1)

    def fake_openai(runtime_request, started):
        raise RuntimeErrorBase("RUNTIME_TIMEOUT", "openai-compatible runtime failed")

    monkeypatch.setenv("AI_DRAMA_API_KEY", "secret")
    monkeypatch.setattr("ai_drama_runtime.runtime._run_openai_compatible", fake_openai)

    try:
        run_runtime(request)
    except RuntimeErrorBase as exc:
        assert exc.code == "RUNTIME_TIMEOUT"
    else:
        raise AssertionError("timeout should fail")


def test_failed_run_persists_resolved_env_model(monkeypatch, tmp_path):
    package = load_skill_package(SKILL_ROOT)
    monkeypatch.setenv("AI_DRAMA_MODEL", "env-model")
    monkeypatch.setenv("AI_DRAMA_API_KEY", "secret")

    def fake_openai(runtime_request, started):
        assert runtime_request.to_dict()["runtime_config"]["model"] == "env-model"
        raise RuntimeErrorBase("RUNTIME_PROVIDER_ERROR", "fake provider")

    monkeypatch.setattr("ai_drama_runtime.runtime._run_openai_compatible", fake_openai)

    with _service(tmp_path) as service:
        result = service.run_acceptance(package, ACCEPTANCE_ROOT, "openai-compatible", "")
        stored = service.store.get_run(result.run.run_id)
        snapshot = service.store.read_text(stored.request_object_id)

    assert stored.status == "RUNTIME_FAILED"
    assert stored.model == "env-model"
    assert '"model":"env-model"' in snapshot


def test_runtime_failures_persist_complete_metadata(monkeypatch, tmp_path):
    package = load_skill_package(SKILL_ROOT)
    cases = [
        ("CONFIG_MISSING_API_KEY", {}, "model"),
        ("CONFIG_MISSING_MODEL", {"AI_DRAMA_API_KEY": "secret"}, ""),
        ("RUNTIME_TIMEOUT", {"AI_DRAMA_API_KEY": "secret"}, "model"),
        ("RUNTIME_PROVIDER_ERROR", {"AI_DRAMA_API_KEY": "secret"}, "model"),
    ]

    for code, env, model in cases:
        monkeypatch.delenv("AI_DRAMA_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        if code in {"RUNTIME_TIMEOUT", "RUNTIME_PROVIDER_ERROR"}:
            monkeypatch.setattr(
                "ai_drama_runtime.runtime._run_openai_compatible",
                lambda runtime_request, started, code=code: (_ for _ in ()).throw(
                    RuntimeErrorBase(code, "openai-compatible runtime failed")
                ),
            )
        with _service(tmp_path / code) as service:
            result = service.run_acceptance(package, ACCEPTANCE_ROOT, "openai-compatible", model)
            stored = service.store.get_run(result.run.run_id)
        assert stored.status == "RUNTIME_FAILED"
        assert stored.provider == "openai-compatible"
        assert stored.model == model
        assert stored.error_code == code
        assert stored.error_message
        assert stored.completed_at
        assert stored.duration_ms >= 0


def test_compare_includes_input_and_request_hash_diffs(tmp_path):
    package = load_skill_package(SKILL_ROOT)
    with _service(tmp_path) as service:
        first = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "a")
        second = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "b")
        diff = service.compare_revisions(first.revision.revision_id, second.revision.revision_id)

        assert "input_hash_diff:" in diff
        assert "request_hash_diff:" in diff
        assert "source_chapter" in diff


def test_compare_validator_status_contains_only_left_and_right(tmp_path):
    package = load_skill_package(SKILL_ROOT)
    with _service(tmp_path) as service:
        left = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "left")
        right = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "right")
        service.store.insert_validation(
            revision_id=left.revision.revision_id,
            validator_id="left_only",
            validator_name="left_only",
            status="PASS",
            required=0,
            exit_code=0,
            error_code="",
            duration_ms=1,
            stdout_object_id=service.store.write_text_object(""),
            stderr_object_id=service.store.write_text_object(""),
            report_object_id=service.store.write_text_object("{}"),
        )
        service.store.insert_validation(
            revision_id=right.revision.revision_id,
            validator_id="right_only",
            validator_name="right_only",
            status="FAIL",
            required=0,
            exit_code=1,
            error_code="ERR_RIGHT",
            duration_ms=1,
            stdout_object_id=service.store.write_text_object(""),
            stderr_object_id=service.store.write_text_object(""),
            report_object_id=service.store.write_text_object("{}"),
        )
        diff = service.compare_revisions(left.revision.revision_id, right.revision.revision_id)

    metadata_text = diff.split("input_hash_diff:\n", 1)[0].removeprefix("metadata:\n")
    metadata = json.loads(metadata_text)
    validator_status = metadata["validator_status"]

    assert set(validator_status) == {"left", "right"}
    assert validator_status["left"]["left_only"] == "PASS"
    assert "right_only" not in validator_status["left"]
    assert validator_status["right"]["right_only"] == "FAIL"
    assert "left_only" not in validator_status["right"]
