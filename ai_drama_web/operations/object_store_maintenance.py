from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json
import time


class GCGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class ObjectInventoryEntry:
    object_id: str
    size: int
    modified_ns: int
    age_seconds: int
    kind: str
    actual_hash: str
    referenced_by: tuple[str, ...]
    corrupt: bool
    candidate: bool

    @property
    def referenced(self):
        return bool(self.referenced_by)


@dataclass(frozen=True)
class ObjectInventoryReport:
    entries: tuple[ObjectInventoryEntry, ...]
    missing_references: tuple[str, ...]
    inventory_hash: str

    @property
    def candidate_count(self):
        return sum(item.candidate for item in self.entries)

    @property
    def candidate_bytes(self):
        return sum(item.size for item in self.entries if item.candidate)

    def to_dict(self):
        return {
            "inventory_hash": self.inventory_hash,
            "object_count": len(self.entries),
            "object_bytes": sum(item.size for item in self.entries),
            "candidate_count": self.candidate_count,
            "candidate_bytes": self.candidate_bytes,
            "missing_references": list(self.missing_references),
            "entries": [asdict(item) for item in self.entries],
        }


@dataclass(frozen=True)
class GCApplyReport:
    applied: bool
    inventory_hash: str
    deleted_count: int
    deleted_bytes: int
    deleted_object_ids: tuple[str, ...]

    def to_dict(self):
        return asdict(self)


class ObjectInventory:
    def __init__(self, product_store, data_root):
        self.store = product_store
        self.runtime = product_store.runtime
        self.data_root = Path(data_root).resolve()

    def build(self, *, grace_seconds=86400):
        now = time.time()
        references = self._references()
        entries = []
        existing = set()
        for path in sorted(self.runtime.objects_root.glob("*/*")):
            if not path.is_file():
                continue
            object_id = path.name
            existing.add(object_id)
            data = path.read_bytes()
            actual_hash = hashlib.sha256(data).hexdigest()
            stat = path.stat()
            age_seconds = max(0, int(now - stat.st_mtime))
            kind = _kind(data)
            corrupt = actual_hash != object_id
            referenced_by = tuple(sorted(references.get(object_id, ())))
            candidate = (
                not referenced_by
                and not corrupt
                and kind != "unknown"
                and age_seconds >= grace_seconds
            )
            entries.append(
                ObjectInventoryEntry(
                    object_id=object_id,
                    size=len(data),
                    modified_ns=stat.st_mtime_ns,
                    age_seconds=age_seconds,
                    kind=kind,
                    actual_hash=actual_hash,
                    referenced_by=referenced_by,
                    corrupt=corrupt,
                    candidate=candidate,
                )
            )
        missing = tuple(sorted(set(references) - existing))
        payload = [
            {
                "object_id": item.object_id,
                "size": item.size,
                "modified_ns": item.modified_ns,
                "actual_hash": item.actual_hash,
                "referenced_by": item.referenced_by,
                "corrupt": item.corrupt,
                "candidate": item.candidate,
            }
            for item in entries
        ]
        digest = hashlib.sha256(
            json.dumps(
                {"entries": payload, "missing_references": missing},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return ObjectInventoryReport(tuple(entries), missing, digest)

    def _references(self):
        references = {}
        tables = [
            row["name"]
            for row in self.store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        ]
        for table in tables:
            columns = [
                row["name"]
                for row in self.store.conn.execute(
                    'PRAGMA table_info("%s")' % table.replace('"', '""')
                ).fetchall()
                if row["name"] == "object_id" or row["name"].endswith("_object_id")
            ]
            for column in columns:
                query = 'SELECT "%s" AS object_id FROM "%s" WHERE "%s" IS NOT NULL AND "%s" != ?' % (
                    column.replace('"', '""'),
                    table.replace('"', '""'),
                    column.replace('"', '""'),
                    column.replace('"', '""'),
                )
                for row in self.store.conn.execute(query, ("",)).fetchall():
                    object_id = str(row["object_id"])
                    references.setdefault(object_id, set()).add(f"{table}.{column}")
        return references


class ObjectGarbageCollector:
    def __init__(self, product_store, data_root):
        self.store = product_store
        self.runtime = product_store.runtime
        self.data_root = Path(data_root).resolve()

    def plan(self, *, grace_seconds=86400):
        return ObjectInventory(self.store, self.data_root).build(
            grace_seconds=grace_seconds
        )

    def run(self, *, grace_seconds=86400):
        plan = self.plan(grace_seconds=grace_seconds)
        return GCApplyReport(False, plan.inventory_hash, 0, 0, ())

    def apply(self, inventory_hash, *, backup_manifest, grace_seconds=86400):
        if not (self.data_root / ".m6e-temporary-root").is_file():
            raise GCGuardError("TEMPORARY_ROOT_REQUIRED")
        if backup_manifest is None:
            raise GCGuardError("BACKUP_REQUIRED")
        manifest = _read_manifest(backup_manifest)
        if (
            manifest.get("status") != "verified"
            or Path(str(manifest.get("source_data_root", ""))).resolve() != self.data_root
            or manifest.get("inventory_hash") != inventory_hash
        ):
            raise GCGuardError("BACKUP_INVALID")
        plan = self.plan(grace_seconds=grace_seconds)
        if plan.inventory_hash != inventory_hash:
            raise GCGuardError("INVENTORY_CHANGED")
        deleted = []
        deleted_bytes = 0
        for item in plan.entries:
            if not item.candidate:
                continue
            path = self.runtime.object_path(item.object_id)
            if path.is_file():
                deleted_bytes += item.size
                path.unlink()
                deleted.append(item.object_id)
        return GCApplyReport(
            True,
            inventory_hash,
            len(deleted),
            deleted_bytes,
            tuple(deleted),
        )


def _read_manifest(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GCGuardError("BACKUP_INVALID") from exc
    if not isinstance(value, dict):
        raise GCGuardError("BACKUP_INVALID")
    return value


def _kind(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data[4:8] == b"ftyp":
        return "mp4"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "unknown"
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return "text" if text.isprintable() or "\n" in text or "\t" in text else "unknown"
    return "json"
