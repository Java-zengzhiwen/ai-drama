import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools" / "verify_model_level_provider_tests.py"


def _module():
    spec = importlib.util.spec_from_file_location("model_test_verifier", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_has_ordered_schema_and_zero_real_request_evidence():
    module = _module()
    report = module.verify(group_results={name: True for name in module.GROUP_COMMANDS})

    assert list(report["checks"]) == [f"MTEST-{number:03d}" for number in range(1, 16)]
    assert report["result"] == "PASS"
    assert report["success_token"] == "MODEL_LEVEL_PROVIDER_TESTS_PASS"
    assert report["verification_mode"] == "offline_fake_only"
    assert report["production_model_test_flag_enabled"] is False
    assert report["real_provider_requests"] is False
    assert report["real_request_counts"] == {"text": 0, "image": 0, "video": 0}
    assert report["transport_guard_enabled"] is True
    assert "tests/conftest.py" in report["network_evidence"]
    assert all(item["result"] == "PASS" for item in report["checks"].values())
    assert all(item["command_category"] and item["evidence"] for item in report["checks"].values())


def test_markdown_is_deterministic_and_contains_no_secret_material():
    module = _module()
    report = module.verify(group_results={name: True for name in module.GROUP_COMMANDS})

    first = module.markdown(report)
    second = module.markdown(report)

    assert first == second
    assert "MTEST-001" in first and "MTEST-015" in first
    assert "Bearer " not in first
    assert "api_key" not in first.lower()
    assert "text=0 image=0 video=0" in first
    assert "Production model test flag enabled: false" in first


def test_cli_self_test_and_forced_failure_have_stable_exit_codes():
    passed = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(passed.stdout)["result"] == "PASS"

    failed = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test", "--force-fail", "MTEST-001"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["checks"]["MTEST-001"]["result"] == "FAIL"
