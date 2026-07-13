#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.operations.backup_restore import M6BackupService
from ai_drama_web.store import ProductStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    runtime = RuntimeStore(args.data_root / "runtime.db", args.data_root / "objects")
    try:
        manifest = M6BackupService(ProductStore(runtime), args.data_root).create(
            args.destination
        )
        print(
            json.dumps(
                {
                    "status": manifest.status,
                    "manifest": str(manifest.path),
                    "file_count": len(manifest.files),
                    "inventory_hash": manifest.inventory_hash,
                },
                sort_keys=True,
            )
        )
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
