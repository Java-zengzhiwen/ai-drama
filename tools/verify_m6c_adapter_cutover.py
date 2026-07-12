#!/usr/bin/env python3
"""Offline M6C contract verifier; never opens a Provider connection."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ai_drama_web.suppliers.adapters import FakeSupplierAdapter, SupplierAdapterGateway
from ai_drama_web.config import Settings
from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore


def main():
    fake = FakeSupplierAdapter()
    gateway = SupplierAdapterGateway(fake, supplier_slug="fake")
    text = gateway.text_request({"prompt": "hello"})
    submitted = gateway.video_submit({"prompt": "shot"})
    polled = gateway.video_poll(submitted.value["video_id"])
    fetched = gateway.video_fetch(submitted.value["video_id"])
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = ProductStore(RuntimeStore(root / "runtime.db", root / "objects"))
        columns = {row["name"] for row in store.conn.execute("PRAGMA table_info(generation_jobs)")}
        attempt_table = store.conn.execute("SELECT name FROM sqlite_master WHERE name='generation_submission_attempts'").fetchone()
    checks = {
        "M6C-001": text.value == "fake-text:hello" and text.usage["output_tokens"] == 1,
        "M6C-002": attempt_table is not None and "snapshot_hash" in columns,
        "M6C-003": fake.submit_count == 1,
        "M6C-004": fake.poll_count == 1 and fake.fetch_count == 1,
        "M6C-005": polled.value["video_id"] == "fake-video-1" and polled.value["status"] == "completed",
        "M6C-006": "snapshot_hash" in columns and "snapshot_object_id" in columns,
        "M6C-007": "source_job_id" in columns,
        "M6C-008": "rerun_resolution_mode" in columns,
        "M6C-009": store.conn.execute("SELECT name FROM sqlite_master WHERE name='supplier_idempotency_records'").fetchone() is not None,
        "M6C-010": Settings().m6_supplier_execution_enabled is False,
        "M6C-011": "video_id" in submitted.value and fetched.value["media_type"] == "video/mp4",
        "M6C-012": isinstance(fake, FakeSupplierAdapter) and fake.submit_count == 1,
        "M6C-013": store.conn.execute("SELECT COUNT(*) FROM generation_jobs").fetchone()[0] == 0,
    }
    result = {"checks": checks, "passed": all(checks.values()), "real_provider_requests": 0}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
