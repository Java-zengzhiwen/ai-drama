#!/usr/bin/env python3
from common import *
import re


def _shots(text):
    scenes = []
    current = None
    shot = None
    for line in text.splitlines():
        if line.startswith("## 场次：") or line.startswith("## Scene"):
            if current:
                scenes.append(current)
            current = {"scene": line, "shots": []}
            shot = None
            continue
        if line.startswith("### 镜头 "):
            shot = {"header": line, "fields": {}}
            if current is not None:
                current["shots"].append(shot)
            continue
        m = re.match(r"^-\s*([a-z_]+):\s*(.*)$", line)
        if shot and m:
            shot["fields"][m.group(1)] = m.group(2)
    if current:
        scenes.append(current)
    return scenes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    scenes = _shots(text)
    issues = []
    seen_shot_ids = set()
    for scene in scenes:
        if not scene["shots"]:
            issues.append("scene without shots: %s" % scene["scene"])
        seen_orders = set()
        for shot in scene["shots"]:
            fields = shot["fields"]
            required = [
                "scene_id",
                "shot_id",
                "shot_order",
                "source_scene_reference",
                "duration_seconds",
                "shot_size",
                "camera_angle",
                "camera_movement",
                "visual_composition",
                "character_positions",
                "character_actions",
                "emotion_performance",
                "dialogue",
                "sound_notes",
                "continuity_in",
                "continuity_out",
            ]
            missing = [name for name in required if not fields.get(name)]
            if missing:
                issues.append({"shot": shot["header"], "missing": missing})
            shot_id = fields.get("shot_id")
            if shot_id in seen_shot_ids:
                issues.append({"shot": shot["header"], "duplicate_shot_id": shot_id})
            elif shot_id:
                seen_shot_ids.add(shot_id)
            order = fields.get("shot_order")
            if order in seen_orders:
                issues.append({"shot": shot["header"], "duplicate_shot_order": order})
            elif order:
                seen_orders.add(order)
            if fields.get("scene_id") != scene["scene"].replace("## 场次：", "").strip() and fields.get("source_scene_reference") and fields["source_scene_reference"] != fields["scene_id"]:
                issues.append({"shot": shot["header"], "scene_reference_mismatch": True})
    if issues:
        emit("fail", "ERR_STRUCTURE", "storyboard structure invalid", args.report, issues=issues)
    emit("pass", "", "storyboard structure valid", args.report, scenes=len(scenes))


if __name__ == "__main__":
    main()
