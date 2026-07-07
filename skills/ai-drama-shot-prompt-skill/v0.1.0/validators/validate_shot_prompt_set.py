#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


VALIDATOR_ID = "shot_prompt_set_structure"


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


def _shot_prompt_module(repo_root):
    root = Path(repo_root).resolve()
    module_path = root / "ai_drama_runtime" / "shot_prompt_canonical.py"
    if not module_path.is_file():
        raise ValidatorFailure(
            "SHOT_PROMPT_VALIDATOR_IMPORT_FAILED",
            "repo root does not contain ai_drama_runtime/shot_prompt_canonical.py",
        )
    spec = importlib.util.spec_from_file_location("ai_drama_runtime.shot_prompt_canonical", module_path)
    if spec is None or spec.loader is None:
        raise ValidatorFailure("SHOT_PROMPT_VALIDATOR_IMPORT_FAILED", "failed to load shot prompt canonical module")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ValidatorFailure(
            "SHOT_PROMPT_VALIDATOR_IMPORT_FAILED",
            "failed to import shot prompt canonical module: %s" % exc.__class__.__name__,
        ) from exc
    return module


def _write_report(path, report):
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _require_string(value, code, message):
    if not isinstance(value, str) or not value:
        raise ValidatorFailure(code, message)


def _validate_dialogue(shots):
    for shot_index, shot in enumerate(shots):
        for line_index, line in enumerate(shot["dialogue"]):
            if not isinstance(line, dict):
                raise ValidatorFailure(
                    "SHOT_PROMPT_DIALOGUE_INVALID",
                    "shots[%d].dialogue[%d] must be an object" % (shot_index, line_index),
                )
            _require_string(
                line.get("speaker_character_id"),
                "SHOT_PROMPT_DIALOGUE_INVALID",
                "shots[%d].dialogue[%d].speaker_character_id must be a non-empty string"
                % (shot_index, line_index),
            )
            _require_string(
                line.get("text"),
                "SHOT_PROMPT_DIALOGUE_INVALID",
                "shots[%d].dialogue[%d].text must be a non-empty string" % (shot_index, line_index),
            )


def _validate_consistency(data):
    seen_shot_ids = set()
    for index, shot in enumerate(data["shots"]):
        shot_id = shot["shot_id"]
        if shot_id in seen_shot_ids:
            raise ValidatorFailure("SHOT_PROMPT_MAPPING_INVALID", "duplicate shot_id: %s" % shot_id)
        seen_shot_ids.add(shot_id)
        if len(set(shot["asset_refs"])) != len(shot["asset_refs"]):
            raise ValidatorFailure(
                "SHOT_PROMPT_ASSET_REFS_INVALID",
                "shots[%d].asset_refs must not contain duplicates" % index,
            )
        preview_duration = shot["agnes_video_params"].get("duration_seconds")
        if preview_duration is not None and preview_duration != shot["duration_seconds"]:
            raise ValidatorFailure(
                "SHOT_PROMPT_DURATION_INVALID",
                "shots[%d].agnes_video_params.duration_seconds must match duration_seconds" % index,
            )
    _validate_dialogue(data["shots"])


def main(argv=None):
    args = _parse_args()
    report = {"validator_id": VALIDATOR_ID, "status": "PASS"}
    try:
        module = _shot_prompt_module(args.repo_root)
    except ValidatorFailure as exc:
        report.update({"status": "FAIL", "error_code": exc.code, "message": exc.safe_message})
        _write_report(args.report, report)
        print("%s FAIL %s" % (VALIDATOR_ID, exc.code))
        return 1
    try:
        data = module.parse_shot_prompt_json(Path(args.revision).read_bytes())
        module.validate_shot_prompt_canonical(data)
        _validate_consistency(data)
        report["canonical_hash"] = module.shot_prompt_content_hash(data)
    except module.CanonicalShotPromptError as exc:
        report.update({"status": "FAIL", "error_code": exc.code, "message": exc.safe_message})
        _write_report(args.report, report)
        print("%s FAIL %s" % (VALIDATOR_ID, exc.code))
        return 1
    except ValidatorFailure as exc:
        report.update({"status": "FAIL", "error_code": exc.code, "message": exc.safe_message})
        _write_report(args.report, report)
        print("%s FAIL %s" % (VALIDATOR_ID, exc.code))
        return 1
    _write_report(args.report, report)
    print("%s PASS" % VALIDATOR_ID)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
