import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_REF = "ai-drama-script-adaptation-skill@v0.6.1-rc2.4"
STORYBOARD_SKILL_REF = "ai-drama-storyboard-design-skill@v0.1.0"


def _cli(tmp_path, *args, check=True, env=None):
    cmd = [
        sys.executable,
        "-m",
        "ai_drama_runtime.cli",
        "--data-root",
        str(tmp_path / "data"),
        "--skills-root",
        str(REPO_ROOT / "skills"),
        *map(str, args),
    ]
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        env=env,
    )


def test_cli_required_command_flow_and_restart_reads(tmp_path):
    assert json.loads(_cli(tmp_path, "skills", "list").stdout)[0]["skill_ref"] == SKILL_REF
    assert json.loads(_cli(tmp_path, "skills", "show", SKILL_REF).stdout)["version"] == "v0.6.1-rc2.4"
    assert json.loads(_cli(tmp_path, "skills", "validate", SKILL_REF).stdout)["valid"] is True

    run = json.loads(
        _cli(
            tmp_path,
            "run",
            "create",
            "--skill",
            SKILL_REF,
            "--input",
            ACCEPTANCE_ROOT,
            "--runtime",
            "mock",
            "--model",
            "mock-cli",
        ).stdout
    )
    assert run["status"] == "SUCCEEDED"
    assert run["revision_id"]
    assert json.loads(_cli(tmp_path, "runs", "show", run["run_id"]).stdout)["run_id"] == run["run_id"]
    assert json.loads(_cli(tmp_path, "artifacts", "list").stdout)[0]["artifact_id"] == "shengsi-chapter-001"
    assert json.loads(_cli(tmp_path, "artifacts", "revisions", "shengsi-chapter-001").stdout)

    _cli(tmp_path, "approvals", "approve", run["revision_id"], "--reviewer", "cli")
    assert json.loads(_cli(tmp_path, "artifacts", "approved", "shengsi-chapter-001").stdout)["revision_id"] == run["revision_id"]
    output = tmp_path / "approved.md"
    _cli(tmp_path, "artifacts", "export-approved", "shengsi-chapter-001", "--output", output)
    assert output.exists()
    assert (tmp_path / "approved.md.provenance.json").exists()


def test_cli_exit_codes_and_redacts_credentials(tmp_path):
    not_found = _cli(tmp_path, "skills", "show", "missing@v1", check=False)
    assert not_found.returncode == 3

    runtime_failed = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        SKILL_REF,
        "--input",
        ACCEPTANCE_ROOT,
        "--runtime",
        "mock",
        "--mock-mode",
        "runtime_failure",
        check=False,
    )
    assert runtime_failed.returncode == 4

    env = dict(**__import__("os").environ, AI_DRAMA_API_KEY="secret-value")
    failed_openai = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        SKILL_REF,
        "--input",
        ACCEPTANCE_ROOT,
        "--runtime",
        "openai-compatible",
        check=False,
        env=env,
    )
    assert "secret-value" not in failed_openai.stderr
    assert failed_openai.returncode in {2, 4}


def test_cli_storyboard_run_flow(tmp_path):
    script_run = json.loads(
        _cli(
            tmp_path,
            "run",
            "create",
            "--skill",
            SKILL_REF,
            "--input",
            ACCEPTANCE_ROOT,
            "--runtime",
            "mock",
            "--model",
            "mock-script",
        ).stdout
    )
    _cli(tmp_path, "approvals", "approve", script_run["revision_id"], "--reviewer", "cli")

    storyboard_run = json.loads(
        _cli(
            tmp_path,
            "run",
            "create",
            "--skill",
            STORYBOARD_SKILL_REF,
            "--source-revision",
            script_run["revision_id"],
            "--runtime",
            "mock",
            "--model",
            "mock-storyboard",
        ).stdout
    )
    assert storyboard_run["status"] == "SUCCEEDED"
    assert storyboard_run["revision_id"]


def test_cli_enforces_mutually_exclusive_inputs(tmp_path):
    conflict = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        SKILL_REF,
        "--input",
        ACCEPTANCE_ROOT,
        "--source-revision",
        "abc",
        "--runtime",
        "mock",
        check=False,
    )
    assert conflict.returncode == 2
    assert "not allowed with argument" in conflict.stderr

    missing = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        SKILL_REF,
        "--runtime",
        "mock",
        check=False,
    )
    assert missing.returncode == 2


def test_cli_reports_storyboard_gate_failures(tmp_path):
    gate = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        STORYBOARD_SKILL_REF,
        "--source-revision",
        "missing-revision",
        "--runtime",
        "mock",
        check=False,
    )
    assert gate.returncode == 2
    payload = json.loads(gate.stdout)
    assert payload["error_code"] == "SOURCE_REVISION_NOT_FOUND"


def test_cli_rejects_skill_input_type_mismatch(tmp_path):
    bad_storyboard = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        STORYBOARD_SKILL_REF,
        "--input",
        ACCEPTANCE_ROOT,
        "--runtime",
        "mock",
        check=False,
    )
    assert bad_storyboard.returncode == 2
    assert "SKILL_INPUT_TYPE_MISMATCH" in bad_storyboard.stdout

    bad_script = _cli(
        tmp_path,
        "run",
        "create",
        "--skill",
        SKILL_REF,
        "--source-revision",
        "x",
        "--runtime",
        "mock",
        check=False,
    )
    assert bad_script.returncode == 2
    assert "SKILL_INPUT_TYPE_MISMATCH" in bad_script.stdout
