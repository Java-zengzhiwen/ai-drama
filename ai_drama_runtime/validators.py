from pathlib import Path
import subprocess
import tempfile


def run_declared_validators(store, skill, revision, acceptance_root, repo_root=None):
    results = []
    revision_path = store.object_path(revision.content_object_id)
    repo_root = Path(repo_root or Path.cwd()).resolve()
    for validator in skill.validators:
        if not validator.command:
            results.append(
                store.insert_validation(
                    revision_id=revision.revision_id,
                    validator_name=validator.name,
                    status="skipped",
                    required=int(validator.required),
                    exit_code=0,
                    stdout_object_id=store.write_text_object(""),
                    stderr_object_id=store.write_text_object("no command declared for MVP runtime\n"),
                    report_object_id=store.write_text_object("{}\n"),
                )
            )
            continue

        with tempfile.TemporaryDirectory(prefix="ai-drama-validator-") as tmp:
            report_path = Path(tmp) / ("%s-report.json" % validator.name)
            substitutions = {
                "entrypoint": str(validator.entrypoint),
                "revision_path": str(revision_path),
                "artifact_id": revision.artifact_id,
                "skill_root": str(skill.root),
                "acceptance_root": str(acceptance_root),
                "repo_root": str(repo_root),
                "report_path": str(report_path),
            }
            command = [part.format(**substitutions) for part in validator.command]
            proc = subprocess.run(
                command,
                cwd=str(skill.root),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            report_text = report_path.read_text(encoding="utf-8") if report_path.exists() else "{}\n"
            results.append(
                store.insert_validation(
                    revision_id=revision.revision_id,
                    validator_name=validator.name,
                    status="passed" if proc.returncode == 0 else "failed",
                    required=int(validator.required),
                    exit_code=proc.returncode,
                    stdout_object_id=store.write_text_object(proc.stdout),
                    stderr_object_id=store.write_text_object(proc.stderr),
                    report_object_id=store.write_text_object(report_text),
                )
            )
    return results
