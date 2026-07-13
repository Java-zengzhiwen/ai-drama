from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3

from ai_drama_runtime.store import now_iso

from .object_store_maintenance import ObjectInventory


class BackupIntegrityError(RuntimeError):
    pass


@dataclass(frozen=True)
class BackupFile:
    path: str
    size: int
    sha256: str
    mode: int


@dataclass(frozen=True)
class BackupManifest:
    path: Path
    status: str
    source_data_root: str
    backup_root: str
    inventory_hash: str
    created_at: str
    files: tuple[BackupFile, ...]


@dataclass(frozen=True)
class RestoreReport:
    status: str
    destination: str
    file_count: int
    inventory_hash: str


class M6BackupService:
    def __init__(self, product_store, data_root):
        self.store = product_store
        self.data_root = Path(data_root).resolve()

    def create(self, destination):
        destination = Path(destination).resolve()
        _require_disjoint(self.data_root, destination, "BACKUP_PATH_OVERLAP")
        _require_empty(destination, "BACKUP_DESTINATION_NOT_EMPTY")
        _reject_symlinks(self.data_root / "objects")
        _reject_symlinks(self.data_root / "secrets")
        _validate_ready_credentials(self.store, self.data_root)
        payload = destination / "payload"
        payload.mkdir(parents=True)
        self.store.conn.execute("PRAGMA wal_checkpoint(FULL)")
        target = sqlite3.connect(payload / "runtime.db")
        try:
            self.store.conn.backup(target)
        finally:
            target.close()
        _fsync_file(payload / "runtime.db")
        for name in ("objects", "secrets"):
            source = self.data_root / name
            if source.is_dir():
                shutil.copytree(source, payload / name, copy_function=shutil.copy2)
        _fsync_tree(payload)
        inventory_hash = _validate_payload_consistency(payload, self.data_root)
        _fsync_tree(payload)
        files = tuple(_file_record(path, destination) for path in _payload_files(payload))
        manifest_path = destination / "manifest.json"
        manifest_payload = {
            "schema_version": "m6-backup-v1",
            "status": "verified",
            "source_data_root": str(self.data_root),
            "backup_root": str(destination),
            "inventory_hash": inventory_hash,
            "created_at": now_iso(),
            "files": [asdict(item) for item in files],
        }
        manifest_path.write_text(
            json.dumps(manifest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            encoding="utf-8",
        )
        _fsync_file(manifest_path)
        _fsync_directory(destination)
        return BackupManifest(
            manifest_path,
            "verified",
            str(self.data_root),
            str(destination),
            inventory_hash,
            manifest_payload["created_at"],
            files,
        )


class M6RestoreService:
    def restore(self, manifest_path, destination):
        manifest_path = Path(manifest_path).resolve()
        destination = Path(destination).resolve()
        _require_disjoint(manifest_path.parent, destination, "RESTORE_PATH_OVERLAP")
        _require_empty(destination, "RESTORE_DESTINATION_NOT_EMPTY")
        manifest = verify_backup_manifest(manifest_path)
        backup_root = manifest_path.parent
        destination.mkdir(parents=True)
        for source in sorted((backup_root / "payload").iterdir()):
            target = destination / source.name
            if source.is_dir():
                shutil.copytree(source, target, copy_function=shutil.copy2)
            else:
                shutil.copy2(source, target)
        self._relocate_credentials(destination, Path(manifest["source_data_root"]))
        return RestoreReport(
            "verified",
            str(destination),
            len(manifest["files"]),
            manifest["inventory_hash"],
        )

    @staticmethod
    def _relocate_credentials(destination, source_root):
        database = sqlite3.connect(destination / "runtime.db")
        database.row_factory = sqlite3.Row
        try:
            rows = database.execute(
                "SELECT credential_version_id, secret_path FROM credential_versions"
            ).fetchall()
            for row in rows:
                relative = _relocated_secret_path(Path(row["secret_path"]), source_root)
                target = destination / relative
                if target.is_file():
                    os.chmod(target, 0o600)
                database.execute(
                    "UPDATE credential_versions SET secret_path=? WHERE credential_version_id=?",
                    (str(target), row["credential_version_id"]),
                )
            journals = database.execute(
                "SELECT operation_id, temp_path, final_path FROM credential_migration_journal"
            ).fetchall()
            for row in journals:
                values = []
                for name in ("temp_path", "final_path"):
                    value = row[name]
                    values.append(
                        ""
                        if not value
                        else str(destination / _relocated_secret_path(Path(value), source_root))
                    )
                database.execute(
                    "UPDATE credential_migration_journal SET temp_path=?, final_path=? WHERE operation_id=?",
                    (*values, row["operation_id"]),
                )
            database.commit()
        finally:
            database.close()


def verify_backup_manifest(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = _load_manifest(manifest_path)
    backup_root = manifest_path.parent
    entries = manifest["files"]
    try:
        expected = {str(item["path"]) for item in entries}
    except (KeyError, TypeError) as exc:
        raise BackupIntegrityError("BACKUP_MANIFEST_INVALID") from exc
    if not entries or len(expected) != len(entries):
        raise BackupIntegrityError("BACKUP_MANIFEST_INVALID")
    actual = {
        str(path.relative_to(backup_root))
        for path in _payload_files(backup_root / "payload")
    }
    if actual != expected:
        raise BackupIntegrityError("BACKUP_FILE_SET_MISMATCH")
    for item in entries:
        try:
            path = _safe_member(backup_root, str(item["path"]))
            size = int(item["size"])
            expected_hash = str(item["sha256"])
            expected_mode = int(item["mode"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BackupIntegrityError("BACKUP_MANIFEST_INVALID") from exc
        if path.stat().st_size != size or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
            raise BackupIntegrityError("BACKUP_HASH_MISMATCH")
        if path.stat().st_mode & 0o777 != expected_mode:
            raise BackupIntegrityError("BACKUP_MODE_MISMATCH")
    inventory_hash = _validate_payload_consistency(
        backup_root / "payload", Path(str(manifest.get("source_data_root", "")))
    )
    if inventory_hash != manifest.get("inventory_hash"):
        raise BackupIntegrityError("BACKUP_INVENTORY_MISMATCH")
    return manifest


def semantic_store_summary(product_store):
    conn = product_store.conn
    table_names = (
        "projects",
        "chapters",
        "chapter_source_revisions",
        "assets",
        "generation_jobs",
        "generation_results",
        "suppliers",
        "supplier_versions",
        "supplier_config_revisions",
        "credential_versions",
        "supplier_models",
        "supplier_model_revisions",
        "project_model_bindings",
        "project_model_operation_overrides",
        "execution_snapshots",
        "schema_migrations",
    )
    counts = {
        table: conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()["n"]
        for table in table_names
    }
    identities = {
        "projects": _column(conn, "projects", "project_id"),
        "suppliers": _column(conn, "suppliers", "supplier_id"),
        "models": _column(conn, "supplier_models", "supplier_model_id"),
        "jobs": _column(conn, "generation_jobs", "job_id"),
        "results": _column(conn, "generation_results", "result_id"),
        "snapshots": _column(conn, "execution_snapshots", "snapshot_hash"),
        "objects": sorted(path.name for path in product_store.runtime.objects_root.glob("*/*") if path.is_file()),
    }
    return {"counts": counts, "identities": identities}


def _column(conn, table, column):
    return [
        row[column]
        for row in conn.execute(
            f'SELECT "{column}" FROM "{table}" ORDER BY "{column}"'
        ).fetchall()
    ]


def _payload_files(payload):
    return sorted(path for path in payload.rglob("*") if path.is_file())


def _file_record(path, backup_root):
    data = path.read_bytes()
    return BackupFile(
        str(path.relative_to(backup_root)),
        len(data),
        hashlib.sha256(data).hexdigest(),
        path.stat().st_mode & 0o777,
    )


def _load_manifest(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackupIntegrityError("BACKUP_MANIFEST_INVALID") from exc
    if (
        not isinstance(value, dict)
        or value.get("schema_version") != "m6-backup-v1"
        or value.get("status") != "verified"
        or not isinstance(value.get("files"), list)
    ):
        raise BackupIntegrityError("BACKUP_MANIFEST_INVALID")
    return value


def _safe_member(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not str(relative).startswith("payload/"):
        raise BackupIntegrityError("BACKUP_PATH_INVALID")
    return path


def _relocated_secret_path(path, source_root):
    try:
        relative = path.resolve().relative_to(source_root.resolve())
    except ValueError as exc:
        raise BackupIntegrityError("CREDENTIAL_PATH_OUTSIDE_DATA_ROOT") from exc
    if not relative.parts or relative.parts[0] != "secrets":
        raise BackupIntegrityError("CREDENTIAL_PATH_OUTSIDE_DATA_ROOT")
    return relative


def _require_empty(path, code):
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise BackupIntegrityError(code)


def _require_disjoint(first, second, code):
    first = Path(first).resolve()
    second = Path(second).resolve()
    if first == second or first.is_relative_to(second) or second.is_relative_to(first):
        raise BackupIntegrityError(code)


def _reject_symlinks(root):
    root = Path(root)
    if root.is_symlink():
        raise BackupIntegrityError("BACKUP_SYMLINK_FORBIDDEN")
    if root.is_dir() and any(path.is_symlink() for path in root.rglob("*")):
        raise BackupIntegrityError("BACKUP_SYMLINK_FORBIDDEN")


def _validate_ready_credentials(store, data_root, source_paths_root=None):
    secrets_root = (Path(data_root) / "secrets").resolve()
    source_paths_root = Path(source_paths_root or data_root).resolve()
    rows = store.conn.execute(
        "SELECT state, secret_path, content_hash FROM credential_versions ORDER BY credential_version_id"
    ).fetchall()
    for row in rows:
        if row["state"] != "ready":
            raise BackupIntegrityError("CREDENTIAL_BACKUP_NOT_READY")
        recorded = Path(row["secret_path"])
        try:
            relative = recorded.resolve().relative_to(source_paths_root)
        except ValueError as exc:
            raise BackupIntegrityError("CREDENTIAL_BACKUP_UNSAFE") from exc
        path = Path(data_root) / relative
        resolved = path.resolve()
        if (
            path.is_symlink()
            or not path.is_file()
            or not resolved.is_relative_to(secrets_root)
            or path.stat().st_mode & 0o777 != 0o600
        ):
            raise BackupIntegrityError("CREDENTIAL_BACKUP_UNSAFE")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["content_hash"]:
            raise BackupIntegrityError("CREDENTIAL_BACKUP_CORRUPT")


def _validate_payload_consistency(payload, source_data_root):
    from ai_drama_runtime.store import RuntimeStore
    from ai_drama_web.store import ProductStore

    payload = Path(payload).resolve()
    runtime = RuntimeStore(payload / "runtime.db", payload / "objects")
    try:
        store = ProductStore(runtime)
        inventory = ObjectInventory(store, payload).build(grace_seconds=0)
        if inventory.missing_references:
            raise BackupIntegrityError("BACKUP_OBJECT_REFERENCE_MISSING")
        if any(item.corrupt and item.referenced for item in inventory.entries):
            raise BackupIntegrityError("BACKUP_OBJECT_CORRUPT")
        _validate_ready_credentials(store, payload, source_data_root)
        return inventory.inventory_hash
    finally:
        runtime.close()


def _fsync_file(path):
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_tree(root):
    root = Path(root)
    for path in _payload_files(root):
        _fsync_file(path)
    for directory in sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        _fsync_directory(directory)
    _fsync_directory(root)
