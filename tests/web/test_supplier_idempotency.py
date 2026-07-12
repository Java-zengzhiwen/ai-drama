import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.idempotency import (
    SupplierIdempotencyConflict,
    SupplierIdempotencyStore,
    canonical_request_hash,
)


def test_request_hash_combines_normalized_request_and_snapshot_hash():
    left = canonical_request_hash({"prompt": "x", "params": {"b": 2, "a": 1}}, "snapshot-a")
    right = canonical_request_hash({"params": {"a": 1, "b": 2}, "prompt": "x"}, "snapshot-a")
    assert left == right
    assert left != canonical_request_hash({"prompt": "x", "params": {"a": 1, "b": 2}}, "snapshot-b")


def test_scoped_idempotency_replays_and_conflicts_by_snapshot(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    suppliers = store.list_suppliers()
    idem = SupplierIdempotencyStore(store)
    request_hash = canonical_request_hash({"prompt": "x"}, "snapshot-a")

    assert idem.claim(suppliers[0].supplier_id, "text", "same-key", request_hash, "job-1") == ("job-1", True)
    assert idem.claim(suppliers[0].supplier_id, "text", "same-key", request_hash, "job-2") == ("job-1", False)
    with pytest.raises(SupplierIdempotencyConflict, match="IDEMPOTENCY_CONFLICT"):
        idem.claim(
            suppliers[0].supplier_id,
            "text",
            "same-key",
            canonical_request_hash({"prompt": "x"}, "snapshot-b"),
            "job-3",
        )
    assert idem.claim(suppliers[1].supplier_id, "text", "same-key", request_hash, "job-4") == ("job-4", True)


def test_legacy_generation_idempotency_schema_is_unchanged(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    ProductStore(runtime)
    sql = runtime.conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'generation_jobs'"
    ).fetchone()["sql"]
    assert "UNIQUE(provider, idempotency_key)" in sql
    assert "supplier_id" not in sql
