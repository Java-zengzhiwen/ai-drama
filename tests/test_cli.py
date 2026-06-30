import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_REF = "ai-drama-script-adaptation-skill@v0.6.1-rc2.4"
STORYBOARD_SKILL_REF = "ai-drama-storyboard-design-skill@v0.1.0"
STORYBOARD_CANONICAL_SKILL_REF = "ai-drama-storyboard-design-skill@v0.2.0"


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


def _canonical_revision_via_cli(tmp_path):
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
            STORYBOARD_CANONICAL_SKILL_REF,
            "--source-revision",
            script_run["revision_id"],
            "--runtime",
            "mock",
            "--model",
            "mock-storyboard-canonical",
        ).stdout
    )
    return storyboard_run["revision_id"]


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


def test_cli_canonical_storyboard_render_and_legacy_migration(tmp_path):
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

    canonical_run = json.loads(
        _cli(
            tmp_path,
            "run",
            "create",
            "--skill",
            STORYBOARD_CANONICAL_SKILL_REF,
            "--source-revision",
            script_run["revision_id"],
            "--runtime",
            "mock",
            "--model",
            "mock-storyboard-canonical",
        ).stdout
    )
    render_path = tmp_path / "canonical.md"
    rendered = json.loads(_cli(tmp_path, "storyboard", "render", "--revision", canonical_run["revision_id"], "--output", render_path).stdout)
    assert rendered["status"] == "RENDERED"
    assert rendered["content_profile"] == "storyboard-canonical-v1"
    assert render_path.read_text(encoding="utf-8").startswith("# Storyboard Canonical Render\n")

    legacy_run = json.loads(
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
    _cli(tmp_path, "approvals", "approve", legacy_run["revision_id"], "--reviewer", "cli")
    preview = json.loads(
        _cli(
            tmp_path,
            "storyboard",
            "migrate-legacy",
            "--source-revision",
            legacy_run["revision_id"],
            "--preview",
            "--output",
            tmp_path / "preview",
        ).stdout
    )
    assert preview["status"] == "PREVIEW"
    confirmed = json.loads(
        _cli(
            tmp_path,
            "storyboard",
            "migrate-legacy",
            "--source-revision",
            legacy_run["revision_id"],
            "--confirm-candidate-hash",
            preview["candidate_hash"],
            "--output",
            tmp_path / "confirm",
        ).stdout
    )
    assert confirmed["status"] == "PENDING_CANONICAL_REVISION"
    assert confirmed["approval_status"] == "pending"


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


def test_artifacts_outputs_returns_frozen_json_contract(tmp_path):
    revision_id = _canonical_revision_via_cli(tmp_path)

    payload = json.loads(_cli(tmp_path, "artifacts", "outputs", "--revision", revision_id).stdout)

    assert payload["revision_id"] == revision_id
    assert payload["artifact_type"] == "storyboard"
    assert payload["content_profile"] == "storyboard-canonical-v1"
    assert payload["materialization_status"] == "NOT_MATERIALIZED"
    assert payload["bundle_integrity"] == "NOT_CHECKED"
    assert payload["bundle_manifest_hash"] == ""
    assert payload["outputs"] == []


def test_artifacts_materialize_bundle_returns_frozen_json_contract(tmp_path):
    revision_id = _canonical_revision_via_cli(tmp_path)

    payload = json.loads(_cli(tmp_path, "artifacts", "materialize-bundle", "--revision", revision_id).stdout)

    assert payload["status"] == "MATERIALIZED"
    assert payload["revision_id"] == revision_id
    assert payload["rendered_markdown_output_id"]
    assert payload["bundle_manifest_output_id"]
    assert payload["bundle_manifest_hash"]
    assert payload["bundle_integrity"] == "PASS"
    assert payload["approval_status"] == "pending"


def test_artifacts_export_bundle_returns_frozen_json_contract(tmp_path):
    revision_id = _canonical_revision_via_cli(tmp_path)
    _cli(tmp_path, "artifacts", "materialize-bundle", "--revision", revision_id)
    _cli(tmp_path, "approvals", "approve", revision_id, "--reviewer", "cli")

    output = tmp_path / "formal-review"
    payload = json.loads(
        _cli(
            tmp_path,
            "artifacts",
            "export-bundle",
            "--revision",
            revision_id,
            "--kind",
            "formal-review",
            "--output",
            output,
        ).stdout
    )

    assert payload["status"] == "EXPORTED"
    assert payload["revision_id"] == revision_id
    assert payload["export_kind"] == "formal_review"
    assert payload["destination"] == str(output)
    assert payload["bundle_manifest_hash"]
    assert payload["freshness_status"] == "FRESH"
    assert payload["diagnostic_only"] is False
    assert payload["not_an_execution_package"] is True
    assert payload["execution_ready"] is False


def test_artifacts_export_bundle_execution_returns_blocked_json_and_zero_exit(tmp_path):
    revision_id = _canonical_revision_via_cli(tmp_path)
    output = tmp_path / "execution"

    result = _cli(
        tmp_path,
        "artifacts",
        "export-bundle",
        "--revision",
        revision_id,
        "--kind",
        "execution",
        "--output",
        output,
        check=False,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 0
    assert payload["status"] == "BLOCKED"
    assert payload["revision_id"] == revision_id
    assert payload["export_kind"] == "execution"
    assert payload["bundle_status"] == "not_materialized"
    assert payload["bundle_manifest_hash"] == ""
    assert payload["error_code"] == "EXPORT_NOT_EXECUTION_READY"
    assert not output.exists()


def test_artifacts_export_bundle_rejects_unsupported_profile(tmp_path):
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

    result = _cli(
        tmp_path,
        "artifacts",
        "export-bundle",
        "--revision",
        script_run["revision_id"],
        "--kind",
        "formal-review",
        "--output",
        tmp_path / "bad-profile",
        check=False,
    )
    payload = json.loads(result.stdout)

    assert result.returncode == 2
    assert payload["error_code"] == "BUNDLE_PROFILE_UNSUPPORTED"


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
