#!/usr/bin/env python3
from common import *
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    scenes = re.findall(r"^## 场次：([^\n]+)$", text, flags=re.M)
    refs = re.findall(r"^- source_scene_reference:\s*(.+)$", text, flags=re.M)
    missing = sorted(set(scenes) - set(refs))
    extra = sorted(set(refs) - set(scenes))
    if missing or extra or not scenes or not refs:
        emit("fail", "ERR_SOURCE_COVERAGE", "storyboard source coverage invalid", args.report, source_scene_references=refs, missing_scene_references=missing, extra_scene_references=extra)
    emit("pass", "", "source coverage valid", args.report, source_scene_references=refs, missing_scene_references=[], extra_scene_references=[])


if __name__ == "__main__":
    main()
