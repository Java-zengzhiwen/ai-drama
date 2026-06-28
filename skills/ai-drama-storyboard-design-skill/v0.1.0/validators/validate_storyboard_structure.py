#!/usr/bin/env python3
from common import *


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    issues = []
    if "## 场次" not in text and "## Scene" not in text:
        issues.append("missing scene sections")
    if "shot_id" not in text:
        issues.append("missing shot markers")
    if "duration_seconds" not in text:
        issues.append("missing duration field")
    if issues:
        emit("fail", "ERR_STRUCTURE", "storyboard structure invalid", args.report, issues=issues)
    emit("pass", "", "storyboard structure valid", args.report)


if __name__ == "__main__":
    main()
