#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, sys, tempfile

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore, STREAMING_SCRIPT_GENERATION_MIGRATION_ID

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

with tempfile.TemporaryDirectory(prefix="ai-drama-migration-check-") as temporary:
    temporary_root = Path(temporary)
    runtime = RuntimeStore(temporary_root / "runtime.db", temporary_root / "objects")
    store = ProductStore(runtime)
    tables = {
        row["name"]
        for row in store.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    migration = store.conn.execute(
        "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
        (STREAMING_SCRIPT_GENERATION_MIGRATION_ID,),
    ).fetchone()
    runtime.close()

streaming_migration_valid = bool(migration) and {
    "script_generation_runs",
    "script_generation_events",
}.issubset(tables)
if not streaming_migration_valid:
    print(
        json.dumps(
            {
                "status": "invalid",
                "streaming_script_generation_migration": "missing",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    sys.exit(1)

print(
    json.dumps(
        {
            "status": "valid",
            "checked_files": len(manifest["files"]),
            "streaming_script_generation_migration": "valid",
        },
        ensure_ascii=False,
        indent=2,
    )
)
