import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
VERIFIER = ROOT / "tools" / "verify_m6_supplier_model_management.py"


def _module():
    spec = importlib.util.spec_from_file_location("m6e_verifier", VERIFIER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_verifier_has_ordered_semantic_schema_and_zero_real_request_evidence():
    module = _module()
    report = module.verify(group_results={name: True for name in module.GROUP_COMMANDS})

    assert list(report["checks"]) == [f"M6E-{number:03d}" for number in range(1, 19)]
    assert report["result"] == "PASS"
    assert report["success_token"] == "M6_SUPPLIER_MODEL_MANAGEMENT_PASS"
    assert report["verification_mode"] == "semantic"
    assert report["production_flag_enabled"] is False
    assert report["real_request_counts"] == {"text": 0, "image": 0, "video": 0}
    assert all(item["result"] == "PASS" for item in report["checks"].values())
    assert all(item["command_category"] and item["evidence"] for item in report["checks"].values())


def test_markdown_is_deterministic_and_contains_no_secret_material():
    module = _module()
    report = module.verify(group_results={name: True for name in module.GROUP_COMMANDS})

    first = module.markdown(report)
    second = module.markdown(report)

    assert first == second
    assert "M6E-001" in first and "M6E-018" in first
    assert "Bearer " not in first
    assert "api_key" not in first.lower()
    assert "text=0 image=0 video=0" in first


def test_cli_forced_failure_is_nonzero_and_compatibility_entrypoint_matches():
    failed = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test", "--force-fail", "M6E-001"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1
    payload = json.loads(failed.stdout)
    assert payload["checks"]["M6E-001"]["result"] == "FAIL"

    canonical = subprocess.run(
        [sys.executable, str(VERIFIER), "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    compatibility = subprocess.run(
        [sys.executable, "tools/verify_supplier_model_configuration.py", "--self-test"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(canonical.stdout) == json.loads(compatibility.stdout)
