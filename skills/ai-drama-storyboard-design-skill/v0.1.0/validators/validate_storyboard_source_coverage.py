#!/usr/bin/env python3
from common import *


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revision", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()
    text = Path(args.revision).read_text(encoding="utf-8")
    if "scene_id:" not in text or "source_script_revision_id" not in text:
        emit("fail", "ERR_SOURCE_COVERAGE", "storyboard is missing source coverage markers", args.report)
    emit("pass", "", "source coverage valid", args.report)


if __name__ == "__main__":
    main()
