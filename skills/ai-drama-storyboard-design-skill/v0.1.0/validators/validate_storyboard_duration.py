#!/usr/bin/env python3
from common import *
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    durations = [int(m.group(1)) for m in re.finditer(r"^- duration_seconds:\s*(\d+)\s*$", text, flags=re.M)]
    shot_headers = re.findall(r"^### 镜头\s+\d+", text, flags=re.M)
    if not durations or len(durations) != len(shot_headers) or any(d < 5 or d > 15 for d in durations):
        emit("fail", "ERR_DURATION", "shot duration out of bounds", args.report, durations=durations, shot_count=len(shot_headers))
    emit("pass", "", "duration valid", args.report, durations=durations, shot_count=len(shot_headers))


if __name__ == "__main__":
    main()
