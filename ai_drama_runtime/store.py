from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    artifact_id: str
    project_id: str
    chapter_id: str
    skill_id: str
    skill_version: str
    skill_hash: str
    runtime: str
    provider: str
    model: str
    status: str
    request_object_id: str
    response_object_id: str
    input_hash: str
    request_hash: str
    usage_status: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    usage_raw_object_id: str
    error_code: str
    error_message: str
    started_at: str
    completed_at: str
    duration_ms: int
    created_at: str


@dataclass(frozen=True)
class InputSnapshot:
    run_id: str
    logical_type: str
    source_relative_path: str
    source_path: Path
    sha256: str
    object_id: str


@dataclass(frozen=True)
class RevisionRecord:
    revision_id: str
    artifact_id: str
    artifact_type: str
    project_id: str
    chapter_id: str
    run_id: str
    skill_id: str
    skill_version: str
    skill_package_hash: str
    runtime_provider: str
    runtime_model: str
    number: int
    content_object_id: str
    content_hash: str
    raw_response_object_id: str
    parser_version: str
    supersedes_revision_id: str
    approval_status: str
    created_at: str


@dataclass(frozen=True)
class ValidationRecord:
    validation_id: str
    revision_id: str
    validator_id: str
    validator_name: str
    status: str
    required: bool
    exit_code: int
    error_code: str
    duration_ms: int
    stdout_object_id: str
    stderr_object_id: str
    report_object_id: str
    created_at: str


@dataclass(frozen=True)
class ApprovalRecord:
    sequence: int
    record_id: str
    revision_id: str
    artifact_id: str
    action: str
    reviewer: str
    note: str
    created_at: str


@dataclass(frozen=True)
class ExportRecord:
    export_id: str
    artifact_id: str
    revision_id: str
    run_id: str
    content_hash: str
    destination: str
    provenance_object_id: str
    created_at: str


class RuntimeStore:
    def __init__(self, db_path, objects_root):
        self.db_path = Path(db_path)
        self.objects_root = Path(objects_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.objects_root.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def close(self):
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def _init_schema(self):
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS artifacts (
              artifact_id TEXT PRIMARY KEY,
              artifact_type TEXT NOT NULL,
              project_id TEXT NOT NULL,
              chapter_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL,
              project_id TEXT NOT NULL,
              chapter_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              skill_version TEXT NOT NULL,
              skill_hash TEXT NOT NULL,
              runtime TEXT NOT NULL,
              provider TEXT NOT NULL,
              model TEXT NOT NULL,
              status TEXT NOT NULL,
              request_object_id TEXT NOT NULL,
              response_object_id TEXT NOT NULL,
              input_hash TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              usage_status TEXT NOT NULL,
              prompt_tokens INTEGER NOT NULL,
              completion_tokens INTEGER NOT NULL,
              total_tokens INTEGER NOT NULL,
              usage_raw_object_id TEXT NOT NULL,
              error_code TEXT NOT NULL,
              error_message TEXT NOT NULL,
              started_at TEXT NOT NULL,
              completed_at TEXT NOT NULL,
              duration_ms INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS input_snapshots (
              run_id TEXT NOT NULL,
              logical_type TEXT NOT NULL,
              source_relative_path TEXT NOT NULL,
              source_path TEXT NOT NULL,
              sha256 TEXT NOT NULL,
              object_id TEXT NOT NULL,
              PRIMARY KEY(run_id, logical_type),
              FOREIGN KEY(run_id) REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS revisions (
              revision_id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL,
              artifact_type TEXT NOT NULL,
              project_id TEXT NOT NULL,
              chapter_id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              skill_version TEXT NOT NULL,
              skill_package_hash TEXT NOT NULL,
              runtime_provider TEXT NOT NULL,
              runtime_model TEXT NOT NULL,
              number INTEGER NOT NULL,
              content_object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              raw_response_object_id TEXT NOT NULL,
              parser_version TEXT NOT NULL,
              supersedes_revision_id TEXT NOT NULL,
              approval_status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS validation_results (
              validation_id TEXT PRIMARY KEY,
              revision_id TEXT NOT NULL,
              validator_id TEXT NOT NULL,
              validator_name TEXT NOT NULL,
              status TEXT NOT NULL,
              required INTEGER NOT NULL,
              exit_code INTEGER NOT NULL,
              error_code TEXT NOT NULL,
              duration_ms INTEGER NOT NULL,
              stdout_object_id TEXT NOT NULL,
              stderr_object_id TEXT NOT NULL,
              report_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS approval_records (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              record_id TEXT NOT NULL UNIQUE,
              revision_id TEXT NOT NULL,
              artifact_id TEXT NOT NULL,
              action TEXT NOT NULL,
              reviewer TEXT NOT NULL,
              note TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS export_records (
              export_id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL,
              revision_id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              destination TEXT NOT NULL,
              provenance_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_current_approved_revision
              ON revisions(artifact_id)
              WHERE approval_status = 'approved';
            """
        )
        self._ensure_columns()
        self.conn.commit()

    def _ensure_columns(self):
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(runs)").fetchall()}
        additions = {
            "request_hash": "TEXT NOT NULL DEFAULT ''",
            "usage_status": "TEXT NOT NULL DEFAULT 'NOT_PROVIDED'",
            "prompt_tokens": "INTEGER NOT NULL DEFAULT 0",
            "completion_tokens": "INTEGER NOT NULL DEFAULT 0",
            "total_tokens": "INTEGER NOT NULL DEFAULT 0",
            "usage_raw_object_id": "TEXT NOT NULL DEFAULT ''",
        }
        for name, spec in additions.items():
            if name not in columns:
                self.conn.execute("ALTER TABLE runs ADD COLUMN %s %s" % (name, spec))
        approval_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(approval_records)").fetchall()}
        if approval_columns and "sequence" not in approval_columns:
            self.conn.executescript(
                """
                ALTER TABLE approval_records RENAME TO approval_records_old;
                CREATE TABLE approval_records (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  record_id TEXT NOT NULL UNIQUE,
                  revision_id TEXT NOT NULL,
                  artifact_id TEXT NOT NULL,
                  action TEXT NOT NULL,
                  reviewer TEXT NOT NULL,
                  note TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
                );
                INSERT INTO approval_records
                (sequence, record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                SELECT rowid, record_id, revision_id, artifact_id, action, reviewer, note, created_at
                FROM approval_records_old
                ORDER BY rowid;
                DROP TABLE approval_records_old;
                """
            )

    def write_text_object(self, text):
        data = text.encode("utf-8")
        object_id = hashlib.sha256(data).hexdigest()
        directory = self.objects_root / object_id[:2]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / object_id
        if not path.exists():
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        return object_id

    def object_path(self, object_id):
        return self.objects_root / object_id[:2] / object_id

    def read_text(self, object_id):
        data = self.object_path(object_id).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != object_id:
            raise RuntimeError("immutable object hash mismatch: %s" % object_id)
        return data.decode("utf-8")

    def ensure_artifact(self, artifact_id, artifact_type, project_id, chapter_id):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO artifacts
            (artifact_id, artifact_type, project_id, chapter_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (artifact_id, artifact_type, project_id, chapter_id, now_iso()),
        )
        self.conn.commit()

    def create_run(self, **values):
        values.setdefault("run_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        values.setdefault("started_at", values["created_at"])
        values.setdefault("completed_at", "")
        values.setdefault("duration_ms", 0)
        values.setdefault("response_object_id", "")
        values.setdefault("request_hash", values.get("input_hash", ""))
        values.setdefault("usage_status", "NOT_PROVIDED")
        values.setdefault("prompt_tokens", 0)
        values.setdefault("completion_tokens", 0)
        values.setdefault("total_tokens", 0)
        values.setdefault("usage_raw_object_id", "")
        values.setdefault("error_code", "")
        values.setdefault("error_message", "")
        columns = list(values)
        self.conn.execute(
            "INSERT INTO runs (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self.get_run(values["run_id"])

    def update_run(self, run_id, **values):
        values = dict(values)
        values.setdefault("completed_at", now_iso())
        columns = ", ".join("%s = ?" % key for key in values)
        self.conn.execute(
            "UPDATE runs SET %s WHERE run_id = ?" % columns,
            list(values.values()) + [run_id],
        )
        self.conn.commit()
        return self.get_run(run_id)

    def insert_input_snapshot(self, run_id, logical_type, source_relative_path, source_path, text):
        object_id = self.write_text_object(text)
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.conn.execute(
            """
            INSERT INTO input_snapshots
            (run_id, logical_type, source_relative_path, source_path, sha256, object_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, logical_type, source_relative_path, str(source_path), sha, object_id),
        )
        self.conn.commit()
        return object_id

    def input_snapshots(self, run_id):
        rows = self.conn.execute(
            "SELECT * FROM input_snapshots WHERE run_id = ? ORDER BY logical_type",
            (run_id,),
        ).fetchall()
        return [
            InputSnapshot(
                run_id=row["run_id"],
                logical_type=row["logical_type"],
                source_relative_path=row["source_relative_path"],
                source_path=Path(row["source_path"]),
                sha256=row["sha256"],
                object_id=row["object_id"],
            )
            for row in rows
        ]

    def insert_revision(self, **values):
        row = self.conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 AS n FROM revisions WHERE artifact_id = ?",
            (values["artifact_id"],),
        ).fetchone()
        previous = self.conn.execute(
            "SELECT revision_id FROM revisions WHERE artifact_id = ? ORDER BY number DESC LIMIT 1",
            (values["artifact_id"],),
        ).fetchone()
        values.setdefault("revision_id", uuid.uuid4().hex)
        values.setdefault("number", int(row["n"]))
        values.setdefault("supersedes_revision_id", previous["revision_id"] if previous else "")
        values.setdefault("approval_status", "pending")
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO revisions (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self.get_revision(values["revision_id"])

    def insert_validation(self, **values):
        values.setdefault("validation_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO validation_results (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self._validation_from_row(
            self.conn.execute(
                "SELECT * FROM validation_results WHERE validation_id = ?",
                (values["validation_id"],),
            ).fetchone()
        )

    def approve_in_transaction(self, revision, reviewer, note):
        record_id = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "UPDATE revisions SET approval_status = 'superseded' WHERE artifact_id = ? AND approval_status = 'approved'",
                (revision.artifact_id,),
            )
            self.conn.execute(
                "UPDATE revisions SET approval_status = 'approved' WHERE revision_id = ?",
                (revision.revision_id,),
            )
            self.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, revision.revision_id, revision.artifact_id, "script_approved", reviewer, note or "", now_iso()),
            )
        return self.approval_record(record_id)

    def record_rejection(self, revision, reviewer, note):
        record_id = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                "UPDATE revisions SET approval_status = 'rejected' WHERE revision_id = ?",
                (revision.revision_id,),
            )
            self.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, revision.revision_id, revision.artifact_id, "script_rejected", reviewer, note or "", now_iso()),
            )
        return self.approval_record(record_id)

    def approval_record(self, record_id):
        return self._approval_from_row(
            self.conn.execute("SELECT * FROM approval_records WHERE record_id = ?", (record_id,)).fetchone()
        )

    def latest_approval(self, revision_id):
        return self._approval_from_row(
            self.conn.execute(
                "SELECT * FROM approval_records WHERE revision_id = ? ORDER BY sequence DESC LIMIT 1",
                (revision_id,),
            ).fetchone()
        )

    def record_export(self, **values):
        values.setdefault("export_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO export_records (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self._export_from_row(
            self.conn.execute("SELECT * FROM export_records WHERE export_id = ?", (values["export_id"],)).fetchone()
        )

    def export_records(self, artifact_id):
        rows = self.conn.execute(
            "SELECT * FROM export_records WHERE artifact_id = ? ORDER BY created_at, export_id",
            (artifact_id,),
        ).fetchall()
        return [self._export_from_row(row) for row in rows]

    def artifacts(self):
        return [dict(row) for row in self.conn.execute("SELECT * FROM artifacts ORDER BY artifact_id").fetchall()]

    def get_run(self, run_id):
        return self._run_from_row(self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone())

    def get_revision(self, revision_id):
        return self._revision_from_row(
            self.conn.execute("SELECT * FROM revisions WHERE revision_id = ?", (revision_id,)).fetchone()
        )

    def revisions_for_artifact(self, artifact_id):
        rows = self.conn.execute(
            "SELECT * FROM revisions WHERE artifact_id = ? ORDER BY number",
            (artifact_id,),
        ).fetchall()
        return [self._revision_from_row(row) for row in rows]

    def validation_results(self, revision_id):
        rows = self.conn.execute(
            "SELECT * FROM validation_results WHERE revision_id = ? ORDER BY created_at, validator_id",
            (revision_id,),
        ).fetchall()
        return [self._validation_from_row(row) for row in rows]

    def current_approved(self, artifact_id):
        return self._revision_from_row(
            self.conn.execute(
                "SELECT * FROM revisions WHERE artifact_id = ? AND approval_status = 'approved' ORDER BY number DESC LIMIT 1",
                (artifact_id,),
            ).fetchone()
        )

    def to_json(self, record):
        return json.dumps(record.__dict__, ensure_ascii=False, sort_keys=True)

    def _run_from_row(self, row):
        return None if row is None else RunRecord(**dict(row))

    def _revision_from_row(self, row):
        return None if row is None else RevisionRecord(**dict(row))

    def _validation_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        data["required"] = bool(data["required"])
        return ValidationRecord(**data)

    def _approval_from_row(self, row):
        return None if row is None else ApprovalRecord(**dict(row))

    def _export_from_row(self, row):
        return None if row is None else ExportRecord(**dict(row))
