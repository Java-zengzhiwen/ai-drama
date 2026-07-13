#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_drama_web.operations.backup_restore import M6RestoreService


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    report = M6RestoreService().restore(args.manifest, args.destination)
    print(
        json.dumps(
            {
                "status": report.status,
                "destination": report.destination,
                "file_count": report.file_count,
                "inventory_hash": report.inventory_hash,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
