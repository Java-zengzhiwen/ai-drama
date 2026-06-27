#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys

root = Path(__file__).resolve().parents[2]
manifest = json.loads((root / "migration/migration-manifest.json").read_text(encoding="utf-8"))
missing = []
modified = []
for item in manifest["files"]:
    path = root / item["target_relative_path"]
    if not path.is_file():
        missing.append(item["target_relative_path"])
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != item["sha256"]:
        modified.append({"path": item["target_relative_path"], "expected": item["sha256"], "actual": actual})
if missing or modified:
    print(json.dumps({"status": "invalid", "missing": missing, "modified": modified}, ensure_ascii=False, indent=2))
    sys.exit(1)
print(json.dumps({"status": "valid", "checked_files": len(manifest["files"])}, ensure_ascii=False, indent=2))
