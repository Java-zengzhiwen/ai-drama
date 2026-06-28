#!/usr/bin/env python3
from common import *


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    required = ["continuity_in:", "continuity_out:", "character_positions:", "character_actions:", "emotion_performance:"]
    missing = [item for item in required if item not in text]
    if missing:
        emit("fail", "ERR_CONTINUITY", "storyboard continuity invalid", args.report, missing=missing)
    emit("pass", "", "continuity valid", args.report)


if __name__ == "__main__":
    main()
