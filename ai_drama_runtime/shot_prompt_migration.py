import sqlite3
from pathlib import Path


SHOT_PROMPT_ARTIFACT_TYPE = "shot_prompt_set"
SHOT_PROMPT_BUSINESS_KEY_TYPE = "source_storyboard_revision_id"
REVISION_APPROVAL_STATUSES = ("pending", "approved", "rejected", "superseded", "revoked")
APPROVAL_ACTIONS = (
    "script_approved",
    "script_rejected",
    "storyboard_approved",
    "storyboard_rejected",
    "shot_prompt_approved",
    "shot_prompt_rejected",
    "shot_prompt_approval_revoked",
)
APPROVAL_EVIDENCE_COLUMNS = (
    "source_storyboard_revision_id",
    "canonical_content_hash",
    "bundle_manifest_hash",
    "qualification_report_hash",
    "qualification_report_object_id",
    "renderer_profile_id",
    "renderer_profile_version",
    "qualification_profile_id",
    "qualification_profile_version",
)
REVIEW_EVENT_TYPES = ("opened", "resolved", "reopened", "voided")
PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES = (
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)
REVISION_OUTPUT_LOGICAL_TYPES = (
    "rendered_positive_prompt",
    "rendered_negative_prompt",
    "rendered_markdown",
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)


class Phase3StoreMigrationError(RuntimeError):
    pass


def preview_phase3_store_migration(db_path):
    conn = _connect(db_path)
    try:
        artifact_sql = _index_sql(conn, "one_shot_prompt_set_per_source_storyboard_revision")
        revision_output_sql = _table_sql(conn, "revision_outputs")
        revisions_sql = _table_sql(conn, "revisions")
        approval_sql = _table_sql(conn, "approval_records")
        approval_columns = _columns(conn, "approval_records")
        checks = {
            "artifact_business_key": _check(
                {"business_key_type", "business_key_value"} <= _columns(conn, "artifacts")
                and "artifact_type = 'shot_prompt_set'" in artifact_sql
                and "business_key_type = 'source_storyboard_revision_id'" in artifact_sql
            ),
            "revision_outputs_check": _check(
                all(value in revision_output_sql for value in REVISION_OUTPUT_LOGICAL_TYPES)
            ),
            "revision_status_check": _check(
                all(value in revisions_sql for value in REVISION_APPROVAL_STATUSES)
                and "approval_status TEXT NOT NULL CHECK" in revisions_sql
            ),
            "approval_action_check": _check(
                all(value in approval_sql for value in APPROVAL_ACTIONS)
            ),
            "approval_evidence_columns": _check(
                set(APPROVAL_EVIDENCE_COLUMNS) <= approval_columns
            ),
            "review_tables": _check(_review_tables_ddl_is_current(conn)),
            "review_indexes": _check(_review_indexes_are_current(conn)),
            "foreign_key_check": _check(
                conn.execute("PRAGMA foreign_key_check").fetchall() == []
            ),
        }
        status = (
            "CURRENT"
            if all(item["status"] == "OK" for item in checks.values())
            else "NEEDS_MIGRATION"
        )
        return {"status": status, "database_path": str(Path(db_path)), "checks": checks}
    finally:
        conn.close()


def _migration_is_current(db_path):
    if preview_phase3_store_migration(db_path)["status"] != "CURRENT":
        return False
    conn = _connect(db_path)
    try:
        return (
            _artifacts_schema_is_current(conn)
            and _export_records_schema_is_current(conn)
            and _input_snapshots_schema_is_current(conn)
            and _review_tables_schema_is_current(conn)
        )
    finally:
        conn.close()


def phase3_store_migration_is_current(db_path):
    return _migration_is_current(db_path)


def apply_phase3_store_migration(db_path):
    db_path = Path(db_path)
    if _migration_is_current(db_path):
        return {"status": "ALREADY_CURRENT", "database_path": str(db_path)}

    conn = _connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            _rebuild_artifacts_for_phase3(conn)
            _ensure_input_snapshots_table_for_conn(conn)
            _rebuild_revisions_for_phase3(conn)
            _rebuild_revision_outputs_for_phase3(conn)
            _rebuild_approval_records_for_phase3(conn)
            _rebuild_export_records_for_phase3(conn)
            _ensure_review_tables_for_conn(conn)
            failures = conn.execute("PRAGMA foreign_key_check").fetchall()
            if failures:
                raise Phase3StoreMigrationError("foreign key check failed")
            conn.commit()
        except Exception as exc:
            conn.rollback()
            transient = conn.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND (name LIKE '%_old' OR name LIKE '%_new')
                """
            ).fetchall()
            if transient:
                raise Phase3StoreMigrationError("rollback left transient migration tables") from exc
            if isinstance(exc, Phase3StoreMigrationError):
                raise
            raise Phase3StoreMigrationError(str(exc)) from exc
        finally:
            conn.execute("PRAGMA foreign_keys = ON")
        if not _migration_is_current(db_path):
            raise Phase3StoreMigrationError("migration finished but preview is not current")
        return {"status": "APPLIED", "database_path": str(db_path)}
    finally:
        conn.close()


MIGRATION_STEPS = (
    "artifact_business_key",
    "revision_status",
    "revision_outputs",
    "approval_records",
    "review_tables",
    "foreign_key_check",
)


def _ensure_artifact_business_key_columns_for_conn(conn):
    columns = _columns(conn, "artifacts")
    for name in ("business_key_type", "business_key_value"):
        if name not in columns:
            conn.execute("ALTER TABLE artifacts ADD COLUMN %s TEXT NOT NULL DEFAULT ''" % name)
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS one_shot_prompt_set_per_source_storyboard_revision
          ON artifacts(artifact_type, business_key_type, business_key_value)
          WHERE artifact_type = 'shot_prompt_set'
            AND business_key_type = 'source_storyboard_revision_id'
        """
    )


def _column_names(conn, table_name):
    return [
        row["name"]
        for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    ]


def _create_artifacts_table(conn):
    conn.execute(
        """
        CREATE TABLE artifacts (
          artifact_id TEXT PRIMARY KEY,
          artifact_type TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          business_key_type TEXT NOT NULL DEFAULT '',
          business_key_value TEXT NOT NULL DEFAULT '',
          created_at TEXT NOT NULL
        )
        """
    )


def _create_artifact_business_key_index(conn):
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS one_shot_prompt_set_per_source_storyboard_revision
          ON artifacts(artifact_type, business_key_type, business_key_value)
          WHERE artifact_type = 'shot_prompt_set'
            AND business_key_type = 'source_storyboard_revision_id'
        """
    )


def _artifacts_schema_is_current(conn):
    return _column_names(conn, "artifacts") == [
        "artifact_id",
        "artifact_type",
        "project_id",
        "chapter_id",
        "business_key_type",
        "business_key_value",
        "created_at",
    ] and "business_key_type = 'source_storyboard_revision_id'" in _index_sql(
        conn, "one_shot_prompt_set_per_source_storyboard_revision"
    )


def _rebuild_artifacts_for_phase3(conn):
    if _artifacts_schema_is_current(conn):
        return
    existing_columns = _columns(conn, "artifacts")
    conn.execute("DROP INDEX IF EXISTS one_shot_prompt_set_per_source_storyboard_revision")
    conn.execute("ALTER TABLE artifacts RENAME TO artifacts_old")
    _create_artifacts_table(conn)
    business_key_type = (
        "business_key_type"
        if "business_key_type" in existing_columns
        else "'' AS business_key_type"
    )
    business_key_value = (
        "business_key_value"
        if "business_key_value" in existing_columns
        else "'' AS business_key_value"
    )
    conn.execute(
        """
        INSERT INTO artifacts
        (artifact_id, artifact_type, project_id, chapter_id, business_key_type, business_key_value, created_at)
        SELECT artifact_id, artifact_type, project_id, chapter_id, %s, %s, created_at
        FROM artifacts_old
        ORDER BY created_at, artifact_id
        """
        % (business_key_type, business_key_value)
    )
    conn.execute("DROP TABLE artifacts_old")
    _create_artifact_business_key_index(conn)


def _quoted(values):
    return ", ".join("'%s'" % value for value in values)


def _revision_output_check_sql():
    return "logical_type TEXT NOT NULL CHECK (logical_type IN (%s))" % _quoted(
        REVISION_OUTPUT_LOGICAL_TYPES
    )


def _create_revision_outputs_table(conn):
    conn.execute(
        """
        CREATE TABLE revision_outputs (
          revision_output_id TEXT PRIMARY KEY,
          revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE RESTRICT,
          %s,
          object_id TEXT NOT NULL,
          content_hash TEXT NOT NULL,
          media_type TEXT NOT NULL,
          generator TEXT NOT NULL,
          generator_version TEXT NOT NULL,
          created_at TEXT NOT NULL,
          UNIQUE(revision_id, logical_type)
        )
        """
        % _revision_output_check_sql()
    )


def _rebuild_revision_outputs_for_phase3(conn):
    current_sql = _table_sql(conn, "revision_outputs")
    if current_sql == "":
        _create_revision_outputs_table(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx "
            "ON revision_outputs(content_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx "
            "ON revision_outputs(object_id)"
        )
        return
    if all(value in current_sql for value in REVISION_OUTPUT_LOGICAL_TYPES):
        return
    conn.execute("ALTER TABLE revision_outputs RENAME TO revision_outputs_old")
    _create_revision_outputs_table(conn)
    conn.execute(
        """
        INSERT INTO revision_outputs
        (revision_output_id, revision_id, logical_type, object_id, content_hash,
         media_type, generator, generator_version, created_at)
        SELECT revision_output_id, revision_id, logical_type, object_id, content_hash,
               media_type, generator, generator_version, created_at
        FROM revision_outputs_old
        ORDER BY created_at, revision_output_id
        """
    )
    conn.execute("DROP TABLE revision_outputs_old")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx "
        "ON revision_outputs(content_hash)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx "
        "ON revision_outputs(object_id)"
    )


def _revision_status_check_sql():
    return "approval_status TEXT NOT NULL CHECK (approval_status IN (%s))" % _quoted(
        REVISION_APPROVAL_STATUSES
    )


def _create_revisions_table(conn):
    conn.execute(
        """
        CREATE TABLE revisions (
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
          %s,
          created_at TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        """
        % _revision_status_check_sql()
    )


def _rebuild_revisions_for_phase3(conn):
    current_sql = _table_sql(conn, "revisions")
    if (
        all(value in current_sql for value in REVISION_APPROVAL_STATUSES)
        and "approval_status TEXT NOT NULL CHECK" in current_sql
    ):
        return
    previous_legacy_alter = conn.execute("PRAGMA legacy_alter_table").fetchone()[0]
    conn.execute("PRAGMA legacy_alter_table = ON")
    try:
        conn.execute("DROP INDEX IF EXISTS one_current_approved_revision")
        conn.execute("ALTER TABLE revisions RENAME TO revisions_old")
        _create_revisions_table(conn)
        conn.execute(
            """
            INSERT INTO revisions
            (revision_id, artifact_id, artifact_type, project_id, chapter_id, run_id,
             skill_id, skill_version, skill_package_hash, runtime_provider, runtime_model,
             number, content_object_id, content_hash, raw_response_object_id,
             parser_version, content_profile, derivation_type, supersedes_revision_id,
             approval_status, created_at)
            SELECT revision_id, artifact_id, artifact_type, project_id, chapter_id, run_id,
                   skill_id, skill_version, skill_package_hash, runtime_provider, runtime_model,
                   number, content_object_id, content_hash, raw_response_object_id,
                   parser_version, content_profile, derivation_type, supersedes_revision_id,
                   approval_status, created_at
            FROM revisions_old
            ORDER BY artifact_id, number
            """
        )
        conn.execute("DROP TABLE revisions_old")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS one_current_approved_revision
              ON revisions(artifact_id)
              WHERE approval_status = 'approved'
            """
        )
    finally:
        conn.execute("PRAGMA legacy_alter_table = %d" % previous_legacy_alter)


def _approval_action_check_sql():
    return "action TEXT NOT NULL CHECK (action IN (%s))" % _quoted(APPROVAL_ACTIONS)


def _approval_evidence_columns_sql():
    return ", ".join("%s TEXT NOT NULL DEFAULT ''" % name for name in APPROVAL_EVIDENCE_COLUMNS)


def _create_approval_records_table(conn):
    conn.execute(
        """
        CREATE TABLE approval_records (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          record_id TEXT NOT NULL UNIQUE,
          revision_id TEXT NOT NULL,
          artifact_id TEXT NOT NULL,
          %s,
          reviewer TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          %s,
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        )
        """
        % (_approval_action_check_sql(), _approval_evidence_columns_sql())
    )


def _export_records_columns():
    return [
        "export_id",
        "artifact_id",
        "revision_id",
        "run_id",
        "content_hash",
        "destination",
        "provenance_object_id",
        "created_at",
        "export_kind",
        "freshness_status",
        "diagnostic_only",
        "not_an_execution_package",
        "execution_ready",
        "bundle_manifest_hash",
        "error_code",
    ]


def _create_export_records_table(conn):
    conn.execute(
        """
        CREATE TABLE export_records (
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
        )
        """
    )


def _export_records_schema_is_current(conn):
    current_sql = _table_sql(conn, "export_records")
    return _column_names(conn, "export_records") == _export_records_columns() and all(
        token in current_sql
        for token in (
            "export_kind TEXT NOT NULL DEFAULT 'legacy_single' CHECK",
            "freshness_status TEXT NOT NULL DEFAULT '' CHECK",
            "diagnostic_only INTEGER NOT NULL DEFAULT 0 CHECK",
            "not_an_execution_package INTEGER NOT NULL DEFAULT 1 CHECK",
            "execution_ready INTEGER NOT NULL DEFAULT 0 CHECK",
            "bundle_manifest_hash TEXT NOT NULL DEFAULT ''",
            "error_code TEXT NOT NULL DEFAULT ''",
        )
    )


def _rebuild_export_records_for_phase3(conn):
    if _export_records_schema_is_current(conn):
        return
    existing_columns = _columns(conn, "export_records")
    conn.execute("ALTER TABLE export_records RENAME TO export_records_old")
    _create_export_records_table(conn)
    select_values = []
    defaults = {
        "export_kind": "'legacy_single' AS export_kind",
        "freshness_status": "'' AS freshness_status",
        "diagnostic_only": "0 AS diagnostic_only",
        "not_an_execution_package": "1 AS not_an_execution_package",
        "execution_ready": "0 AS execution_ready",
        "bundle_manifest_hash": "'' AS bundle_manifest_hash",
        "error_code": "'' AS error_code",
    }
    for column in _export_records_columns():
        select_values.append(column if column in existing_columns else defaults[column])
    conn.execute(
        """
        INSERT INTO export_records
        (%s)
        SELECT %s
        FROM export_records_old
        ORDER BY created_at, export_id
        """
        % (", ".join(_export_records_columns()), ", ".join(select_values))
    )
    conn.execute("DROP TABLE export_records_old")


def _input_snapshots_schema_is_current(conn):
    return _column_names(conn, "input_snapshots") == [
        "run_id",
        "logical_type",
        "source_relative_path",
        "source_path",
        "sha256",
        "object_id",
    ]


def _ensure_input_snapshots_table_for_conn(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS input_snapshots (
          run_id TEXT NOT NULL,
          logical_type TEXT NOT NULL,
          source_relative_path TEXT NOT NULL,
          source_path TEXT NOT NULL,
          sha256 TEXT NOT NULL,
          object_id TEXT NOT NULL,
          PRIMARY KEY(run_id, logical_type),
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        )
        """
    )


def _review_event_check_sql():
    return "event_type TEXT NOT NULL CHECK (event_type IN (%s))" % _quoted(
        REVIEW_EVENT_TYPES
    )


def _review_tables_schema_is_current(conn):
    return _review_tables_ddl_is_current(conn) and _review_indexes_are_current(conn)


def _review_tables_ddl_is_current(conn):
    review_records_sql = _table_sql(conn, "review_records")
    review_record_events_sql = _table_sql(conn, "review_record_events")
    return (
        "review_id TEXT PRIMARY KEY" in review_records_sql
        and "artifact_id TEXT NOT NULL" in review_records_sql
        and "revision_id TEXT NOT NULL" in review_records_sql
        and "scope TEXT NOT NULL CHECK (scope IN ('set','shot'))" in review_records_sql
        and "shot_id TEXT" in review_records_sql
        and "body_hash TEXT NOT NULL" in review_records_sql
        and "blocking INTEGER NOT NULL CHECK (blocking IN (0,1))" in review_records_sql
        and "scope = 'set' AND shot_id IS NULL" in review_records_sql
        and "scope = 'shot' AND shot_id IS NOT NULL" in review_records_sql
        and "FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)" in review_records_sql
        and "event_id TEXT PRIMARY KEY" in review_record_events_sql
        and "review_id TEXT NOT NULL" in review_record_events_sql
        and all(value in review_record_events_sql for value in REVIEW_EVENT_TYPES)
        and "FOREIGN KEY(review_id) REFERENCES review_records(review_id)" in review_record_events_sql
    )


def _review_indexes_are_current(conn):
    return (
        _index_sql(conn, "review_records_revision_shot_idx")
        == "CREATE INDEX review_records_revision_shot_idx ON review_records(revision_id, shot_id)"
        and _index_sql(conn, "review_records_artifact_revision_idx")
        == "CREATE INDEX review_records_artifact_revision_idx ON review_records(artifact_id, revision_id)"
        and _index_sql(conn, "review_record_events_review_id_created_event_idx")
        == "CREATE INDEX review_record_events_review_id_created_event_idx ON review_record_events(review_id, created_at, event_id)"
    )


def _ensure_review_tables_for_conn(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_records (
          review_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          revision_id TEXT NOT NULL,
          scope TEXT NOT NULL CHECK (scope IN ('set','shot')),
          shot_id TEXT,
          body TEXT NOT NULL,
          body_hash TEXT NOT NULL,
          blocking INTEGER NOT NULL CHECK (blocking IN (0,1)),
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          CHECK (
            (scope = 'set' AND shot_id IS NULL)
            OR
            (scope = 'shot' AND shot_id IS NOT NULL)
          ),
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS review_record_events (
          event_id TEXT PRIMARY KEY,
          review_id TEXT NOT NULL,
          %s,
          actor TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(review_id) REFERENCES review_records(review_id)
        )
        """
        % _review_event_check_sql()
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS review_records_revision_shot_idx "
        "ON review_records(revision_id, shot_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS review_records_artifact_revision_idx "
        "ON review_records(artifact_id, revision_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS review_record_events_review_id_created_event_idx "
        "ON review_record_events(review_id, created_at, event_id)"
    )


def _rebuild_approval_records_for_phase3(conn):
    current_sql = _table_sql(conn, "approval_records")
    has_actions = all(action in current_sql for action in APPROVAL_ACTIONS)
    existing_columns = _columns(conn, "approval_records")
    has_evidence = all(column in existing_columns for column in APPROVAL_EVIDENCE_COLUMNS)
    if has_actions and has_evidence:
        return
    conn.execute("ALTER TABLE approval_records RENAME TO approval_records_old")
    _create_approval_records_table(conn)
    select_values = [
        column if column in existing_columns else "'' AS %s" % column
        for column in APPROVAL_EVIDENCE_COLUMNS
    ]
    conn.execute(
        """
        INSERT INTO approval_records
        (sequence, record_id, revision_id, artifact_id, action, reviewer, note, created_at, %s)
        SELECT sequence, record_id, revision_id, artifact_id, action, reviewer, note, created_at, %s
        FROM approval_records_old
        ORDER BY sequence
        """
        % (", ".join(APPROVAL_EVIDENCE_COLUMNS), ", ".join(select_values))
    )
    conn.execute("DROP TABLE approval_records_old")


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _table_sql(conn, name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (name,),
    ).fetchone()
    return "" if row is None else row["sql"]


def _index_sql(conn, name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
        (name,),
    ).fetchone()
    return "" if row is None else row["sql"]


def _columns(conn, table_name):
    return {
        row["name"]
        for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
    }


def _check(status):
    return {"status": "OK" if status else "MISSING"}
