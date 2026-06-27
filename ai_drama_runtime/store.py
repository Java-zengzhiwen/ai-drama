from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import time
import uuid


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    artifact_id: str
    skill_id: str
    skill_version: str
    skill_hash: str
    runtime: str
    model: str
    status: str
    request_object_id: str
    response_object_id: str
    input_hash: str
    created_at: str


@dataclass(frozen=True)
class RevisionRecord:
    revision_id: str
    artifact_id: str
    run_id: str
    number: int
    content_object_id: str
    content_hash: str
    approval_status: str
    created_at: str


@dataclass(frozen=True)
class ValidationRecord:
    validation_id: str
    revision_id: str
    validator_name: str
    status: str
    required: bool
    exit_code: int
    stdout_object_id: str
    stderr_object_id: str
    report_object_id: str
    created_at: str


@dataclass(frozen=True)
class ExportRecord:
    export_id: str
    artifact_id: str
    revision_id: str
    content_hash: str
    destination: str
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

    def _init_schema(self):
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS runs (
              run_id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL,
              skill_id TEXT NOT NULL,
              skill_version TEXT NOT NULL,
              skill_hash TEXT NOT NULL,
              runtime TEXT NOT NULL,
              model TEXT NOT NULL,
              status TEXT NOT NULL,
              request_object_id TEXT NOT NULL,
              response_object_id TEXT NOT NULL,
              input_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS revisions (
              revision_id TEXT PRIMARY KEY,
              artifact_id TEXT NOT NULL,
              run_id TEXT NOT NULL,
              number INTEGER NOT NULL,
              content_object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              approval_status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(run_id) REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS validation_results (
              validation_id TEXT PRIMARY KEY,
              revision_id TEXT NOT NULL,
              validator_name TEXT NOT NULL,
              status TEXT NOT NULL,
              required INTEGER NOT NULL,
              exit_code INTEGER NOT NULL,
              stdout_object_id TEXT NOT NULL,
              stderr_object_id TEXT NOT NULL,
              report_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS approval_records (
              record_id TEXT PRIMARY KEY,
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
              content_hash TEXT NOT NULL,
              destination TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_current_approved_revision
              ON revisions(artifact_id)
              WHERE approval_status = 'approved';
            """
        )
        self.conn.commit()

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

    def insert_run(self, **values):
        values.setdefault("run_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO runs (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self.get_run(values["run_id"])

    def insert_revision(self, artifact_id, run_id, content_object_id, content_hash):
        row = self.conn.execute(
            "SELECT COALESCE(MAX(number), 0) + 1 AS n FROM revisions WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()
        values = {
            "revision_id": uuid.uuid4().hex,
            "artifact_id": artifact_id,
            "run_id": run_id,
            "number": int(row["n"]),
            "content_object_id": content_object_id,
            "content_hash": content_hash,
            "approval_status": "pending",
            "created_at": now_iso(),
        }
        self.conn.execute(
            """
            INSERT INTO revisions
            (revision_id, artifact_id, run_id, number, content_object_id, content_hash, approval_status, created_at)
            VALUES (:revision_id, :artifact_id, :run_id, :number, :content_object_id, :content_hash, :approval_status, :created_at)
            """,
            values,
        )
        self.conn.commit()
        return self.get_revision(values["revision_id"])

    def insert_validation(self, **values):
        values.setdefault("validation_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        self.conn.execute(
            """
            INSERT INTO validation_results
            (validation_id, revision_id, validator_name, status, required, exit_code, stdout_object_id, stderr_object_id, report_object_id, created_at)
            VALUES (:validation_id, :revision_id, :validator_name, :status, :required, :exit_code, :stdout_object_id, :stderr_object_id, :report_object_id, :created_at)
            """,
            values,
        )
        self.conn.commit()
        return self._validation_from_row(
            self.conn.execute(
                "SELECT * FROM validation_results WHERE validation_id = ?",
                (values["validation_id"],),
            ).fetchone()
        )

    def record_approval(self, revision_id, artifact_id, action, reviewer, note):
        self.conn.execute(
            """
            INSERT INTO approval_records
            (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (uuid.uuid4().hex, revision_id, artifact_id, action, reviewer, note or "", now_iso()),
        )
        self.conn.commit()

    def record_export(self, artifact_id, revision_id, content_hash, destination):
        values = {
            "export_id": uuid.uuid4().hex,
            "artifact_id": artifact_id,
            "revision_id": revision_id,
            "content_hash": content_hash,
            "destination": str(destination),
            "created_at": now_iso(),
        }
        self.conn.execute(
            """
            INSERT INTO export_records
            (export_id, artifact_id, revision_id, content_hash, destination, created_at)
            VALUES (:export_id, :artifact_id, :revision_id, :content_hash, :destination, :created_at)
            """,
            values,
        )
        self.conn.commit()
        return ExportRecord(**values)

    def export_records(self, artifact_id):
        rows = self.conn.execute(
            "SELECT * FROM export_records WHERE artifact_id = ? ORDER BY created_at",
            (artifact_id,),
        ).fetchall()
        return [ExportRecord(**dict(row)) for row in rows]

    def get_run(self, run_id):
        return self._run_from_row(
            self.conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        )

    def get_revision(self, revision_id):
        return self._revision_from_row(
            self.conn.execute("SELECT * FROM revisions WHERE revision_id = ?", (revision_id,)).fetchone()
        )

    def validation_results(self, revision_id):
        rows = self.conn.execute(
            "SELECT * FROM validation_results WHERE revision_id = ? ORDER BY created_at, validator_name",
            (revision_id,),
        ).fetchall()
        return [self._validation_from_row(row) for row in rows]

    def set_approved(self, revision):
        with self.conn:
            self.conn.execute(
                "UPDATE revisions SET approval_status = 'superseded' WHERE artifact_id = ? AND approval_status = 'approved'",
                (revision.artifact_id,),
            )
            self.conn.execute(
                "UPDATE revisions SET approval_status = 'approved' WHERE revision_id = ?",
                (revision.revision_id,),
            )

    def set_rejected(self, revision):
        self.conn.execute(
            "UPDATE revisions SET approval_status = 'rejected' WHERE revision_id = ?",
            (revision.revision_id,),
        )
        self.conn.commit()

    def current_approved(self, artifact_id):
        row = self.conn.execute(
            """
            SELECT * FROM revisions
            WHERE artifact_id = ? AND approval_status = 'approved'
            ORDER BY number DESC LIMIT 1
            """,
            (artifact_id,),
        ).fetchone()
        return self._revision_from_row(row)

    def to_json(self, record):
        return json.dumps(record.__dict__, ensure_ascii=False, sort_keys=True)

    def _run_from_row(self, row):
        if row is None:
            return None
        return RunRecord(**dict(row))

    def _revision_from_row(self, row):
        if row is None:
            return None
        return RevisionRecord(**dict(row))

    def _validation_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        data["required"] = bool(data["required"])
        return ValidationRecord(**data)
