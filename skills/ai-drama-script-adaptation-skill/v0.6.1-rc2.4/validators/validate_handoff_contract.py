#!/usr/bin/env python3
from common import *

REQUIRED_INPUT_REFS=[
    "source_chapter",
    "worldbuilding",
    "characters",
    "project_brief",
]
REQUIRED_OUTPUT_REFS=[
    "script_markdown",
    "script_json",
    "coverage_report",
    "production_assumption_log",
    "source_conflict_registry",
    "adaptation_extension_registry",
    "schema_validation_report",
    "evidence_sidecar",
    "creator_presentation",
    "source_claim_audit",
]

def ref_path(ref):
    if isinstance(ref, str):
        return ref
    if isinstance(ref, dict):
        return ref.get("path") or ref.get("relative_path") or ref.get("evidence_relative_path")
    return None

def validate_ref_group(group, required_keys, base_dir, report_path, group_name, allow_extra=False):
    if not isinstance(group, dict):
        emit("fail","ERR_HANDOFF_REFS",group_name+" must be object",report_path)
    missing=[k for k in required_keys if k not in group]
    extra=[] if allow_extra else [k for k in group if k not in required_keys]
    if missing or extra:
        emit("fail","ERR_HANDOFF_REFS","handoff refs do not match required keys",report_path,group=group_name,missing=missing,extra=extra)
    keys = list(group.keys()) if allow_extra else required_keys
    for key in keys:
        ref=group.get(key)
        path_value=ref_path(ref)
        if not path_value:
            emit("fail","ERR_HANDOFF_REFS","handoff ref path missing",report_path,group=group_name,key=key)
        target=resolve(base_dir,path_value)
        if not target.exists() or not target.is_file():
            emit("fail","ERR_HANDOFF_REFS","handoff ref file does not exist",report_path,group=group_name,key=key,path=path_value)
        expected_hash=ref.get("sha256") if isinstance(ref, dict) else None
        if not expected_hash or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            emit("fail","ERR_HANDOFF_REFS","handoff ref sha256 missing or invalid",report_path,group=group_name,key=key,path=path_value)
        if sha256(target) != expected_hash:
            emit("fail","ERR_HANDOFF_REFS","handoff ref sha256 mismatch",report_path,group=group_name,key=key,path=path_value)

def validate_single_ref(ref, base_dir, report_path, key):
    path_value=ref_path(ref)
    if not path_value:
        emit("fail","ERR_HANDOFF_REFS","handoff ref path missing",report_path,group="top_level_refs",key=key)
    target=resolve(base_dir,path_value)
    if not target.exists() or not target.is_file():
        emit("fail","ERR_HANDOFF_REFS","handoff ref file does not exist",report_path,group="top_level_refs",key=key,path=path_value)
    expected_hash=ref.get("sha256") if isinstance(ref, dict) else None
    if not expected_hash or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        emit("fail","ERR_HANDOFF_REFS","handoff ref sha256 missing or invalid",report_path,group="top_level_refs",key=key,path=path_value)
    if sha256(target) != expected_hash:
        emit("fail","ERR_HANDOFF_REFS","handoff ref sha256 mismatch",report_path,group="top_level_refs",key=key,path=path_value)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--handoff", required=True); ap.add_argument("--base-dir", default=None); ap.add_argument("--report", required=True); args=ap.parse_args(); h=load_json(args.handoff)
    base_dir=Path(args.base_dir) if args.base_dir else Path(args.handoff).resolve().parent
    required=["project_id","chapter_id","artifact_version","source_fingerprint","created_at","updated_at","input_refs","output_refs","validation_report_ref","stage_result_ref","stale_status","blocking_issues","handoff_status","approved_for_downstream","current_gate"]
    for k in required:
        if k not in h: emit("fail","ERR_HANDOFF_CONTRACT","missing handoff field",args.report,field=k)
    if h.get("approved_for_downstream") is not False: emit("fail","ERR_DOWNSTREAM_APPROVAL","approved_for_downstream must remain false",args.report)
    allowed_handoff_status={"pending_script_approval","script_approved_downstream_unauthorized"}
    if h.get("current_gate") != "SCRIPT_APPROVAL" or h.get("handoff_status") not in allowed_handoff_status or h.get("stale_status") != "fresh":
        emit("fail","ERR_HANDOFF_STATE","bad handoff state",args.report,allowed_handoff_status=sorted(allowed_handoff_status))
    validate_ref_group(h.get("input_refs"), REQUIRED_INPUT_REFS, base_dir, args.report, "input_refs", allow_extra=True)
    validate_ref_group(h.get("output_refs"), REQUIRED_OUTPUT_REFS, base_dir, args.report, "output_refs")
    validate_single_ref(h.get("validation_report_ref"), base_dir, args.report, "validation_report_ref")
    validate_single_ref(h.get("stage_result_ref"), base_dir, args.report, "stage_result_ref")
    expected_version=h.get("artifact_version")
    validate_current_artifact_versions(base_dir, expected_version, args.report)
    schema_report_path=resolve(base_dir, ref_path(h["output_refs"]["schema_validation_report"]))
    validate_authoritative_report(load_json(schema_report_path), args.report, expected_version, "schema validation report")
    final_report_path=resolve(base_dir, ref_path(h["validation_report_ref"]))
    validate_authoritative_report(load_json(final_report_path), args.report, expected_version, "final validation report")
    stage_result_path=resolve(base_dir, ref_path(h["stage_result_ref"]))
    validate_authoritative_report(load_json(stage_result_path), args.report, expected_version, "stage result")
    if not isinstance(h.get("blocking_issues"), list): emit("fail","ERR_HANDOFF_CONTRACT","blocking_issues must be list",args.report)
    emit("pass","","handoff valid",args.report)
if __name__=="__main__": main()
