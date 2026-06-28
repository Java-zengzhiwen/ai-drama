from pathlib import Path
import importlib.util
import subprocess
import sys
import tempfile
import time


def _missing_dependencies(dependencies):
    missing = []
    for dep in dependencies:
        name = dep.split(">=")[0].split("==")[0].strip()
        if name and importlib.util.find_spec(name) is None:
            missing.append(name)
    return missing


def _insert(store, revision, validator, status, exit_code=0, error_code="", duration_ms=0, stdout="", stderr="", report="{}"):
    return store.insert_validation(
        revision_id=revision.revision_id,
        validator_id=validator.validator_id,
        validator_name=validator.name,
        status=status,
        required=int(validator.required),
        exit_code=exit_code,
        error_code=error_code,
        duration_ms=duration_ms,
        stdout_object_id=store.write_text_object(stdout),
        stderr_object_id=store.write_text_object(stderr),
        report_object_id=store.write_text_object(report if report.endswith("\n") else report + "\n"),
    )


def _as_text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _current_artifact_type(revision):
    return revision.artifact_type if hasattr(revision, "artifact_type") else ""


def _validator_applies_to_revision(validator, revision):
    if validator.current_profile_status == "NOT_APPLICABLE":
        return False
    revision_type = _current_artifact_type(revision)
    if revision_type == "drama_script":
        accepted = {"drama_script_revision"}
    elif revision_type == "storyboard":
        accepted = {"storyboard_revision"}
    elif revision_type == "skill_package":
        accepted = {"skill_package"}
    else:
        accepted = set()
    return bool(set(validator.applies_to) & accepted)


def _artifact_source_label(artifact_type):
    if artifact_type == "storyboard":
        return "storyboard_revision"
    if artifact_type == "skill_package":
        return "skill_package"
    return "drama_script_revision"


def run_declared_validators(store, skill, revision, acceptance_root, repo_root=None):
    results = []
    revision_path = store.object_path(revision.content_object_id)
    repo_root = Path(repo_root or Path.cwd()).resolve()
    for validator in skill.validators:
        if validator.current_profile_status == "NOT_APPLICABLE":
            results.append(
                _insert(
                    store,
                    revision,
                    validator,
                    "NOT_APPLICABLE",
                    stderr=(validator.current_profile_reason or "not applicable to current execution profile") + "\n",
                )
            )
            continue
        if not _validator_applies_to_revision(validator, revision):
            results.append(
                _insert(
                    store,
                    revision,
                    validator,
                    "NOT_APPLICABLE",
                    stderr="validator applies to %s, not current revision type %s\n" % (
                        ",".join(validator.applies_to),
                        _artifact_source_label(revision.artifact_type),
                    ),
                )
            )
            continue
        missing = _missing_dependencies(validator.dependencies)
        if missing:
            results.append(
                _insert(
                    store,
                    revision,
                    validator,
                    "SKIPPED_DEPENDENCY_MISSING",
                    error_code="DEPENDENCY_MISSING",
                    stderr="missing dependencies: %s\n" % ",".join(missing),
                )
            )
            continue
        if not validator.command:
            results.append(
                _insert(
                    store,
                    revision,
                    validator,
                    "NOT_APPLICABLE",
                    stderr="no command declared for this artifact shape\n",
                )
            )
            continue

        with tempfile.TemporaryDirectory(prefix="ai-drama-validator-") as tmp:
            report_path = Path(tmp) / ("%s-report.json" % validator.validator_id)
            substitutions = {
                "entrypoint": str(validator.entrypoint),
                "revision_path": str(revision_path),
                "artifact_id": revision.artifact_id,
                "skill_root": str(skill.root),
                "acceptance_root": str(acceptance_root),
                "repo_root": str(repo_root),
                "report_path": str(report_path),
                "python": sys.executable,
            }
            command = [part.format(**substitutions) for part in validator.command]
            started = time.time()
            try:
                proc = subprocess.run(
                    command,
                    cwd=str(skill.root),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=validator.timeout_seconds,
                )
                duration_ms = int((time.time() - started) * 1000)
                report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "{}\n"
                results.append(
                    _insert(
                        store,
                        revision,
                        validator,
                        "PASS" if proc.returncode == 0 else "FAIL",
                        exit_code=proc.returncode,
                        error_code="" if proc.returncode == 0 else "VALIDATOR_EXECUTION_ERROR",
                        duration_ms=duration_ms,
                        stdout=proc.stdout,
                        stderr=proc.stderr,
                        report=report_text,
                    )
                )
            except subprocess.TimeoutExpired as exc:
                stderr = _as_text(exc.stderr) or "validator timed out"
                results.append(
                    _insert(
                        store,
                        revision,
                        validator,
                        "FAIL",
                        exit_code=-1,
                        error_code="VALIDATOR_TIMEOUT",
                        duration_ms=int((time.time() - started) * 1000),
                        stdout=_as_text(exc.stdout),
                        stderr=stderr,
                    )
                )
            except Exception as exc:
                results.append(
                    _insert(
                        store,
                        revision,
                        validator,
                        "FAIL",
                        exit_code=-1,
                        error_code="VALIDATOR_EXECUTION_ERROR",
                        duration_ms=int((time.time() - started) * 1000),
                        stderr=str(exc),
                    )
                )
    return results
