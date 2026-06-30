import json
import subprocess
from pathlib import Path

import pytest

from ai_drama_runtime.manifest import SkillValidator
from ai_drama_runtime.manifest import load_skill_package
from ai_drama_runtime.services import ApprovalBlocked, BundleError, BundleExportError, DiagnosticParentError, ExportConflict, RuntimeService
from ai_drama_runtime.store import RuntimeStore
from ai_drama_runtime.validators import run_declared_validators


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_ROOT = REPO_ROOT / "acceptance" / "shengsi-chapter-001"
SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-script-adaptation-skill" / "v0.6.1-rc2.4"
STORYBOARD_CANONICAL_SKILL_ROOT = REPO_ROOT / "skills" / "ai-drama-storyboard-design-skill" / "v0.2.0"


def _service(tmp_path):
    return RuntimeService(RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects"), repo_root=REPO_ROOT)


def _canonical_storyboard_revision(service, *, materialize=True):
    script = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-script")
    service.approve_revision(script.revision.revision_id, "tester")
    storyboard = service.run_storyboard(
        load_skill_package(STORYBOARD_CANONICAL_SKILL_ROOT),
        script.revision.revision_id,
        "mock",
        "mock-storyboard-canonical-v1",
    )
    if materialize:
        service.materialize_storyboard_bundle(storyboard.revision.revision_id)
    return storyboard.revision


def _approved_bundle_revision(service):
    revision = _canonical_storyboard_revision(service)
    service.approve_revision(revision.revision_id, "tester")
    return service.store.get_revision(revision.revision_id)


def _set_output_object(service, output, data):
    object_id = service.store.write_bytes_object(data)
    service.store.conn.execute(
        "UPDATE revision_outputs SET object_id = ?, content_hash = ? WHERE revision_output_id = ?",
        (object_id, object_id, output.revision_output_id),
    )
    service.store.conn.commit()
    return object_id


def test_validator_statuses_and_required_approval_block(tmp_path):
    with _service(tmp_path) as service:
        result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-a")

        statuses = {item.validator_id: item.status for item in result.validation_results}
        assert statuses["runtime_script_revision_structure"] == "PASS"
        assert "NOT_APPLICABLE" in statuses.values()

        bad = service.run_acceptance(
            load_skill_package(SKILL_ROOT),
            ACCEPTANCE_ROOT,
            "mock",
            "mock-b",
            mock_mode="empty_response",
        )
        assert bad.run.status == "PARSE_FAILED"

        service.approve_revision(result.revision.revision_id, "tester")
        assert service.current_approved("shengsi-chapter-001").revision_id == result.revision.revision_id


def test_required_failed_validator_blocks_approval(tmp_path):
    with _service(tmp_path) as service:
        result = service.run_acceptance(load_skill_package(SKILL_ROOT), ACCEPTANCE_ROOT, "mock", "mock-a")
        service.store.insert_validation(
            revision_id=result.revision.revision_id,
            validator_id="forced",
            validator_name="forced",
            status="FAIL",
            required=1,
            exit_code=1,
            error_code="ERR_FORCED",
            duration_ms=1,
            stdout_object_id=service.store.write_text_object(""),
            stderr_object_id=service.store.write_text_object(""),
            report_object_id=service.store.write_text_object("{}"),
        )

        with pytest.raises(ApprovalBlocked):
            service.approve_revision(result.revision.revision_id, "tester")


def test_required_not_applicable_validator_blocks_approval(tmp_path):
    package = load_skill_package(SKILL_ROOT)
    validators = list(package.validators) + [
        SkillValidator(
            "bundle_required",
            "bundle_required",
            package.validators[0].entrypoint,
            True,
            ["full_artifact_bundle"],
            [],
            [],
            1,
            "zero_is_pass",
            "migrated_skill",
            ["drama_script_json"],
            "NOT_APPLICABLE",
            "requires complete bundle",
        )
    ]
    package = type("Pkg", (), {**package.__dict__, "validators": validators})()

    with _service(tmp_path) as service:
        result = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock")

        assert result.run.status == "VALIDATION_FAILED"
        assert {item.validator_id: item.status for item in result.validation_results}["bundle_required"] == "NOT_APPLICABLE"
        with pytest.raises(ApprovalBlocked):
            service.approve_revision(result.revision.revision_id, "tester")


def test_required_validator_failures_persist_run_error_metadata(tmp_path):
    fail_py = tmp_path / "fail.py"
    missing_py = tmp_path / "missing.py"
    timeout_py = tmp_path / "timeout.py"
    optional_fail_py = tmp_path / "optional_fail.py"
    fail_py.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    missing_py.write_text("print('missing dependency path')\n", encoding="utf-8")
    timeout_py.write_text("import time; time.sleep(3)\n", encoding="utf-8")
    optional_fail_py.write_text("import sys; sys.exit(1)\n", encoding="utf-8")

    base = load_skill_package(SKILL_ROOT)
    cases = [
        ("required_fail", SkillValidator("required_fail", "required_fail", fail_py, True, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 2, "zero_is_pass")),
        (
            "required_missing",
            SkillValidator(
                "required_missing",
                "required_missing",
                missing_py,
                True,
                ["drama_script_revision"],
                ["{python}", "{entrypoint}"],
                ["definitely_missing_pkg_xyz"],
                2,
                "zero_is_pass",
            ),
        ),
        ("required_timeout", SkillValidator("required_timeout", "required_timeout", timeout_py, True, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass")),
    ]

    for name, validator in cases:
        package = type("Pkg", (), {**base.__dict__, "validators": [validator]})()
        with _service(tmp_path / name) as service:
            result = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock")
            stored = service.store.get_run(result.run.run_id)
            assert stored.status == "VALIDATION_FAILED"
            assert stored.error_code == "VALIDATION_REQUIRED_FAILED"
            assert validator.validator_id in stored.error_message
            with pytest.raises(ApprovalBlocked):
                service.approve_revision(result.revision.revision_id, "tester")

    optional_package = type(
        "Pkg",
        (),
        {**base.__dict__, "validators": [SkillValidator("optional_fail", "optional_fail", optional_fail_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 2, "zero_is_pass")]},
    )()
    with _service(tmp_path / "optional") as service:
        result = service.run_acceptance(optional_package, ACCEPTANCE_ROOT, "mock", "mock")
        assert result.run.status == "SUCCEEDED"


def test_compare_includes_metadata_and_export_needs_force_with_sidecar(tmp_path):
    with _service(tmp_path) as service:
        package = load_skill_package(SKILL_ROOT)
        first = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-a")
        second = service.run_acceptance(package, ACCEPTANCE_ROOT, "mock", "mock-b")
        service.approve_revision(second.revision.revision_id, "tester")

        diff = service.compare_revisions(first.revision.revision_id, second.revision.revision_id)
        assert "metadata:" in diff
        assert "validator_status:" in diff
        assert "--- " in diff

        output = tmp_path / "approved.md"
        service.export_approved("shengsi-chapter-001", output)
        with pytest.raises(ExportConflict):
            service.export_approved("shengsi-chapter-001", output)
        output.unlink()
        with pytest.raises(ExportConflict):
            service.export_approved("shengsi-chapter-001", output)
        service.export_approved("shengsi-chapter-001", output, force=True)
        sidecar = json.loads((tmp_path / "approved.md.provenance.json").read_text(encoding="utf-8"))
        assert sidecar["artifact_id"] == "shengsi-chapter-001"
        assert sidecar["revision_id"] == second.revision.revision_id
        assert sidecar["export_time"].endswith("Z")
        assert service.store.read_text(service.store.export_records("shengsi-chapter-001")[-1].provenance_object_id) == (
            tmp_path / "approved.md.provenance.json"
        ).read_text(encoding="utf-8")


def test_validator_dependency_missing_timeout_and_crash_continue(tmp_path):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        store.ensure_artifact("a", "drama_script", "p", "c")
        run = store.create_run(
            artifact_id="a",
            project_id="p",
            chapter_id="c",
            skill_id="s",
            skill_version="v1",
            skill_hash="h",
            runtime="mock",
            provider="mock",
            model="m",
            status="SUCCEEDED",
            request_object_id=store.write_text_object("request"),
            response_object_id=store.write_text_object("{}"),
            input_hash="h",
        )
        revision = store.insert_revision(
            artifact_id="a",
            artifact_type="drama_script",
            project_id="p",
            chapter_id="c",
            run_id=run.run_id,
            skill_id="s",
            skill_version="v1",
            skill_package_hash="h",
            runtime_provider="mock",
            runtime_model="m",
            content_object_id=store.write_text_object("# Script\n\n## Scene\nBody"),
            content_hash="h",
            raw_response_object_id=store.write_text_object("{}"),
            parser_version="p",
        )
        timeout_py = tmp_path / "timeout.py"
        crash_py = tmp_path / "crash.py"
        pass_py = tmp_path / "pass.py"
        timeout_py.write_text("import time; time.sleep(2)\n", encoding="utf-8")
        crash_py.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
        pass_py.write_text("print('ok')\n", encoding="utf-8")
        validators = [
            SkillValidator("missing", "missing", pass_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], ["definitely_missing_pkg_xyz"], 1, "zero_is_pass"),
            SkillValidator("timeout", "timeout", timeout_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass"),
            SkillValidator("crash", "crash", crash_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass"),
            SkillValidator("pass", "pass", pass_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass"),
        ]
        package = type("Pkg", (), {"validators": validators, "root": tmp_path})()

        results = run_declared_validators(store, package, revision, tmp_path, repo_root=tmp_path)
        statuses = {item.validator_id: item.status for item in results}
        assert statuses["missing"] == "SKIPPED_DEPENDENCY_MISSING"
        assert statuses["timeout"] == "FAIL"
        assert statuses["crash"] == "FAIL"
        assert statuses["pass"] == "PASS"


def test_timeout_expired_bytes_are_persisted_as_text_and_validators_continue(tmp_path, monkeypatch):
    with RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects") as store:
        store.ensure_artifact("a", "drama_script", "p", "c")
        run = store.create_run(
            artifact_id="a",
            project_id="p",
            chapter_id="c",
            skill_id="s",
            skill_version="v1",
            skill_hash="h",
            runtime="mock",
            provider="mock",
            model="m",
            status="SUCCEEDED",
            request_object_id=store.write_text_object("request"),
            response_object_id=store.write_text_object("{}"),
            input_hash="h",
        )
        revision = store.insert_revision(
            artifact_id="a",
            artifact_type="drama_script",
            project_id="p",
            chapter_id="c",
            run_id=run.run_id,
            skill_id="s",
            skill_version="v1",
            skill_package_hash="h",
            runtime_provider="mock",
            runtime_model="m",
            content_object_id=store.write_text_object("# Script\n\n## Scene\nBody"),
            content_hash="h",
            raw_response_object_id=store.write_text_object("{}"),
            parser_version="p",
        )
        timeout_py = tmp_path / "timeout.py"
        pass_py = tmp_path / "pass.py"
        timeout_py.write_text("print('timeout')\n", encoding="utf-8")
        pass_py.write_text("print('ok')\n", encoding="utf-8")
        calls = []

        def fake_run(command, **kwargs):
            calls.append(command)
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(command, timeout=1, output=b"partial-\xff-out", stderr=b"partial-\xff-err")
            return subprocess.CompletedProcess(command, 0, "after\n", "")

        monkeypatch.setattr("ai_drama_runtime.validators.subprocess.run", fake_run)
        package = type(
            "Pkg",
            (),
            {
                "validators": [
                    SkillValidator("timeout", "timeout", timeout_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass"),
                    SkillValidator("pass", "pass", pass_py, False, ["drama_script_revision"], ["{python}", "{entrypoint}"], [], 1, "zero_is_pass"),
                ],
                "root": tmp_path,
            },
        )()

        results = run_declared_validators(store, package, revision, tmp_path, repo_root=tmp_path)
        by_id = {item.validator_id: item for item in results}

        assert by_id["timeout"].status == "FAIL"
        assert by_id["timeout"].error_code == "VALIDATOR_TIMEOUT"
        assert store.read_text(by_id["timeout"].stdout_object_id) == "partial-\ufffd-out"
        assert store.read_text(by_id["timeout"].stderr_object_id) == "partial-\ufffd-err"
        assert by_id["pass"].status == "PASS"


def test_bundle_integrity_passes_valid_bundle(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)

        result = service.check_storyboard_bundle_integrity(revision.revision_id)

        assert result["status"] == "PASS"
        assert result["bundle_manifest_hash"]


def test_bundle_integrity_reports_missing_bundle(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)

        with pytest.raises(BundleError) as exc:
            service.check_storyboard_bundle_integrity(revision.revision_id)

        assert exc.value.code == "BUNDLE_NOT_MATERIALIZED"


def test_bundle_integrity_reports_revision_output_hash_mismatch(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        markdown = service.store.get_revision_output(revision.revision_id, "rendered_markdown")
        service.store.conn.execute(
            "UPDATE revision_outputs SET content_hash = ? WHERE revision_output_id = ?",
            ("0" * 64, markdown.revision_output_id),
        )
        service.store.conn.commit()

        with pytest.raises(BundleError) as exc:
            service.check_storyboard_bundle_integrity(revision.revision_id)

        assert exc.value.code == "REVISION_OUTPUT_HASH_MISMATCH"


def test_bundle_integrity_reports_invalid_output_combination(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)
        object_id = service.store.write_text_object("prompt")
        service.store.insert_revision_outputs_transaction(
            [
                {
                    "revision_id": revision.revision_id,
                    "logical_type": "rendered_positive_prompt",
                    "object_id": object_id,
                    "content_hash": object_id,
                    "media_type": "text/plain",
                    "generator": "legacy",
                    "generator_version": "1",
                },
                {
                    "revision_id": revision.revision_id,
                    "logical_type": "rendered_negative_prompt",
                    "object_id": object_id,
                    "content_hash": object_id,
                    "media_type": "text/plain",
                    "generator": "legacy",
                    "generator_version": "1",
                },
            ]
        )
        service.store.conn.commit()

        with pytest.raises(BundleError) as exc:
            service.check_storyboard_bundle_integrity(revision.revision_id)

        assert exc.value.code == "REVISION_OUTPUT_COMBINATION_INVALID"


def test_bundle_integrity_reports_renderer_byte_or_metadata_failure(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        markdown = service.store.get_revision_output(revision.revision_id, "rendered_markdown")
        service.store.conn.execute(
            "UPDATE revision_outputs SET generator_version = ? WHERE revision_output_id = ?",
            ("9.9.9", markdown.revision_output_id),
        )
        service.store.conn.commit()

        with pytest.raises(BundleError) as exc:
            service.check_storyboard_bundle_integrity(revision.revision_id)

        assert exc.value.code == "BUNDLE_INTEGRITY_FAILED"


def test_bundle_integrity_reports_manifest_semantic_failure(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        manifest_output = service.store.get_revision_output(revision.revision_id, "bundle_manifest")
        manifest = json.loads(service.store.read_text(manifest_output.object_id))
        manifest["bundle_manifest_hash"] = "0" * 64
        _set_output_object(service, manifest_output, service._canonical_json_v1_bytes(manifest))

        with pytest.raises(BundleError) as exc:
            service.check_storyboard_bundle_integrity(revision.revision_id)

        assert exc.value.code == "BUNDLE_INTEGRITY_FAILED"


def test_v020_uses_live_bundle_integrity_checker(tmp_path, monkeypatch):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        calls = []
        original = service.check_storyboard_bundle_integrity

        def wrapped(revision_id):
            calls.append(revision_id)
            return original(revision_id)

        monkeypatch.setattr(service, "check_storyboard_bundle_integrity", wrapped)

        result = service.materialize_storyboard_bundle(revision.revision_id)

        assert result["status"] == "ALREADY_MATERIALIZED"
        assert calls == [revision.revision_id]


def test_approval_blocks_missing_bundle(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)

        with pytest.raises(BundleError) as exc:
            service.approve_revision(revision.revision_id, "tester")

        assert exc.value.code == "BUNDLE_NOT_MATERIALIZED"
        assert service.store.get_revision(revision.revision_id).approval_status == "pending"


def test_approval_blocks_invalid_bundle(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        markdown = service.store.get_revision_output(revision.revision_id, "rendered_markdown")
        service.store.conn.execute(
            "UPDATE revision_outputs SET generator = ? WHERE revision_output_id = ?",
            ("wrong-renderer", markdown.revision_output_id),
        )
        service.store.conn.commit()

        with pytest.raises(BundleError) as exc:
            service.approve_revision(revision.revision_id, "tester")

        assert exc.value.code == "BUNDLE_INTEGRITY_FAILED"
        assert service.store.get_revision(revision.revision_id).approval_status == "pending"


def test_approval_does_not_implicitly_materialize_bundle(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)

        with pytest.raises(BundleError) as exc:
            service.approve_revision(revision.revision_id, "tester")

        assert exc.value.code == "BUNDLE_NOT_MATERIALIZED"
        assert service.store.revision_outputs(revision.revision_id) == []


def test_existing_approved_phase1_revision_is_not_revoked(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        service.materialize_storyboard_bundle(revision.revision_id)
        service.approve_revision(revision.revision_id, "tester")
        assert service.store.get_revision(revision.revision_id).approval_status == "approved"

        service.store.conn.execute("DELETE FROM revision_outputs WHERE revision_id = ?", (revision.revision_id,))
        service.store.conn.commit()

        assert service.store.get_revision(revision.revision_id).approval_status == "approved"
        assert service.current_approved(revision.artifact_id).revision_id == revision.revision_id


def test_diagnostic_export_cannot_be_dependency_parent(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        service.store.conn.execute(
            "UPDATE revision_dependencies SET parent_content_hash = ? WHERE child_revision_id = ?",
            ("0" * 64, revision.revision_id),
        )
        service.store.conn.commit()
        result = service.export_storyboard_bundle(revision.revision_id, "diagnostic", tmp_path / "diagnostic-export")

        with pytest.raises(DiagnosticParentError) as exc:
            service.attach_export_dependency("child-revision", result["export_id"], "derived_from_export")

        assert exc.value.code == "DIAGNOSTIC_EXPORT_NOT_PARENTABLE"


def test_formal_review_export_records_success_only_after_atomic_completion(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        result = service.export_storyboard_bundle(revision.revision_id, "formal-review", tmp_path / "formal-review")
        export = service.store.get_export_record(result["export_id"])

        assert result["status"] == "EXPORTED"
        assert result["export_kind"] == "formal_review"
        assert result["diagnostic_only"] is False
        assert result["not_an_execution_package"] is True
        assert result["execution_ready"] is False
        assert export.export_kind == "formal_review"
        assert export.content_hash == revision.content_hash
        assert export.bundle_manifest_hash == result["bundle_manifest_hash"]
        assert export.error_code == ""
        assert not hasattr(export, "status")


def test_formal_review_export_is_atomic(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        output = tmp_path / "bundle-export"

        result = service.export_storyboard_bundle(revision.revision_id, "formal-review", output)

        assert result["status"] == "EXPORTED"
        assert sorted(path.name for path in output.iterdir()) == [
            "bundle-manifest.json",
            "canonical-content.json",
            "export-provenance.json",
            "rendered-markdown.md",
        ]
        manifest_output = service.store.get_revision_output(revision.revision_id, "bundle_manifest")
        markdown_output = service.store.get_revision_output(revision.revision_id, "rendered_markdown")
        assert (output / "canonical-content.json").read_bytes() == service.store.read_bytes_object(revision.content_object_id)
        assert (output / "rendered-markdown.md").read_bytes() == service.store.read_bytes_object(markdown_output.object_id)
        assert (output / "bundle-manifest.json").read_bytes() == service.store.read_bytes_object(manifest_output.object_id)
        provenance = json.loads((output / "export-provenance.json").read_text(encoding="utf-8"))
        assert provenance["schema_version"] == "export-provenance-v1"
        assert provenance["export_kind"] == "formal_review"
        assert provenance["canonical_content_hash"] == revision.content_hash
        assert provenance["bundle_manifest_hash"] == result["bundle_manifest_hash"]
        assert provenance["bundle_status"] == "verified"
        assert provenance["error_code"] == ""


def test_formal_review_export_rolls_back_audit_when_rename_fails(tmp_path, monkeypatch):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        output = tmp_path / "rename-fail"

        def fail_replace(src, dst):
            raise OSError("simulated rename failure")

        monkeypatch.setattr("ai_drama_runtime.services.os.replace", fail_replace)

        with pytest.raises(BundleExportError):
            service.export_storyboard_bundle(revision.revision_id, "formal-review", output)

        assert not output.exists()
        assert [item for item in service.store.export_records(revision.artifact_id) if item.export_kind == "formal_review"] == []
        assert [path for path in tmp_path.iterdir() if path.name.startswith(".rename-fail.")] == []


def test_formal_review_export_compensates_final_directory_when_commit_fails(tmp_path, monkeypatch):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        output = tmp_path / "commit-fail"

        def fail_commit():
            raise RuntimeError("simulated commit failure")

        monkeypatch.setattr(service, "_commit_export_transaction", fail_commit)

        with pytest.raises(BundleExportError):
            service.export_storyboard_bundle(revision.revision_id, "formal-review", output)

        assert not output.exists()
        assert [item for item in service.store.export_records(revision.artifact_id) if item.export_kind == "formal_review"] == []


def test_formal_review_export_blocks_missing_bundle_before_general_gate(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)

        with pytest.raises(BundleError) as exc:
            service.export_storyboard_bundle(revision.revision_id, "formal-review", tmp_path / "blocked")

        assert exc.value.code == "BUNDLE_NOT_MATERIALIZED"
        assert not (tmp_path / "blocked").exists()


def test_formal_review_export_blocks_invalid_bundle_before_general_gate(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service)
        markdown = service.store.get_revision_output(revision.revision_id, "rendered_markdown")
        service.store.conn.execute(
            "UPDATE revision_outputs SET generator = ? WHERE revision_output_id = ?",
            ("wrong-renderer", markdown.revision_output_id),
        )
        service.store.conn.commit()

        with pytest.raises(BundleError) as exc:
            service.export_storyboard_bundle(revision.revision_id, "formal-review", tmp_path / "blocked")

        assert exc.value.code == "BUNDLE_INTEGRITY_FAILED"
        assert not (tmp_path / "blocked").exists()


def test_formal_review_export_blocks_unapproved_stale_or_failed_validator(tmp_path):
    with _service(tmp_path) as service:
        unapproved = _canonical_storyboard_revision(service)

        with pytest.raises(BundleExportError) as exc:
            service.export_storyboard_bundle(unapproved.revision_id, "formal-review", tmp_path / "unapproved")

        assert exc.value.code == "FORMAL_REVIEW_EXPORT_BLOCKED"
        assert not (tmp_path / "unapproved").exists()

        service.approve_revision(unapproved.revision_id, "tester")
        service.store.conn.execute(
            "UPDATE revision_dependencies SET parent_content_hash = ? WHERE child_revision_id = ?",
            ("0" * 64, unapproved.revision_id),
        )
        service.store.conn.commit()
        with pytest.raises(BundleExportError) as stale_exc:
            service.export_storyboard_bundle(unapproved.revision_id, "formal-review", tmp_path / "stale")
        assert stale_exc.value.code == "FORMAL_REVIEW_EXPORT_BLOCKED"
        assert not (tmp_path / "stale").exists()

        service.store.conn.execute(
            "UPDATE revision_dependencies SET parent_content_hash = ? WHERE child_revision_id = ?",
            (service.store.get_revision(service.revision_source_revision_id(unapproved.revision_id)).content_hash, unapproved.revision_id),
        )
        service.store.conn.execute(
            "UPDATE validation_results SET status = ?, error_code = ? WHERE revision_id = ? AND validator_id = ?",
            ("FAIL", "FORCED_FAIL", unapproved.revision_id, "storyboard_canonical_schema"),
        )
        service.store.conn.commit()
        with pytest.raises(BundleExportError) as validator_exc:
            service.export_storyboard_bundle(unapproved.revision_id, "formal-review", tmp_path / "failed-validator")
        assert validator_exc.value.code == "FORMAL_REVIEW_EXPORT_BLOCKED"
        assert not (tmp_path / "failed-validator").exists()
        assert [item for item in service.store.export_records(unapproved.artifact_id) if item.destination.endswith("failed-validator")] == []


def test_formal_review_export_rejects_existing_destination(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        output = tmp_path / "exists"
        output.mkdir()

        with pytest.raises(BundleExportError) as exc:
            service.export_storyboard_bundle(revision.revision_id, "formal-review", output)

        assert exc.value.code == "EXPORT_DESTINATION_EXISTS"


def test_diagnostic_export_requires_stale_revision(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)

        with pytest.raises(BundleExportError) as exc:
            service.export_storyboard_bundle(revision.revision_id, "diagnostic", tmp_path / "fresh-diagnostic")

        assert exc.value.code == "DIAGNOSTIC_EXPORT_REQUIRES_STALE"

        service.store.conn.execute(
            "UPDATE revision_dependencies SET parent_content_hash = ? WHERE child_revision_id = ?",
            ("0" * 64, revision.revision_id),
        )
        service.store.conn.commit()
        result = service.export_storyboard_bundle(revision.revision_id, "diagnostic", tmp_path / "stale-diagnostic")
        assert result["status"] == "EXPORTED"
        assert result["diagnostic_only"] is True
        assert result["freshness_status"] == "STALE"


def test_execution_export_records_block_without_filesystem_writes(tmp_path):
    with _service(tmp_path) as service:
        revision = _approved_bundle_revision(service)
        output = tmp_path / "execution"

        result = service.export_storyboard_bundle(revision.revision_id, "execution", output)

        assert result["status"] == "BLOCKED"
        assert result["export_kind"] == "execution"
        assert result["bundle_status"] == "verified"
        assert result["bundle_manifest_hash"]
        assert result["error_code"] == "EXPORT_NOT_EXECUTION_READY"
        assert not output.exists()


def test_execution_export_persists_blocked_attempt_without_filesystem_writes(tmp_path):
    with _service(tmp_path) as service:
        revision = _canonical_storyboard_revision(service, materialize=False)
        output = tmp_path / "execution-missing"

        result = service.export_storyboard_bundle(revision.revision_id, "execution", output)
        export = service.store.get_export_record(result["export_id"])

        assert result["status"] == "BLOCKED"
        assert result["bundle_status"] == "not_materialized"
        assert result["bundle_manifest_hash"] == ""
        assert export.export_kind == "execution"
        assert export.destination == str(output)
        assert export.content_hash == revision.content_hash
        assert export.bundle_manifest_hash == ""
        assert export.error_code == "EXPORT_NOT_EXECUTION_READY"
        assert export.not_an_execution_package is True
        assert export.execution_ready is False
        assert export.provenance_object_id
        provenance = json.loads(service.store.read_text(export.provenance_object_id))
        assert provenance["export_kind"] == "execution"
        assert provenance["bundle_status"] == "not_materialized"
        assert provenance["error_code"] == "EXPORT_NOT_EXECUTION_READY"
        assert not output.exists()
