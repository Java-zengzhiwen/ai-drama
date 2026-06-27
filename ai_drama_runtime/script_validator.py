import argparse
import json
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args(argv)

    text = Path(args.revision).read_text(encoding="utf-8")
    issues = []
    if not text.lstrip().startswith("#"):
        issues.append("script must start with a Markdown heading")
    if "Scene" not in text and "场" not in text:
        issues.append("script must contain at least one scene marker")
    if len(text.strip()) < 80:
        issues.append("script is too short for a persisted drama script revision")

    payload = {
        "final_status": "pass" if not issues else "fail",
        "issues": issues,
        "revision_path": str(Path(args.revision).resolve()),
    }
    Path(args.report).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
