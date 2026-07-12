import hashlib
import json

from ai_drama_runtime.store import now_iso


class SupplierIdempotencyConflict(ValueError):
    pass


def canonical_request_hash(request, execution_snapshot_hash):
    normalized = json.dumps(
        {
            "request": request,
            "execution_snapshot_hash": execution_snapshot_hash,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SupplierIdempotencyStore:
    def __init__(self, store):
        self.store = store

    def claim(self, supplier_id, capability, idempotency_key, request_hash, existing_id):
        self.store.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.store.conn.execute(
                """
                SELECT * FROM supplier_idempotency_records
                WHERE supplier_id = ? AND capability = ? AND idempotency_key = ?
                """,
                (supplier_id, capability, idempotency_key),
            ).fetchone()
            if row:
                if row["request_hash"] != request_hash:
                    raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
                self.store.conn.commit()
                return row["existing_id"], False
            self.store.conn.execute(
                """
                INSERT INTO supplier_idempotency_records
                (supplier_id, capability, idempotency_key, request_hash, existing_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (supplier_id, capability, idempotency_key, request_hash, existing_id, now_iso()),
            )
            self.store.conn.commit()
            return existing_id, True
        except Exception:
            self.store.conn.rollback()
            raise
