#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class ValidatorFailure(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.safe_message = message


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--repo-root", required=True)
    return parser.parse_args()


def _storyboard_module(repo_root):
    root = str(Path(repo_root).resolve())
    if root not in sys.path:
        sys.path.insert(0, root)
    from ai_drama_runtime import storyboard_canonical

    return storyboard_canonical


def _write_report(path, report):
    Path(path).write_text(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _require_object(value, code, message):
    if not isinstance(value, dict):
        raise ValidatorFailure(code, message)


def _require_array(value, code, message):
    if not isinstance(value, list):
        raise ValidatorFailure(code, message)


def _require_int(value, code, message):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValidatorFailure(code, message)


def fail(code, message):
    raise ValidatorFailure(code, message)


def run_validator(validator_id, validate):
    args = _parse_args()
    module = _storyboard_module(args.repo_root)
    report = {"validator_id": validator_id, "final_status": "pass"}
    try:
        data = module.parse_canonical_json(Path(args.revision).read_bytes())
        extra = validate(data, module) or {}
        report.update(extra)
    except module.CanonicalStoryboardError as exc:
        report.update({"final_status": "fail", "error_code": exc.code, "message": exc.safe_message})
        _write_report(args.report, report)
        print("%s FAIL %s" % (validator_id, exc.code))
        return 1
    except ValidatorFailure as exc:
        report.update({"final_status": "fail", "error_code": exc.code, "message": exc.safe_message})
        _write_report(args.report, report)
        print("%s FAIL %s" % (validator_id, exc.code))
        return 1
    _write_report(args.report, report)
    print("%s PASS" % validator_id)
    return 0


def require_object(value, code="CANONICAL_SCHEMA_INVALID", message="value must be an object"):
    _require_object(value, code, message)


def require_array(value, code="CANONICAL_SCHEMA_INVALID", message="value must be an array"):
    _require_array(value, code, message)


def require_int(value, code="CANONICAL_SCHEMA_INVALID", message="value must be an integer"):
    _require_int(value, code, message)
