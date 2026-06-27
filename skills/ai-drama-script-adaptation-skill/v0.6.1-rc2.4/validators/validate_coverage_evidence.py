#!/usr/bin/env python3
from common import *

ALLOWED_BODY_HEADINGS = [
    "正文", "剧本正文", "动作", "台词", "表演反应", "停顿、呼吸、视线、微表情",
    "声音或有效沉默", "环境声或有效沉默", "场尾钩子", "场次结束动作", "收束",
    "Actions", "Dialogue", "Performance Details", "Sound or Effective Silence", "End State", "End Hook", "Script Body"
]
FORBIDDEN_EVIDENCE_TOKENS = [
    "场景目标", "本场剧情目标", "情绪起点", "人物情绪起点", "情绪推进", "人物情绪变化",
    "情绪落点", "人物情绪终点", "氛围", "场景氛围", "覆盖 Beats", "Covered Beats",
    "coverage", "Coverage", "QC", "Creator Presentation", "推荐决策"
]
DIMENSIONS = ["event", "information", "causal", "emotional", "relationship"]

def dimension_applies(value):
    return bool(str(value or "").strip()) and not str(value).strip().lower().startswith("not_applicable")

def extract_body_zone(scene_text):
    lines = scene_text.splitlines()
    allowed = False
    body = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("###"):
            heading = stripped.lstrip("#").strip()
            allowed = any(token in heading for token in ALLOWED_BODY_HEADINGS)
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            allowed = False
            continue
        if allowed:
            body.append(line)
    return "\n".join(body).strip()

def nonempty_story_lines(text):
    lines=[]
    for line in text.splitlines():
        stripped=line.strip()
        if not stripped: continue
        if stripped.startswith("-"): continue
        if stripped.startswith("###"): continue
        lines.append(stripped)
    return lines

def body_density_ok(body):
    lines = nonempty_story_lines(body)
    char_count = len("".join(lines))
    # A complete critical scene may be short, but it cannot be a two-line card.
    return len(lines) >= 2 and char_count >= 70

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--script", required=True)
    ap.add_argument("--script-json", required=True)
    ap.add_argument("--beat-registry", required=True)
    ap.add_argument("--coverage-report", required=True)
    ap.add_argument("--report", required=True)
    args=ap.parse_args()
    Path(args.script).read_text(encoding="utf-8")
    script_json=load_json(args.script_json)
    scene_map={s.get("scene_id"):s.get("full_scene_markdown","") for s in script_json.get("scenes", []) if s.get("scene_id")}
    body_map={sid: extract_body_zone(text) for sid,text in scene_map.items()}
    coverage=load_json(args.coverage_report)
    expected=beat_ids_from_registry(args.beat_registry)
    critical=critical_ids_from_registry(args.beat_registry)
    registry_beats={b.get("beat_id"): b for b in beat_list(args.beat_registry)}
    items=coverage.get("items", [])
    if not items: emit("fail","ERR_COVERAGE_EMPTY","coverage items empty",args.report)
    if coverage.get("expected_beat_count") != len(expected) or coverage.get("evaluated_beat_count") != len(items):
        emit("fail","ERR_BEAT_COUNT_MISMATCH","coverage counts do not match registry/items",args.report)
    seen=[]; metadata_used=0; scene_card_scenes=[]
    for item in items:
        bid=item.get("beat_id")
        if bid in seen: emit("fail","ERR_DUPLICATE_BEAT","duplicate beat id",args.report,beat_id=bid)
        seen.append(bid)
    if set(seen) != set(expected): emit("fail","ERR_BEAT_SET_MISMATCH","coverage beat ids do not match registry",args.report)
    scene_ids=set(scene_map)
    for item in items:
        bid=item.get("beat_id")
        beat_scene_ids=set(item.get("script_scene_ids", []))
        if bid in critical:
            dims=item.get("coverage_dimensions")
            if not isinstance(dims, dict):
                emit("fail","ERR_COVERAGE_DIMENSIONS_MISSING","critical coverage requires coverage_dimensions",args.report,beat_id=bid)
            for dim in DIMENSIONS:
                status=dims.get(dim)
                if status not in {"fully_covered","not_applicable"}:
                    emit("fail","ERR_CRITICAL_DIMENSION_COVERAGE","critical beat dimension is not fully covered",args.report,beat_id=bid,dimension=dim,status=status)
            for field,dim in [("required_event","event"),("required_information","information"),("required_causal_link","causal"),("required_emotional_change","emotional"),("required_relationship_state","relationship")]:
                if dimension_applies(registry_beats.get(bid, {}).get(field, "")) and dims.get(dim) != "fully_covered":
                    emit("fail","ERR_CRITICAL_DIMENSION_COVERAGE","required beat field lacks full dimension coverage",args.report,beat_id=bid,field=field,dimension=dim)
            for sid in beat_scene_ids:
                if sid in body_map and not body_density_ok(body_map[sid]):
                    scene_card_scenes.append(sid)
        for sid in item.get("script_scene_ids", []):
            if sid not in scene_ids: emit("fail","ERR_SCENE_REF_MISSING","coverage references missing scene",args.report,scene_id=sid)
        if not item.get("body_evidence_zone_refs"):
            emit("fail","ERR_BODY_EVIDENCE_REFS_MISSING","coverage item must include body_evidence_zone_refs",args.report,beat_id=bid)
        for ref in item.get("script_evidence_refs", []):
            sid=ref.get("scene_id")
            text=ref.get("text", "")
            if not text:
                emit("fail","ERR_EVIDENCE_TEXT_MISSING","script evidence text not found",args.report,beat_id=bid,text=text)
            if not sid or sid not in scene_ids:
                emit("fail","ERR_EVIDENCE_SCENE_MISMATCH","script evidence scene missing from script json",args.report,beat_id=bid,scene_id=sid)
            if sid not in beat_scene_ids:
                emit("fail","ERR_EVIDENCE_SCENE_MISMATCH","script evidence scene is not listed on beat script_scene_ids",args.report,beat_id=bid,scene_id=sid)
            if text not in scene_map.get(sid, ""):
                emit("fail","ERR_EVIDENCE_SCENE_MISMATCH","script evidence text not found in referenced scene full_scene_markdown",args.report,beat_id=bid,scene_id=sid,text=text)
            if text not in body_map.get(sid, ""):
                metadata_used += 1
                emit("fail","ERR_METADATA_AS_EVIDENCE","script evidence is outside body evidence zone",args.report,beat_id=bid,scene_id=sid,text=text,metadata_used_as_coverage_evidence_count=metadata_used)
            if any(token in text for token in FORBIDDEN_EVIDENCE_TOKENS):
                emit("fail","ERR_METADATA_AS_EVIDENCE","metadata cannot count as story evidence",args.report,beat_id=bid,text=text)
    if scene_card_scenes:
        emit("fail","ERR_SCENE_CARD_BODY","critical scene body is too compressed",args.report,scene_ids=sorted(set(scene_card_scenes)))
    full_critical={i.get("beat_id") for i in items if i.get("beat_id") in critical and i.get("status")=="fully_covered"}
    if full_critical != critical:
        emit("fail","ERR_STRICT_CRITICAL_COVERAGE","critical beats must all be fully covered",args.report,missing=sorted(critical-full_critical))
    emit("pass","","coverage evidence valid",args.report,expected_beat_count=len(expected),critical_count=len(critical),metadata_used_as_coverage_evidence_count=0,synopsis_or_scene_card_status=False)
if __name__=="__main__": main()
