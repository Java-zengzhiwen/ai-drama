#!/usr/bin/env python3
from common import *
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    shots = re.split(r"^### 镜头\s+\d+\s*$", text, flags=re.M)
    issues = []
    for block in shots[1:]:
        required = [
            "continuity_in:",
            "continuity_out:",
            "character_positions:",
            "character_actions:",
            "emotion_performance:",
        ]
        missing = [item for item in required if item not in block]
        if missing:
            issues.append({"missing": missing})
    if issues:
        emit("fail", "ERR_CONTINUITY", "storyboard continuity invalid", args.report, issues=issues)
    emit("pass", "", "continuity valid", args.report, shot_count=len(shots) - 1)


if __name__ == "__main__":
    main()
