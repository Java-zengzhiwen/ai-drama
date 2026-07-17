import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools" / "verify_aixora_adapter_model_archive.py"


def module():
    spec = importlib.util.spec_from_file_location("aixora_verifier", VERIFIER)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_verifier_schema_is_fake_only_and_has_zero_real_calls():
    loaded = module()
    report = loaded.verify(group_results={name: True for name in loaded.GROUP_COMMANDS})

    assert list(report["checks"]) == [f"AIXORA-{number:03d}" for number in range(1, 13)]
    assert "reasoning" in loaded.GROUP_COMMANDS
    assert report["result"] == "PASS"
    assert report["success_token"] == "AIXORA_MODEL_ARCHIVE_PASS"
    assert report["verification_mode"] == "offline_fake_only"
    assert report["production_m6_execution_flag_enabled"] is False
    assert report["real_provider_requests"] is False
    assert report["real_request_counts"] == {"text": 0, "image": 0, "video": 0}
    assert report["transport_guard_enabled"] is True


def test_cli_self_test_and_forced_failure_are_stable():
    passed = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(passed.stdout)["result"] == "PASS"

    failed = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test", "--force-fail", "AIXORA-001"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1
    assert json.loads(failed.stdout)["checks"]["AIXORA-001"]["result"] == "FAIL"
