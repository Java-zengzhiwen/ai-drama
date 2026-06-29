import argparse
import json
from pathlib import Path
import sys

from .acceptance import AcceptanceError
from .manifest import SkillManifestError
from .registry import DuplicateSkillError, SkillNotFoundError, SkillRegistry
from .runtime import RuntimeErrorBase
from .services import ApprovalBlocked, ExportConflict, NotFound, RuntimeService, WorkflowGateError
from .store import RuntimeStore


EXIT_INVALID = 2
EXIT_NOT_FOUND = 3
EXIT_RUNTIME = 4
EXIT_VALIDATION = 5
EXIT_APPROVAL = 6


def _json(data):
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))


def _store(args):
    return RuntimeStore(Path(args.data_root) / "runtime.db", Path(args.data_root) / "objects")


def _service(args):
    return RuntimeService(_store(args), repo_root=Path.cwd())


def _with_store(args, fn):
    store = _store(args)
    try:
        return fn(store)
    finally:
        store.close()


def _with_service(args, fn):
    service = _service(args)
    try:
        return fn(service)
    finally:
        service.close()


def _registry(args):
    return SkillRegistry.scan([args.skills_root])


def _skills_list(args):
    registry = _registry(args)
    _json(registry.list())


def _skills_show(args):
    _json(_registry(args).show(args.skill_ref))


def _skills_validate(args):
    _json(_registry(args).validate(args.skill_ref))


def _run_create(args):
    registry = _registry(args)
    package = registry.get_ref(args.skill)
    mode = "source_revision" if args.source_revision is not None else "input" if args.input is not None else ""
    result = _with_service(
        args,
        lambda service: service.run_storyboard(
            package,
            args.source_revision,
            args.runtime,
            args.model,
            mock_mode=args.mock_mode,
        )
        if mode == "source_revision"
        else service.run_acceptance(
            package,
            args.input,
            args.runtime,
            args.model,
            mock_mode=args.mock_mode,
        ),
    )
    payload = {
        "run_id": result.run.run_id,
        "status": result.run.status,
        "artifact_id": result.run.artifact_id,
        "revision_id": result.revision.revision_id if result.revision else "",
        "error_code": result.run.error_code,
        "validation": [
            {
                "validator_id": item.validator_id,
                "status": item.status,
                "required": item.required,
                "error_code": item.error_code,
            }
            for item in result.validation_results
        ],
    }
    _json(payload)
    if result.run.status in {"RUNTIME_FAILED", "PARSE_FAILED"}:
        return EXIT_RUNTIME
    if result.run.status == "VALIDATION_FAILED":
        return EXIT_VALIDATION
    return 0


def _runs_show(args):
    run = _with_store(args, lambda store: store.get_run(args.run_id))
    if not run:
        raise NotFound("run not found: %s" % args.run_id)
    _json(run.__dict__)


def _artifacts_list(args):
    _json(_with_store(args, lambda store: store.artifacts()))


def _artifacts_revisions(args):
    _json(_with_store(args, lambda store: [item.__dict__ for item in store.revisions_for_artifact(args.artifact_id)]))


def _artifacts_compare(args):
    sys.stdout.write(_with_service(args, lambda service: service.compare_revisions(args.left_revision_id, args.right_revision_id)))


def _artifacts_approved(args):
    revision = _with_service(args, lambda service: service.current_approved(args.artifact_id))
    payload = revision.__dict__.copy()
    payload["freshness_status"] = _with_service(args, lambda service: service.revision_freshness(revision.revision_id))
    payload["source_script_revision_id"] = _with_service(args, lambda service: service.revision_source_revision_id(revision.revision_id))
    _json(payload)


def _artifacts_export(args):
    _json(_with_service(args, lambda service: service.export_approved(args.artifact_id, args.output, force=args.force).__dict__))


def _storyboard_render(args):
    _json(_with_service(args, lambda service: service.render_storyboard_revision(args.revision, args.output)))


def _storyboard_migrate_legacy(args):
    if args.preview:
        _json(_with_service(args, lambda service: service.preview_legacy_storyboard_migration(args.source_revision, args.output)))
        return 0
    _json(
        _with_service(
            args,
            lambda service: service.confirm_legacy_storyboard_migration(
                args.source_revision,
                args.confirm_candidate_hash,
                args.output,
            ),
        )
    )
    return 0


def _approvals_approve(args):
    revision = _with_service(args, lambda service: service.approve_revision(args.revision_id, args.reviewer, args.note))
    _json({"revision_id": revision.revision_id, "artifact_id": revision.artifact_id, "approval_status": revision.approval_status})


def _approvals_reject(args):
    revision = _with_service(args, lambda service: service.reject_revision(args.revision_id, args.reviewer, args.note))
    _json({"revision_id": revision.revision_id, "artifact_id": revision.artifact_id, "approval_status": revision.approval_status})


def build_parser():
    parser = argparse.ArgumentParser(prog="ai-drama")
    parser.add_argument("--data-root", default="runtime-data")
    parser.add_argument("--skills-root", default="skills")
    sub = parser.add_subparsers(dest="command", required=True)

    skills = sub.add_parser("skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    p = skills_sub.add_parser("list")
    p.set_defaults(func=_skills_list)
    p = skills_sub.add_parser("show")
    p.add_argument("skill_ref")
    p.set_defaults(func=_skills_show)
    p = skills_sub.add_parser("validate")
    p.add_argument("skill_ref")
    p.set_defaults(func=_skills_validate)

    run = sub.add_parser("run")
    run_sub = run.add_subparsers(dest="run_command", required=True)
    p = run_sub.add_parser("create")
    p.add_argument("--skill", required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input")
    mode.add_argument("--source-revision")
    p.add_argument("--runtime", choices=["mock", "openai-compatible"], default="mock")
    p.add_argument("--model", default="")
    p.add_argument("--mock-mode", choices=["success", "runtime_failure", "empty_response", "parse_failure"], default="success")
    p.set_defaults(func=_run_create)

    runs = sub.add_parser("runs")
    runs_sub = runs.add_subparsers(dest="runs_command", required=True)
    p = runs_sub.add_parser("show")
    p.add_argument("run_id")
    p.set_defaults(func=_runs_show)

    artifacts = sub.add_parser("artifacts")
    art_sub = artifacts.add_subparsers(dest="artifacts_command", required=True)
    p = art_sub.add_parser("list")
    p.set_defaults(func=_artifacts_list)
    p = art_sub.add_parser("revisions")
    p.add_argument("artifact_id")
    p.set_defaults(func=_artifacts_revisions)
    p = art_sub.add_parser("compare")
    p.add_argument("left_revision_id")
    p.add_argument("right_revision_id")
    p.set_defaults(func=_artifacts_compare)
    p = art_sub.add_parser("approved")
    p.add_argument("artifact_id")
    p.set_defaults(func=_artifacts_approved)
    p = art_sub.add_parser("export-approved")
    p.add_argument("artifact_id")
    p.add_argument("--output", required=True)
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=_artifacts_export)

    storyboard = sub.add_parser("storyboard")
    storyboard_sub = storyboard.add_subparsers(dest="storyboard_command", required=True)
    p = storyboard_sub.add_parser("render")
    p.add_argument("--revision", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=_storyboard_render)
    p = storyboard_sub.add_parser("migrate-legacy")
    p.add_argument("--source-revision", required=True)
    migration_mode = p.add_mutually_exclusive_group(required=True)
    migration_mode.add_argument("--preview", action="store_true")
    migration_mode.add_argument("--confirm-candidate-hash")
    p.add_argument("--output", required=True)
    p.set_defaults(func=_storyboard_migrate_legacy)

    approvals = sub.add_parser("approvals")
    appr_sub = approvals.add_subparsers(dest="approvals_command", required=True)
    p = appr_sub.add_parser("approve")
    p.add_argument("revision_id")
    p.add_argument("--reviewer", default="local-user")
    p.add_argument("--note", default="")
    p.set_defaults(func=_approvals_approve)
    p = appr_sub.add_parser("reject")
    p.add_argument("revision_id")
    p.add_argument("--reviewer", default="local-user")
    p.add_argument("--note", default="")
    p.set_defaults(func=_approvals_reject)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
        return code or 0
    except WorkflowGateError as exc:
        _json({"error_code": exc.code, "error_message": exc.safe_message})
        return EXIT_INVALID
    except (ValueError, SkillManifestError, AcceptanceError) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INVALID
    except (SkillNotFoundError, DuplicateSkillError, NotFound, ExportConflict) as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_NOT_FOUND
    except RuntimeErrorBase as exc:
        print(exc.safe_message, file=sys.stderr)
        return EXIT_RUNTIME
    except ApprovalBlocked as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_APPROVAL


if __name__ == "__main__":
    raise SystemExit(main())
