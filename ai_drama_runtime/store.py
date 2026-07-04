from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from ai_drama_runtime.shot_prompt_migration import (
    APPROVAL_ACTIONS,
    APPROVAL_EVIDENCE_COLUMNS,
    PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES,
    REVISION_APPROVAL_STATUSES,
    REVISION_OUTPUT_LOGICAL_TYPES,
    SHOT_PROMPT_ARTIFACT_TYPE,
    SHOT_PROMPT_BUSINESS_KEY_TYPE,
    _ensure_review_tables_for_conn,
)


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _quoted_sql_values(values):
    return ", ".join("'%s'" % value for value in values)


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
    content_profile: str
    derivation_type: str
    supersedes_revision_id: str
    approval_status: str
    created_at: str


@dataclass(frozen=True)
class RevisionDependencyRecord:
    child_revision_id: str
    parent_revision_id: str
    relation_type: str
    parent_content_hash: str
    parent_approval_record_id: str
    created_at: str


@dataclass(frozen=True)
class WorkflowGateRecord:
    gate_id: str
    run_id: str
    target_skill_id: str
    target_skill_version: str
    target_artifact_id: str
    source_revision_id: str
    request_reference: str
    error_code: str
    error_message: str
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
    source_storyboard_revision_id: str
    canonical_content_hash: str
    bundle_manifest_hash: str
    qualification_report_hash: str
    qualification_report_object_id: str
    renderer_profile_id: str
    renderer_profile_version: str
    qualification_profile_id: str
    qualification_profile_version: str


@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    artifact_id: str
    revision_id: str
    scope: str
    shot_id: Optional[str]
    body: str
    body_hash: str
    blocking: bool
    created_by: str
    created_at: str


@dataclass(frozen=True)
class ReviewEventRecord:
    event_id: str
    review_id: str
    event_type: str
    actor: str
    note: str
    created_at: str


@dataclass(frozen=True)
class RevisionOutputRecord:
    revision_output_id: str
    revision_id: str
    logical_type: str
    object_id: str
    content_hash: str
    media_type: str
    generator: str
    generator_version: str
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
    export_kind: str
    freshness_status: str
    diagnostic_only: bool
    not_an_execution_package: bool
    execution_ready: bool
    bundle_manifest_hash: str
    error_code: str


class RuntimeStore:
    def __init__(self, db_path, objects_root):
        self.db_path = Path(db_path)
        self.objects_root = Path(objects_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.objects_root.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            from ai_drama_runtime import shot_prompt_migration

            preview = shot_prompt_migration.preview_phase3_store_migration(self.db_path)
            if preview["status"] == "NEEDS_MIGRATION":
                shot_prompt_migration.apply_phase3_store_migration(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
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
        fresh_database = not self.conn.execute(
            """
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            LIMIT 1
            """
        ).fetchone()
        revision_output_logical_types = _quoted_sql_values(REVISION_OUTPUT_LOGICAL_TYPES)
        revision_approval_statuses = _quoted_sql_values(REVISION_APPROVAL_STATUSES)
        approval_actions = _quoted_sql_values(APPROVAL_ACTIONS)
        approval_evidence_columns = ", ".join(
            "%s TEXT NOT NULL DEFAULT ''" % name for name in APPROVAL_EVIDENCE_COLUMNS
        )
        self.conn.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS artifacts (
              artifact_id TEXT PRIMARY KEY,
              artifact_type TEXT NOT NULL,
              project_id TEXT NOT NULL,
              chapter_id TEXT NOT NULL,
              business_key_type TEXT NOT NULL DEFAULT '',
              business_key_value TEXT NOT NULL DEFAULT '',
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
              content_profile TEXT NOT NULL DEFAULT '',
              derivation_type TEXT NOT NULL DEFAULT 'model_generation',
              supersedes_revision_id TEXT NOT NULL,
              approval_status TEXT NOT NULL CHECK (approval_status IN (%s)),
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
              action TEXT NOT NULL CHECK (action IN (%s)),
              reviewer TEXT NOT NULL,
              note TEXT NOT NULL,
              created_at TEXT NOT NULL,
              %s,
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
              export_kind TEXT NOT NULL DEFAULT 'legacy_single' CHECK (export_kind IN ('legacy_single','formal_review','diagnostic','execution')),
              freshness_status TEXT NOT NULL DEFAULT '' CHECK (freshness_status IN ('','FRESH','STALE')),
              diagnostic_only INTEGER NOT NULL DEFAULT 0 CHECK (diagnostic_only IN (0,1)),
              not_an_execution_package INTEGER NOT NULL DEFAULT 1 CHECK (not_an_execution_package IN (0,1)),
              execution_ready INTEGER NOT NULL DEFAULT 0 CHECK (execution_ready IN (0,1)),
              bundle_manifest_hash TEXT NOT NULL DEFAULT '',
              error_code TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS revision_outputs (
              revision_output_id TEXT PRIMARY KEY,
              revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
              logical_type TEXT NOT NULL CHECK (logical_type IN (%s)),
              object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              media_type TEXT NOT NULL,
              generator TEXT NOT NULL,
              generator_version TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(revision_id, logical_type)
            );
            CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx ON revision_outputs(content_hash);
            CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx ON revision_outputs(object_id);
            CREATE TABLE IF NOT EXISTS revision_dependencies (
              child_revision_id TEXT NOT NULL,
              parent_revision_id TEXT NOT NULL,
              relation_type TEXT NOT NULL,
              parent_content_hash TEXT NOT NULL,
              parent_approval_record_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(child_revision_id, parent_revision_id, relation_type),
              FOREIGN KEY(child_revision_id) REFERENCES revisions(revision_id),
              FOREIGN KEY(parent_revision_id) REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS workflow_gate_records (
              gate_id TEXT PRIMARY KEY,
              run_id TEXT NOT NULL,
              target_skill_id TEXT NOT NULL,
              target_skill_version TEXT NOT NULL,
              target_artifact_id TEXT NOT NULL,
              source_revision_id TEXT NOT NULL,
              request_reference TEXT NOT NULL,
              error_code TEXT NOT NULL,
              error_message TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_current_approved_revision
              ON revisions(artifact_id)
              WHERE approval_status = 'approved';
            """
            % (
                revision_approval_statuses,
                approval_actions,
                approval_evidence_columns,
                revision_output_logical_types,
            )
        )
        if fresh_database:
            _ensure_review_tables_for_conn(self.conn)
        self._ensure_columns()
        artifact_columns = {
            row["name"] for row in self.conn.execute("PRAGMA table_info(artifacts)").fetchall()
        }
        if {"business_key_type", "business_key_value"} <= artifact_columns:
            self.conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS one_shot_prompt_set_per_source_storyboard_revision
                  ON artifacts(artifact_type, business_key_type, business_key_value)
                  WHERE artifact_type = 'shot_prompt_set'
                    AND business_key_type = 'source_storyboard_revision_id'
                """
            )
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
            approval_columns = {
                row["name"] for row in self.conn.execute("PRAGMA table_info(approval_records)").fetchall()
            }
        for name in APPROVAL_EVIDENCE_COLUMNS:
            if approval_columns and name not in approval_columns:
                self.conn.execute(
                    "ALTER TABLE approval_records ADD COLUMN %s TEXT NOT NULL DEFAULT ''" % name
                )
        dependency_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(revision_dependencies)").fetchall()}
        if dependency_columns and "parent_approval_record_id" not in dependency_columns:
            self.conn.executescript(
                """
                ALTER TABLE revision_dependencies RENAME TO revision_dependencies_old;
                CREATE TABLE revision_dependencies (
                  child_revision_id TEXT NOT NULL,
                  parent_revision_id TEXT NOT NULL,
                  relation_type TEXT NOT NULL,
                  parent_content_hash TEXT NOT NULL,
                  parent_approval_record_id TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  PRIMARY KEY(child_revision_id, parent_revision_id, relation_type),
                  FOREIGN KEY(child_revision_id) REFERENCES revisions(revision_id),
                  FOREIGN KEY(parent_revision_id) REFERENCES revisions(revision_id)
                );
                INSERT INTO revision_dependencies
                (child_revision_id, parent_revision_id, relation_type, parent_content_hash, parent_approval_record_id, created_at)
                SELECT child_revision_id, parent_revision_id, relation_type, parent_content_hash, parent_approval_record_id, created_at
                FROM revision_dependencies_old;
                DROP TABLE revision_dependencies_old;
                """
            )
        revision_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(revisions)").fetchall()}
        if revision_columns and "content_profile" not in revision_columns:
            self.conn.execute("ALTER TABLE revisions ADD COLUMN content_profile TEXT NOT NULL DEFAULT ''")
        if revision_columns and "derivation_type" not in revision_columns:
            self.conn.execute("ALTER TABLE revisions ADD COLUMN derivation_type TEXT NOT NULL DEFAULT 'model_generation'")
        self.conn.execute(
            """
            UPDATE revisions
            SET content_profile = CASE
              WHEN artifact_type = 'drama_script' THEN 'markdown-script-mvp-v1'
              WHEN artifact_type = 'storyboard' THEN 'storyboard-markdown-mvp-v1'
              ELSE content_profile
            END
            WHERE content_profile = ''
            """
        )
        gate_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(workflow_gate_records)").fetchall()}
        if gate_columns and "request_reference" not in gate_columns:
            self.conn.executescript(
                """
                ALTER TABLE workflow_gate_records RENAME TO workflow_gate_records_old;
                CREATE TABLE workflow_gate_records (
                  gate_id TEXT PRIMARY KEY,
                  run_id TEXT NOT NULL,
                  target_skill_id TEXT NOT NULL,
                  target_skill_version TEXT NOT NULL,
                  target_artifact_id TEXT NOT NULL,
                  source_revision_id TEXT NOT NULL,
                  request_reference TEXT NOT NULL,
                  error_code TEXT NOT NULL,
                  error_message TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                INSERT INTO workflow_gate_records
                (gate_id, run_id, target_skill_id, target_skill_version, target_artifact_id, source_revision_id, request_reference, error_code, error_message, created_at)
                SELECT gate_id, run_id, target_skill_id, target_skill_version, target_artifact_id, source_revision_id, '', error_code, error_message, created_at
                FROM workflow_gate_records_old;
                DROP TABLE workflow_gate_records_old;
                """
            )
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS revision_outputs (
              revision_output_id TEXT PRIMARY KEY,
              revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
              logical_type TEXT NOT NULL CHECK (logical_type IN ('rendered_positive_prompt', 'rendered_negative_prompt', 'rendered_markdown', 'bundle_manifest')),
              object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              media_type TEXT NOT NULL,
              generator TEXT NOT NULL,
              generator_version TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(revision_id, logical_type)
            );
            CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx ON revision_outputs(content_hash);
            CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx ON revision_outputs(object_id);
            """
        )
        export_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(export_records)").fetchall()}
        export_additions = {
            "export_kind": "TEXT NOT NULL DEFAULT 'legacy_single' CHECK (export_kind IN ('legacy_single','formal_review','diagnostic','execution'))",
            "freshness_status": "TEXT NOT NULL DEFAULT '' CHECK (freshness_status IN ('','FRESH','STALE'))",
            "diagnostic_only": "INTEGER NOT NULL DEFAULT 0 CHECK (diagnostic_only IN (0,1))",
            "not_an_execution_package": "INTEGER NOT NULL DEFAULT 1 CHECK (not_an_execution_package IN (0,1))",
            "execution_ready": "INTEGER NOT NULL DEFAULT 0 CHECK (execution_ready IN (0,1))",
            "bundle_manifest_hash": "TEXT NOT NULL DEFAULT ''",
            "error_code": "TEXT NOT NULL DEFAULT ''",
        }
        for name, spec in export_additions.items():
            if name not in export_columns:
                self.conn.execute("ALTER TABLE export_records ADD COLUMN %s %s" % (name, spec))

    def write_bytes_object(self, data):
        object_id = hashlib.sha256(data).hexdigest()
        directory = self.objects_root / object_id[:2]
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / object_id
        if not path.exists():
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        return object_id

    def read_bytes_object(self, object_id):
        data = self.object_path(object_id).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != object_id:
            raise RuntimeError("immutable object hash mismatch: %s" % object_id)
        return data

    def write_text_object(self, text):
        return self.write_bytes_object(text.encode("utf-8"))

    def object_path(self, object_id):
        return self.objects_root / object_id[:2] / object_id

    def read_text(self, object_id):
        return self.read_bytes_object(object_id).decode("utf-8")

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

    def artifact_by_business_key(self, artifact_type, business_key_type, business_key_value):
        row = self.conn.execute(
            """
            SELECT * FROM artifacts
            WHERE artifact_type = ? AND business_key_type = ? AND business_key_value = ?
            ORDER BY created_at, artifact_id
            LIMIT 1
            """,
            (artifact_type, business_key_type, business_key_value),
        ).fetchone()
        return None if row is None else dict(row)

    def ensure_shot_prompt_artifact(self, *, project_id, chapter_id, source_storyboard_revision_id):
        existing = self.artifact_by_business_key(
            SHOT_PROMPT_ARTIFACT_TYPE,
            SHOT_PROMPT_BUSINESS_KEY_TYPE,
            source_storyboard_revision_id,
        )
        if existing is not None:
            return existing
        artifact_id = uuid.uuid4().hex
        try:
            self.conn.execute(
                """
                INSERT INTO artifacts
                (artifact_id, artifact_type, project_id, chapter_id,
                 business_key_type, business_key_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    SHOT_PROMPT_ARTIFACT_TYPE,
                    project_id,
                    chapter_id,
                    SHOT_PROMPT_BUSINESS_KEY_TYPE,
                    source_storyboard_revision_id,
                    now_iso(),
                ),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            self.conn.rollback()
        return self.artifact_by_business_key(
            SHOT_PROMPT_ARTIFACT_TYPE,
            SHOT_PROMPT_BUSINESS_KEY_TYPE,
            source_storyboard_revision_id,
        )

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
        values.setdefault("derivation_type", "model_generation")
        if "content_profile" not in values:
            if values["artifact_type"] == "drama_script":
                values["content_profile"] = "markdown-script-mvp-v1"
            elif values["artifact_type"] == "storyboard":
                values["content_profile"] = "storyboard-markdown-mvp-v1"
            else:
                values["content_profile"] = ""
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
        action = "storyboard_approved" if revision.artifact_type == "storyboard" else "script_approved"
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
                (record_id, revision.revision_id, revision.artifact_id, action, reviewer, note or "", now_iso()),
            )
        return self.approval_record(record_id)

    def record_rejection(self, revision, reviewer, note):
        record_id = uuid.uuid4().hex
        action = "storyboard_rejected" if revision.artifact_type == "storyboard" else "script_rejected"
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
                (record_id, revision.revision_id, revision.artifact_id, action, reviewer, note or "", now_iso()),
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

    def insert_revision_outputs_transaction(self, rows):
        created = []
        now = now_iso()
        for row in rows:
            values = dict(row)
            values.setdefault("revision_output_id", uuid.uuid4().hex)
            values.setdefault("created_at", now)
            columns = list(values)
            self.conn.execute(
                "INSERT INTO revision_outputs (%s) VALUES (%s)"
                % (",".join(columns), ",".join("?" for _ in columns)),
                [values[column] for column in columns],
            )
            created.append(self.get_revision_output(values["revision_id"], values["logical_type"]))
        return created

    def insert_phase3_revision_outputs_atomically(self, revision_id, rows):
        if self.get_revision(revision_id) is None:
            raise ValueError("revision does not exist")
        rows = [dict(row) for row in rows]
        logical_types = [row.get("logical_type") for row in rows]
        if len(set(logical_types)) != len(logical_types):
            raise ValueError("phase3 output logical types must be unique")
        if set(logical_types) != set(PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES):
            raise ValueError("phase3 outputs must match required logical type set")
        for row in rows:
            if row.get("revision_id") != revision_id:
                raise ValueError("phase3 output revision_id mismatch")
        ordered_rows = sorted(
            rows,
            key=lambda row: PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES.index(row["logical_type"]),
        )
        with self.conn:
            return self._insert_revision_output_rows_no_commit(ordered_rows)

    def _insert_revision_output_rows_no_commit(self, rows):
        return self.insert_revision_outputs_transaction(rows)

    def insert_export_record_in_transaction(self, **values):
        values.setdefault("export_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        values.setdefault("export_kind", "legacy_single")
        values.setdefault("freshness_status", "")
        values.setdefault("diagnostic_only", 0)
        values.setdefault("not_an_execution_package", 1)
        values.setdefault("execution_ready", 0)
        values.setdefault("bundle_manifest_hash", "")
        values.setdefault("error_code", "")
        columns = list(values)
        self.conn.execute(
            "INSERT INTO export_records (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        return self.get_export_record(values["export_id"])

    def insert_export_record(self, **values):
        with self.conn:
            return self.insert_export_record_in_transaction(**values)

    def insert_revision_dependency(self, **values):
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO revision_dependencies (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self.revision_dependencies(values["child_revision_id"])[-1]

    def insert_workflow_gate_record(self, **values):
        values.setdefault("gate_id", uuid.uuid4().hex)
        values.setdefault("created_at", now_iso())
        columns = list(values)
        self.conn.execute(
            "INSERT INTO workflow_gate_records (%s) VALUES (%s)"
            % (",".join(columns), ",".join("?" for _ in columns)),
            [values[column] for column in columns],
        )
        self.conn.commit()
        return self.workflow_gate_record(values["gate_id"])

    def export_records(self, artifact_id):
        rows = self.conn.execute(
            "SELECT * FROM export_records WHERE artifact_id = ? ORDER BY created_at, export_id",
            (artifact_id,),
        ).fetchall()
        return [self._export_from_row(row) for row in rows]

    def revision_outputs(self, revision_id):
        rows = self.conn.execute(
            "SELECT * FROM revision_outputs WHERE revision_id = ? ORDER BY created_at, logical_type, revision_output_id",
            (revision_id,),
        ).fetchall()
        return [self._revision_output_from_row(row) for row in rows]

    def get_revision_output(self, revision_id, logical_type):
        return self._revision_output_from_row(
            self.conn.execute(
                "SELECT * FROM revision_outputs WHERE revision_id = ? AND logical_type = ?",
                (revision_id, logical_type),
            ).fetchone()
        )

    def get_export_record(self, export_id):
        return self._export_from_row(
            self.conn.execute("SELECT * FROM export_records WHERE export_id = ?", (export_id,)).fetchone()
        )

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

    def revision_dependencies(self, child_revision_id):
        rows = self.conn.execute(
            "SELECT * FROM revision_dependencies WHERE child_revision_id = ? ORDER BY created_at, parent_revision_id",
            (child_revision_id,),
        ).fetchall()
        return [RevisionDependencyRecord(**dict(row)) for row in rows]

    def revision_dependents(self, parent_revision_id):
        rows = self.conn.execute(
            "SELECT * FROM revision_dependencies WHERE parent_revision_id = ? ORDER BY created_at, child_revision_id",
            (parent_revision_id,),
        ).fetchall()
        return [RevisionDependencyRecord(**dict(row)) for row in rows]

    def workflow_gate_record(self, gate_id):
        row = self.conn.execute("SELECT * FROM workflow_gate_records WHERE gate_id = ?", (gate_id,)).fetchone()
        return None if row is None else WorkflowGateRecord(**dict(row))

    def workflow_gate_records(self):
        rows = self.conn.execute("SELECT * FROM workflow_gate_records ORDER BY created_at, gate_id").fetchall()
        return [WorkflowGateRecord(**dict(row)) for row in rows]

    def validation_results(self, revision_id):
        rows = self.conn.execute(
            "SELECT * FROM validation_results WHERE revision_id = ? ORDER BY created_at, validator_id",
            (revision_id,),
        ).fetchall()
        return [self._validation_from_row(row) for row in rows]

    def latest_validation_result(self, revision_id, validator_id):
        row = self.conn.execute(
            """
            SELECT * FROM validation_results
            WHERE revision_id = ? AND validator_id = ?
            ORDER BY created_at DESC, validation_id DESC
            LIMIT 1
            """,
            (revision_id, validator_id),
        ).fetchone()
        return self._validation_from_row(row)

    def latest_validation_results(self, revision_id):
        rows = self.conn.execute(
            """
            SELECT * FROM validation_results
            WHERE revision_id = ?
            ORDER BY created_at ASC, validation_id ASC
            """,
            (revision_id,),
        ).fetchall()
        latest = {}
        for row in rows:
            record = self._validation_from_row(row)
            latest[record.validator_id] = record
        return latest

    def review_record(self, review_id):
        return self._review_from_row(
            self.conn.execute(
                "SELECT * FROM review_records WHERE review_id = ?",
                (review_id,),
            ).fetchone()
        )

    def review_event(self, event_id):
        return self._review_event_from_row(
            self.conn.execute(
                "SELECT * FROM review_record_events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        )

    def review_events(self, review_id):
        rows = self.conn.execute(
            """
            SELECT * FROM review_record_events
            WHERE review_id = ?
            ORDER BY created_at, event_id
            """,
            (review_id,),
        ).fetchall()
        return [self._review_event_from_row(row) for row in rows]

    def _insert_review_event_row(
        self,
        *,
        review_id,
        event_type,
        actor,
        note="",
        event_id=None,
        created_at=None,
    ):
        event_id = event_id or uuid.uuid4().hex
        created_at = created_at or now_iso()
        self.conn.execute(
            """
            INSERT INTO review_record_events
            (event_id, review_id, event_type, actor, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, review_id, event_type, actor, note, created_at),
        )
        return self.review_event(event_id)

    def insert_review_event(self, *, review_id, event_type, actor, note=""):
        with self.conn:
            return self._insert_review_event_row(
                review_id=review_id,
                event_type=event_type,
                actor=actor,
                note=note,
            )

    def _insert_review_record_row(
        self,
        *,
        review_id,
        artifact_id,
        revision_id,
        scope,
        shot_id,
        body,
        body_hash,
        blocking,
        created_by,
        created_at,
    ):
        self.conn.execute(
            """
            INSERT INTO review_records
            (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                artifact_id,
                revision_id,
                scope,
                shot_id,
                body,
                body_hash,
                int(blocking),
                created_by,
                created_at,
            ),
        )
        return self.review_record(review_id)

    def insert_review_record_with_opened_event(
        self,
        *,
        artifact_id,
        revision_id,
        scope,
        shot_id,
        body,
        blocking,
        created_by,
        note="",
    ):
        review_id = uuid.uuid4().hex
        body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        with self.conn:
            created_at = now_iso()
            self._insert_review_record_row(
                review_id=review_id,
                artifact_id=artifact_id,
                revision_id=revision_id,
                scope=scope,
                shot_id=shot_id,
                body=body,
                body_hash=body_hash,
                blocking=blocking,
                created_by=created_by,
                created_at=created_at,
            )
            self._insert_review_event_row(
                review_id=review_id,
                event_type="opened",
                actor=created_by,
                note=note,
                created_at=created_at,
            )
        return self.review_record(review_id)

    def review_status(self, review_id):
        row = self.conn.execute(
            """
            SELECT event_type FROM review_record_events
            WHERE review_id = ?
            ORDER BY created_at DESC, event_id DESC
            LIMIT 1
            """,
            (review_id,),
        ).fetchone()
        return "" if row is None else row["event_type"]

    def open_blocking_review_count(self, revision_id):
        rows = self.conn.execute(
            """
            SELECT review_id FROM review_records
            WHERE revision_id = ? AND blocking = 1
            ORDER BY created_at, review_id
            """,
            (revision_id,),
        ).fetchall()
        return sum(
            1
            for row in rows
            if self.review_status(row["review_id"]) not in {"resolved", "voided"}
        )

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

    def _review_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        data["blocking"] = bool(data["blocking"])
        return ReviewRecord(**data)

    def _review_event_from_row(self, row):
        return None if row is None else ReviewEventRecord(**dict(row))

    def _revision_output_from_row(self, row):
        return None if row is None else RevisionOutputRecord(**dict(row))

    def _export_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        data["diagnostic_only"] = bool(data["diagnostic_only"])
        data["not_an_execution_package"] = bool(data["not_an_execution_package"])
        data["execution_ready"] = bool(data["execution_ready"])
        return ExportRecord(**data)
