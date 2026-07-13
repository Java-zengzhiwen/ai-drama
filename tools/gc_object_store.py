#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.operations.object_store_maintenance import ObjectGarbageCollector
from ai_drama_web.store import ProductStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--grace-seconds", type=int, default=86400)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--inventory-hash")
    parser.add_argument("--backup-manifest", type=Path)
    args = parser.parse_args()
    runtime = RuntimeStore(args.data_root / "runtime.db", args.data_root / "objects")
    try:
        collector = ObjectGarbageCollector(ProductStore(runtime), args.data_root)
        result = (
            collector.apply(
                args.inventory_hash or "",
                backup_manifest=args.backup_manifest,
                grace_seconds=args.grace_seconds,
            )
            if args.apply
            else collector.run(grace_seconds=args.grace_seconds)
        )
        print(json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True))
    finally:
        runtime.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
