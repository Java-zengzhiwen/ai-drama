#!/usr/bin/env python3
from common import *

REQUIRED_SECTIONS={
    "full_script":["完整剧本","Full Script"],
    "current_revision":["当前 Revision","Current Revision","当前修订"],
    "scene_overview":["场次概览","Scene Overview"],
    "strict_critical_beat_coverage":["Strict Critical Beat Coverage","核心剧情覆盖"],
    "partial_beats":["Partial Beats","部分覆盖"],
    "production_assumptions":["Production Assumptions","production assumptions","生产假设"],
    "adaptation_extensions":["Adaptation Extensions","改编扩展"],
    "source_conflicts":["Source Conflicts","来源冲突"],
    "current_issues":["当前问题","Current Issues"],
    "recommended_decision":["推荐决策","Recommended Decision"],
    "next_after_approval":["批准后下一步","Next After Approval"],
    "revision_impact_scope":["修改影响范围","Revision Impact Scope"],
    "approval_instruction":["批准指令","accept"],
    "revision_instruction":["修改指令","request_revision"],
    "rejection_instruction":["拒绝指令","reject"],
}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--presentation", required=True); ap.add_argument("--script", required=True); ap.add_argument("--report", required=True); args=ap.parse_args()
    pres=Path(args.presentation).read_text(encoding="utf-8"); script=Path(args.script).read_text(encoding="utf-8").strip()
    if script not in pres: emit("fail","ERR_PRESENTATION_FULL_SCRIPT","full script missing from presentation",args.report)
    for token in ["accept", "request_revision", "reject"]:
        if token not in pres: emit("fail","ERR_PRESENTATION_NEXT_ACTION","next action missing",args.report,token=token)
    missing=[]
    for section,tokens in REQUIRED_SECTIONS.items():
        if not any(token in pres for token in tokens):
            missing.append(section)
    if missing:
        emit("fail","ERR_PRESENTATION_REQUIRED_SECTION","creator presentation missing required sections",args.report,missing_sections=missing)
    lowered = pres.lower()
    if "approved_for_downstream=true" in lowered or "approved_for_downstream: true" in lowered or "approved: true" in lowered:
        emit("fail","ERR_PRESENTATION_AUTO_APPROVAL","creator presentation must not auto-approve downstream work",args.report)
    if "approved_for_downstream=false" not in lowered and "approved_for_downstream: false" not in lowered:
        emit("fail","ERR_PRESENTATION_APPROVAL_STATE","creator presentation must state approved_for_downstream=false",args.report)
    if "SCRIPT_APPROVAL" not in pres:
        emit("fail","ERR_PRESENTATION_GATE_STATE","creator presentation must stop at SCRIPT_APPROVAL",args.report)
    if "formal_integration_status=hold" not in lowered and "formal_integration_status: hold" not in lowered:
        emit("fail","ERR_PRESENTATION_FORMAL_INTEGRATION","creator presentation must keep formal integration on hold",args.report)
    emit("pass","","creator presentation valid",args.report,approved_for_downstream=False,current_gate="SCRIPT_APPROVAL",formal_integration_status="hold")
if __name__=="__main__": main()
