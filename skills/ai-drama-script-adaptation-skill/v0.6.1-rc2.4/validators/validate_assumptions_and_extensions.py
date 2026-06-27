#!/usr/bin/env python3
from common import *

VALID_CONFLICT_STATUSES={"not_detected","detected_unresolved","provisionally_resolved","resolved_by_user"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--script", required=True); ap.add_argument("--production-assumptions", required=True); ap.add_argument("--source-conflicts", required=True); ap.add_argument("--adaptation-extension-registry", required=True); ap.add_argument("--report", required=True); args=ap.parse_args()
    script=Path(args.script).read_text(encoding="utf-8")
    ass=load_json(args.production_assumptions); conflicts=load_json(args.source_conflicts); exts=load_json(args.adaptation_extension_registry)
    for item in ass.get("items", []):
        if item.get("classification") not in VALID_ASSUMPTION_CLASSES: emit("fail","ERR_ASSUMPTION_CLASSIFICATION","invalid or missing assumption classification",args.report,assumption_id=item.get("assumption_id"))
        for field in ["assumption_id","scene_id","exact_content","source_support","changes_story_fact","changes_character_motivation","requires_user_approval","status"]:
            if field not in item: emit("fail","ERR_ASSUMPTION_FIELD","missing assumption field",args.report,field=field)
    conflict_status=conflicts.get("conflict_detection_status")
    conflict_items=conflicts.get("items", [])
    if conflict_status not in VALID_CONFLICT_STATUSES:
        emit("fail","ERR_SOURCE_CONFLICT_STATUS","invalid conflict_detection_status",args.report,conflict_status=conflict_status)
    if conflict_status == "not_detected":
        if conflict_items:
            emit("fail","ERR_SOURCE_CONFLICT_STATUS","not_detected conflict registry must have empty items",args.report)
    else:
        if not conflict_items:
            emit("fail","ERR_SOURCE_CONFLICT_STATUS","detected or resolved conflict registry must have nonempty items",args.report,conflict_status=conflict_status)
    if conflict_status == "detected_unresolved":
        emit("fail","ERR_SOURCE_CONFLICT_BLOCKING","unresolved source conflicts block handoff",args.report,source_conflict_count=len(conflict_items))
    if conflict_status == "provisionally_resolved":
        for item in conflict_items:
            if not (item.get("resolution_basis") or item.get("provisional_resolution_basis")):
                emit("fail","ERR_SOURCE_CONFLICT_STATUS","provisionally resolved conflict requires basis",args.report,conflict_id=item.get("conflict_id"))
            if "requires_user_decision" not in item and "user_decision_required" not in item:
                emit("fail","ERR_SOURCE_CONFLICT_STATUS","provisionally resolved conflict requires user-decision flag",args.report,conflict_id=item.get("conflict_id"))
    for ext in exts.get("items", []):
        if ext.get("authorized") is False and ext.get("text") and ext.get("text") in script:
            emit("fail","ERR_UNAUTHORIZED_EXTENSION_PRESENT","unauthorized adaptation extension present",args.report,extension_id=ext.get("extension_id"))
    emit("pass","","assumptions/extensions/conflicts valid",args.report,assumption_count=len(ass.get("items", [])),source_conflict_count=len(conflicts.get("items", [])))
if __name__=="__main__": main()
