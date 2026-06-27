#!/usr/bin/env python3
from common import *

def scene_blocks_from_markdown(markdown, scenes):
    positions=[]
    for scene in scenes:
        sid=scene.get("scene_id","")
        pos=markdown.find(sid)
        if pos < 0:
            return None
        line_start=markdown.rfind("\n",0,pos)
        positions.append((sid, line_start + 1 if line_start >= 0 else 0))
    blocks={}
    for idx,(sid,start) in enumerate(positions):
        end=positions[idx+1][1] if idx+1 < len(positions) else len(markdown)
        blocks[sid]=markdown[start:end].strip()
    return blocks

def require_in_scene(value, scene_text, report_path, scene_id, field):
    if isinstance(value, list):
        values=value
    else:
        values=[value]
    for item in values:
        if not item:
            emit("fail","ERR_EQUIV_REQUIRED_FIELD","scene required field empty",report_path,scene_id=scene_id,field=field)
        if item not in scene_text:
            emit("fail","ERR_EQUIV_JSON_ONLY_CONTENT","json field content missing from markdown scene body",report_path,scene_id=scene_id,field=field,text=item)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--script", required=True); ap.add_argument("--script-json", required=True); ap.add_argument("--coverage-report", required=True); ap.add_argument("--report", required=True); args=ap.parse_args()
    md=Path(args.script).read_text(encoding="utf-8"); data=load_json(args.script_json); coverage=load_json(args.coverage_report)
    scenes=data.get("scenes", [])
    if not scenes: emit("fail","ERR_EQUIV_NO_SCENES","no scenes",args.report)
    blocks=scene_blocks_from_markdown(md, scenes)
    if blocks is None:
        emit("fail","ERR_EQUIV_SCENE_MISSING","scene id missing from markdown",args.report)
    last=-1
    for s in scenes:
        sid=s.get("scene_id", ""); title=s.get("title", "")
        pos=md.find(sid)
        if pos < 0 or title not in md: emit("fail","ERR_EQUIV_SCENE_MISSING","scene id/title missing from markdown",args.report,scene_id=sid)
        if pos < last: emit("fail","ERR_EQUIV_SCENE_ORDER","scene order mismatch",args.report,scene_id=sid)
        last=pos
        full_scene=s.get("full_scene_markdown","").strip()
        if not full_scene or full_scene not in md:
            emit("fail","ERR_EQUIV_JSON_ONLY_CONTENT","full_scene_markdown is not exact continuous content from markdown",args.report,scene_id=sid)
        scene_block=blocks.get(sid,"")
        if full_scene.strip() != scene_block.strip():
            if full_scene.strip() in scene_block.strip():
                emit("fail","ERR_EQUIV_MARKDOWN_ONLY_CONTENT","markdown scene block contains story content absent from JSON full_scene_markdown",args.report,scene_id=sid)
            emit("fail","ERR_EQUIV_JSON_ONLY_CONTENT","full_scene_markdown does not match markdown scene block",args.report,scene_id=sid)
        for ch in s.get("characters", []):
            if ch not in full_scene and ch not in scene_block: emit("fail","ERR_EQUIV_CHARACTER","character missing",args.report,scene_id=sid)
        for field in ["location","time","interior_exterior","atmosphere","scene_goal","emotion_start","emotion_progression","emotion_end","environment","actions","dialogue","performance_details","sound_or_silence","end_state","end_hook"]:
            require_in_scene(s.get(field), full_scene, args.report, sid, field)
    cov_ids={i["beat_id"] for i in coverage.get("items", [])}
    cov_scene_ids={sid for item in coverage.get("items", []) for sid in item.get("script_scene_ids", [])}
    for s in scenes:
        if not set(s.get("covered_beat_ids", [])).issubset(cov_ids): emit("fail","ERR_EQUIV_BEAT_IDS","scene covered beats not in coverage",args.report)
        if s.get("covered_beat_ids") and s.get("scene_id") not in cov_scene_ids:
            emit("fail","ERR_EQUIV_BEAT_IDS","scene covered beats are not linked by coverage report scene ids",args.report,scene_id=s.get("scene_id"))
    emit("pass","","markdown/json equivalence valid",args.report,scene_count=len(scenes),bidirectional_story_fact_check=True)
if __name__=="__main__": main()
