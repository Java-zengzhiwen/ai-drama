from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import stat
import time
import uuid

from ai_drama_runtime.services import NotFound
from ai_drama_runtime.store import now_iso

from .models import CredentialVersionRecord, RevisionConflict


@dataclass(frozen=True)
class CredentialRecoveryReport:
    ready: int = 0
    deleted: int = 0
    corrupt: int = 0
    orphans_removed: int = 0


class SupplierCredentialStore:
    def __init__(self, product_store, data_root, *, checkpoint=None):
        self.product_store = product_store
        self.conn = product_store.conn
        self.secrets_root = Path(data_root) / "secrets" / "suppliers"
        self._checkpoint = checkpoint or (lambda _name: None)

    def temp_path(self, credential_version_id):
        return self.secrets_root / (".%s.tmp" % credential_version_id)

    def replace(self, supplier_id, plaintext, expected_revision):
        supplier = self.product_store.get_supplier(supplier_id)
        if supplier is None:
            raise NotFound("supplier not found: %s" % supplier_id)
        if supplier.credential_revision != expected_revision:
            raise RevisionConflict("supplier credential revision conflict")

        credential_version_id = uuid.uuid4().hex
        operation_id = uuid.uuid4().hex
        temp_path = self.temp_path(credential_version_id)
        final_path = self.secrets_root / credential_version_id
        content = plaintext.encode("utf-8")
        content_hash = hashlib.sha256(content).hexdigest()
        created_at = now_iso()
        self.secrets_root.mkdir(parents=True, exist_ok=True)

        self.conn.execute(
            """
            INSERT INTO credential_migration_journal
            (operation_id, supplier_id, credential_version_id, operation, state,
             temp_path, final_path, content_hash, created_at, updated_at)
            VALUES (?, ?, ?, 'replace', 'journal_created', ?, ?, ?, ?, ?)
            """,
            (
                operation_id,
                supplier_id,
                credential_version_id,
                str(temp_path),
                str(final_path),
                content_hash,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        self._checkpoint("journal_created")

        fd = os.open(temp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        os.chmod(temp_path, 0o600)
        _fsync_directory(self.secrets_root)
        self.conn.execute(
            "UPDATE credential_migration_journal SET state = 'temp_written', updated_at = ? WHERE operation_id = ?",
            (now_iso(), operation_id),
        )
        self.conn.commit()
        self._checkpoint("temp_written")

        revision = expected_revision + 1
        updated_at = now_iso()
        with self.conn:
            current = self.product_store.get_supplier(supplier_id)
            if current.credential_revision != expected_revision:
                raise RevisionConflict("supplier credential revision conflict")
            self.conn.execute(
                """
                INSERT INTO credential_versions
                (credential_version_id, supplier_id, revision, state, secret_path,
                 content_hash, created_at, updated_at)
                VALUES (?, ?, ?, 'pending_finalize', ?, ?, ?, ?)
                """,
                (
                    credential_version_id,
                    supplier_id,
                    revision,
                    str(final_path),
                    content_hash,
                    created_at,
                    updated_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE suppliers
                SET current_credential_version_id = ?, credential_revision = ?, updated_at = ?
                WHERE supplier_id = ?
                """,
                (credential_version_id, revision, updated_at, supplier_id),
            )
            self.conn.execute(
                "UPDATE credential_migration_journal SET state = 'pending_finalize', updated_at = ? WHERE operation_id = ?",
                (updated_at, operation_id),
            )
        self._checkpoint("pending_committed")

        os.replace(temp_path, final_path)
        os.chmod(final_path, 0o600)
        _fsync_directory(self.secrets_root)
        self._checkpoint("renamed")

        self._mark_ready(credential_version_id, operation_id)
        self._checkpoint("ready_committed")
        return self.get(credential_version_id)

    def delete(self, supplier_id, expected_revision):
        supplier = self.product_store.get_supplier(supplier_id)
        if supplier is None:
            raise NotFound("supplier not found: %s" % supplier_id)
        if supplier.credential_revision != expected_revision:
            raise RevisionConflict("supplier credential revision conflict")
        credential_version_id = supplier.current_credential_version_id
        if not credential_version_id:
            return False
        record = self.get(credential_version_id)
        operation_id = uuid.uuid4().hex
        updated_at = now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO credential_migration_journal
                (operation_id, supplier_id, credential_version_id, operation, state,
                 temp_path, final_path, content_hash, created_at, updated_at)
                VALUES (?, ?, ?, 'delete', 'pending_delete', '', ?, ?, ?, ?)
                """,
                (
                    operation_id,
                    supplier_id,
                    credential_version_id,
                    record.secret_path,
                    record.content_hash,
                    updated_at,
                    updated_at,
                ),
            )
            self.conn.execute(
                "UPDATE credential_versions SET state = 'pending_delete', updated_at = ? WHERE credential_version_id = ?",
                (updated_at, credential_version_id),
            )
            self.conn.execute(
                """
                UPDATE suppliers
                SET current_credential_version_id = '', credential_revision = ?, updated_at = ?
                WHERE supplier_id = ?
                """,
                (expected_revision + 1, updated_at, supplier_id),
            )
        self._checkpoint("pending_delete_committed")
        Path(record.secret_path).unlink(missing_ok=True)
        _fsync_directory(self.secrets_root)
        self._checkpoint("delete_file_removed")
        with self.conn:
            self.conn.execute(
                "DELETE FROM credential_versions WHERE credential_version_id = ?",
                (credential_version_id,),
            )
            self.conn.execute(
                "DELETE FROM credential_migration_journal WHERE operation_id = ?",
                (operation_id,),
            )
        return True

    def get(self, credential_version_id):
        row = self.conn.execute(
            "SELECT * FROM credential_versions WHERE credential_version_id = ?",
            (credential_version_id,),
        ).fetchone()
        return None if row is None else CredentialVersionRecord(**dict(row))

    def read(self, credential_version_id):
        record = self.get(credential_version_id)
        if record is None:
            raise NotFound("credential not found: %s" % credential_version_id)
        if record.state != "ready":
            code = (
                "CREDENTIAL_STORAGE_CORRUPT"
                if record.state == "credential_storage_corrupt"
                else "CREDENTIAL_NOT_READY"
            )
            raise RuntimeError(code)
        path = Path(record.secret_path)
        if not self._valid_file(path, record.content_hash):
            self._mark_corrupt(credential_version_id)
            raise RuntimeError("CREDENTIAL_STORAGE_CORRUPT")
        data = path.read_bytes()
        return data.decode("utf-8")

    def recover(self, *, orphan_grace_seconds=300):
        self.secrets_root.mkdir(parents=True, exist_ok=True)
        ready = deleted = corrupt = 0
        journals = self.conn.execute(
            "SELECT * FROM credential_migration_journal ORDER BY created_at, operation_id"
        ).fetchall()
        referenced_temps = {row["temp_path"] for row in journals if row["temp_path"]}
        for row in journals:
            if row["operation"] == "delete":
                Path(row["final_path"]).unlink(missing_ok=True)
                Path(row["temp_path"]).unlink(missing_ok=True) if row["temp_path"] else None
                _fsync_directory(self.secrets_root)
                with self.conn:
                    self.conn.execute(
                        "DELETE FROM credential_versions WHERE credential_version_id = ?",
                        (row["credential_version_id"],),
                    )
                    self.conn.execute(
                        "DELETE FROM credential_migration_journal WHERE operation_id = ?",
                        (row["operation_id"],),
                    )
                deleted += 1
                continue

            record = self.get(row["credential_version_id"])
            temp_path = Path(row["temp_path"])
            final_path = Path(row["final_path"])
            if record is None:
                temp_path.unlink(missing_ok=True)
                final_path.unlink(missing_ok=True)
                self.conn.execute(
                    "DELETE FROM credential_migration_journal WHERE operation_id = ?",
                    (row["operation_id"],),
                )
                self.conn.commit()
                continue
            if self._valid_file(final_path, record.content_hash):
                self._mark_ready(record.credential_version_id, row["operation_id"])
                self._delete_journal(row["operation_id"])
                ready += 1
            elif self._valid_file(temp_path, record.content_hash):
                os.replace(temp_path, final_path)
                os.chmod(final_path, 0o600)
                _fsync_directory(self.secrets_root)
                self._mark_ready(record.credential_version_id, row["operation_id"])
                self._delete_journal(row["operation_id"])
                ready += 1
            else:
                self._mark_corrupt(record.credential_version_id)
                self.conn.execute(
                    "UPDATE credential_migration_journal SET state = 'credential_storage_corrupt', updated_at = ? WHERE operation_id = ?",
                    (now_iso(), row["operation_id"]),
                )
                self.conn.commit()
                corrupt += 1

        removed = 0
        cutoff = time.time() - orphan_grace_seconds
        for path in self.secrets_root.glob(".*.tmp"):
            if str(path) not in referenced_temps and path.stat().st_mtime <= cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        if removed:
            _fsync_directory(self.secrets_root)
        return CredentialRecoveryReport(ready, deleted, corrupt, removed)

    def _mark_ready(self, credential_version_id, operation_id):
        updated_at = now_iso()
        with self.conn:
            self.conn.execute(
                "UPDATE credential_versions SET state = 'ready', updated_at = ? WHERE credential_version_id = ?",
                (updated_at, credential_version_id),
            )
            self.conn.execute(
                "UPDATE credential_migration_journal SET state = 'ready', updated_at = ? WHERE operation_id = ?",
                (updated_at, operation_id),
            )

    def _mark_corrupt(self, credential_version_id):
        self.conn.execute(
            "UPDATE credential_versions SET state = 'credential_storage_corrupt', updated_at = ? WHERE credential_version_id = ?",
            (now_iso(), credential_version_id),
        )
        self.conn.commit()

    def _delete_journal(self, operation_id):
        self.conn.execute(
            "DELETE FROM credential_migration_journal WHERE operation_id = ?",
            (operation_id,),
        )
        self.conn.commit()

    @staticmethod
    def _valid_file(path, expected_hash):
        if not path.is_file():
            return False
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash


def _fsync_directory(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
