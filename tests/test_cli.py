import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = (
    REPO_ROOT
    / "skills"
    / "ai-drama-script-adaptation-skill"
    / "v0.6.1-rc2.4"
)


def _cli(tmp_path, *args):
    cmd = [
        sys.executable,
        "-m",
        "ai_drama_runtime.cli",
        "--store",
        str(tmp_path / "runtime.db"),
        "--objects",
        str(tmp_path / "objects"),
        *map(str, args),
    ]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def test_cli_mock_run_approve_and_export(tmp_path):
    validate = _cli(
        tmp_path,
        "skills",
        "validate",
        "--skill-root",
        SKILL_ROOT,
        "--version",
        "v0.6.1-rc2.4",
    )
    assert "v0.6.1-rc2.4" in validate.stdout

    run = _cli(
        tmp_path,
        "run",
        "--skill-root",
        SKILL_ROOT,
        "--acceptance-root",
        ACCEPTANCE_ROOT,
        "--runtime",
        "mock",
        "--model",
        "mock-cli",
    )
    payload = json.loads(run.stdout)
    assert payload["status"] == "succeeded"
    assert payload["revision_id"]

    _cli(tmp_path, "approve", payload["revision_id"], "--reviewer", "cli-test")
    current = json.loads(_cli(tmp_path, "approved", "shengsi-chapter-001").stdout)
    assert current["revision_id"] == payload["revision_id"]

    export_path = tmp_path / "export.md"
    _cli(tmp_path, "export", "shengsi-chapter-001", "--output", export_path)
    assert export_path.read_text(encoding="utf-8").startswith("#")
