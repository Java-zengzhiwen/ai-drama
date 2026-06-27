import argparse
import json
from pathlib import Path
import sys

from .manifest import discover_skill_packages, load_skill_package
from .services import ApprovalBlocked, NotFound, RuntimeService
from .store import RuntimeStore


def _json(data):
    print(json.dumps(data, ensure_ascii=False, sort_keys=True))


def _service(args):
    return RuntimeService(RuntimeStore(args.store, args.objects), repo_root=Path.cwd())


def _skills_list(args):
    packages = discover_skill_packages(args.skills_root)
    _json([_package_json(package) for package in packages])


def _skills_validate(args):
    package = load_skill_package(args.skill_root)
    if args.version and package.version != args.version:
        raise ValueError(
            "skill version mismatch: expected %s, found %s" % (args.version, package.version)
        )
    _json(_package_json(package))


def _package_json(package):
    return {
        "skill_id": package.skill_id,
        "version": package.version,
        "root": str(package.root),
        "instructions_entry": str(package.instructions_entry),
        "content_hash": package.content_hash,
        "validators": [
            {
                "name": item.name,
                "entrypoint": str(item.entrypoint),
                "required": item.required,
                "executable": bool(item.command),
            }
            for item in package.validators
        ],
    }


def _run(args):
    service = _service(args)
    package = load_skill_package(args.skill_root)
    result = service.run_acceptance(
        skill=package,
        acceptance_root=args.acceptance_root,
        runtime=args.runtime,
        model=args.model,
    )
    _json(
        {
            "status": result.run.status,
            "run_id": result.run.run_id,
            "revision_id": result.revision.revision_id,
            "artifact_id": result.revision.artifact_id,
            "validation": [
                {
                    "name": item.validator_name,
                    "status": item.status,
                    "required": item.required,
                    "exit_code": item.exit_code,
                }
                for item in result.validation_results
            ],
        }
    )


def _approve(args):
    revision = _service(args).approve_revision(args.revision_id, args.reviewer, args.note)
    _json({"revision_id": revision.revision_id, "artifact_id": revision.artifact_id, "approval_status": revision.approval_status})


def _reject(args):
    revision = _service(args).reject_revision(args.revision_id, args.reviewer, args.note)
    _json({"revision_id": revision.revision_id, "artifact_id": revision.artifact_id, "approval_status": revision.approval_status})


def _approved(args):
    revision = _service(args).current_approved(args.artifact_id)
    _json(revision.__dict__)


def _compare(args):
    sys.stdout.write(_service(args).compare_revisions(args.left_revision_id, args.right_revision_id))


def _export(args):
    record = _service(args).export_approved(args.artifact_id, args.output)
    _json(record.__dict__)


def build_parser():
    parser = argparse.ArgumentParser(prog="ai-drama")
    parser.add_argument("--store", default="runtime-data/runtime.db")
    parser.add_argument("--objects", default="runtime-data/objects")
    sub = parser.add_subparsers(dest="command", required=True)

    skills = sub.add_parser("skills")
    skills_sub = skills.add_subparsers(dest="skills_command", required=True)
    skills_list = skills_sub.add_parser("list")
    skills_list.add_argument("--skills-root", default="skills")
    skills_list.set_defaults(func=_skills_list)
    skills_validate = skills_sub.add_parser("validate")
    skills_validate.add_argument("--skill-root", required=True)
    skills_validate.add_argument("--version")
    skills_validate.set_defaults(func=_skills_validate)

    run = sub.add_parser("run")
    run.add_argument("--skill-root", required=True)
    run.add_argument("--acceptance-root", required=True)
    run.add_argument("--runtime", choices=["mock", "openai", "openai-compatible"], default="mock")
    run.add_argument("--model", default="mock-script-v1")
    run.set_defaults(func=_run)

    approve = sub.add_parser("approve")
    approve.add_argument("revision_id")
    approve.add_argument("--reviewer", default="local-user")
    approve.add_argument("--note", default="")
    approve.set_defaults(func=_approve)

    reject = sub.add_parser("reject")
    reject.add_argument("revision_id")
    reject.add_argument("--reviewer", default="local-user")
    reject.add_argument("--note", default="")
    reject.set_defaults(func=_reject)

    approved = sub.add_parser("approved")
    approved.add_argument("artifact_id")
    approved.set_defaults(func=_approved)

    compare = sub.add_parser("compare")
    compare.add_argument("left_revision_id")
    compare.add_argument("right_revision_id")
    compare.set_defaults(func=_compare)

    export = sub.add_parser("export")
    export.add_argument("artifact_id")
    export.add_argument("--output", required=True)
    export.set_defaults(func=_export)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ApprovalBlocked, NotFound, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
