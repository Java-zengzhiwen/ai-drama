from pathlib import Path
import json
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
    elif revision_type == "shot_prompt_set":
        accepted = {"shot_prompt_set"}
    elif revision_type == "skill_package":
        accepted = {"skill_package"}
    else:
        accepted = set()
    return bool(set(validator.applies_to) & accepted)


def _artifact_source_label(artifact_type):
    if artifact_type == "storyboard":
        return "storyboard_revision"
    if artifact_type == "shot_prompt_set":
        return "shot_prompt_set"
    if artifact_type == "skill_package":
        return "skill_package"
    return "drama_script_revision"


def _revision_content_profile(revision):
    return getattr(revision, "content_profile", "")


def _freshness_status(store, revision_id, seen=None):
    seen = set(seen or [])
    if revision_id in seen:
        return "DEPENDENCY_CYCLE_DETECTED"
    seen.add(revision_id)
    revision = store.get_revision(revision_id)
    if revision is None:
        return "DEPENDENCY_MISSING"
    deps = store.revision_dependencies(revision_id)
    for dep in deps:
        parent = store.get_revision(dep.parent_revision_id)
        if parent is None:
            return "DEPENDENCY_MISSING"
        if parent.content_hash != dep.parent_content_hash:
            return "SOURCE_STALE"
        current = store.current_approved(parent.artifact_id)
        if not current or current.revision_id != parent.revision_id:
            return "SOURCE_STALE"
        if dep.parent_approval_record_id and store.approval_record(dep.parent_approval_record_id) is None:
            return "DEPENDENCY_MISSING"
        parent_status = _freshness_status(store, parent.revision_id, seen)
        if parent_status != "FRESH":
            return parent_status
    return "FRESH"


def recursive_freshness_status(store, revision_id):
    status = _freshness_status(store, revision_id)
    return "STALE" if status in {"SOURCE_STALE", "DEPENDENCY_MISSING", "DEPENDENCY_CYCLE_DETECTED"} else status


def _extract_script_scenes(text):
    import re

    scenes = []
    for line in text.splitlines():
        match = re.match(r"^##\s*(?:Scene(?:\s*:\s*|\s+)?|场次：)(.+?)\s*$", line)
        if match:
            scenes.append(match.group(1).strip())
    return scenes


def _validate_source_coverage(store, revision, canonical):
    deps = store.revision_dependencies(revision.revision_id)
    if not deps:
        raise ValueError("missing source dependency")
    source = store.get_revision(deps[0].parent_revision_id)
    if source is None:
        raise ValueError("missing source revision")
    source_scenes = _extract_script_scenes(store.read_text(source.content_object_id))
    scene_refs = [scene["source_scene_reference"] for scene in canonical["scenes"]]
    missing = [scene for scene in source_scenes if scene not in scene_refs]
    extra = [ref for ref in scene_refs if ref not in source_scenes]
    if missing or extra:
        raise ValueError("missing=%s extra=%s" % (missing, extra))


def _validate_continuity(canonical):
    shot_ids = {shot["shot_id"] for shot in canonical["shots"]}
    for shot in canonical["shots"]:
        for key in ("continuity_in", "continuity_out"):
            source_ref = shot[key].get("source_unit_or_shot_id")
            if source_ref is not None and source_ref not in shot_ids:
                raise ValueError("%s references unknown shot %s" % (key, source_ref))


def _run_native_canonical_validator(store, revision, validator):
    if _revision_content_profile(revision) != "storyboard-canonical-v1":
        return None
    if validator.validator_id not in {
        "storyboard_source_coverage",
        "storyboard_renderer_parity",
        "storyboard_source_freshness",
        "storyboard_bundle_integrity",
    }:
        return None
    from .storyboard_canonical import CanonicalStoryboardError, parse_canonical_json
    from .storyboard_renderer import render_storyboard_markdown

    started = time.time()
    status = "PASS"
    error_code = ""
    report = {"validator_id": validator.validator_id, "final_status": "pass"}
    try:
        canonical = parse_canonical_json(store.read_text(revision.content_object_id))
        if validator.validator_id == "storyboard_source_coverage":
            _validate_source_coverage(store, revision, canonical)
        elif validator.validator_id == "storyboard_renderer_parity":
            first = render_storyboard_markdown(canonical)
            second = render_storyboard_markdown(canonical)
            if first.encode("utf-8") != second.encode("utf-8"):
                raise CanonicalStoryboardError("RENDERER_PARITY_FAILED", "renderer output is not deterministic")
            report["rendered_markdown_sha256"] = __import__("hashlib").sha256(first.encode("utf-8")).hexdigest()
        elif validator.validator_id == "storyboard_source_freshness":
            freshness = _freshness_status(store, revision.revision_id)
            report["freshness_status"] = freshness
            if freshness != "FRESH":
                raise CanonicalStoryboardError(freshness, "source freshness is %s" % freshness)
        elif validator.validator_id == "storyboard_bundle_integrity":
            from .services import RuntimeService

            integrity = RuntimeService(store).check_storyboard_bundle_integrity(revision.revision_id)
            report["bundle_manifest_hash"] = integrity["bundle_manifest_hash"]
    except CanonicalStoryboardError as exc:
        status = "FAIL"
        error_code = exc.code
        report["final_status"] = "fail"
        report["error_code"] = exc.code
        report["message"] = exc.safe_message
    except ValueError as exc:
        status = "FAIL"
        if validator.validator_id == "storyboard_source_coverage":
            error_code = "SHOT_COVERAGE_INCOMPLETE"
        else:
            error_code = "CANONICAL_SCHEMA_INVALID"
        report["final_status"] = "fail"
        report["error_code"] = error_code
        report["message"] = str(exc)
    except RuntimeError as exc:
        if not hasattr(exc, "code"):
            raise
        status = "FAIL"
        error_code = exc.code
        report["final_status"] = "fail"
        report["error_code"] = exc.code
        report["message"] = exc.safe_message
    return _insert(
        store,
        revision,
        validator,
        status,
        exit_code=0 if status == "PASS" else 1,
        error_code=error_code,
        duration_ms=int((time.time() - started) * 1000),
        report=__import__("json").dumps(report, ensure_ascii=False, sort_keys=True),
    )


def run_declared_validators(store, skill, revision, acceptance_root, repo_root=None):
    results = []
    revision_path = store.object_path(revision.content_object_id)
    repo_root = Path(repo_root or Path.cwd()).resolve()
    for validator in skill.validators:
        native = _run_native_canonical_validator(store, revision, validator)
        if native is not None:
            results.append(native)
            continue
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
                error_code = ""
                if proc.returncode != 0:
                    error_code = "VALIDATOR_EXECUTION_ERROR"
                    try:
                        error_code = json.loads(report_text).get("error_code") or error_code
                    except (json.JSONDecodeError, AttributeError):
                        pass
                results.append(
                    _insert(
                        store,
                        revision,
                        validator,
                        "PASS" if proc.returncode == 0 else "FAIL",
                        exit_code=proc.returncode,
                        error_code=error_code,
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
