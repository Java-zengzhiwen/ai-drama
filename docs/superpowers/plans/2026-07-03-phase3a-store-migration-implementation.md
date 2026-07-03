# Phase 3A Store And Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the Phase 0-2 Runtime Store for Phase 3 Shot Prompt artifacts, outputs, reviews, approval evidence, and replay-safe legacy migration.

**Architecture:** Preserve the existing RuntimeStore as the schema authority. Add only Phase 3 persistence primitives in this plan; Canonical, Renderer, Service orchestration, CLI, Skill, and Verifier behavior remain outside Phase 3A.

**Tech Stack:** Python, SQLite, pytest, existing RuntimeStore and migration patterns.

---

Plan Status: IMPLEMENTATION_PLAN_PENDING_USER_REVIEW
Implementation: IMPLEMENTATION_NOT_AUTHORIZED
Phase 3B+: NOT_AUTHORIZED
Phase 4: PHASE4_NOT_AUTHORIZED

## Scope

Phase 3A is Store and migration only. It creates no Canonical parser, Renderer, Bundle helper, Service orchestration, CLI command, Skill package, verifier, report writer, platform adapter, generation action, or Phase 4 asset binding behavior.

Allowed implementation files:

- `ai_drama_runtime/store.py`
- `ai_drama_runtime/shot_prompt_migration.py`
- `tests/test_shot_prompt_store_migration.py`
- `tests/test_shot_prompt_review_records.py`
- `tests/shot_prompt_store_support.py`

Forbidden implementation files:

- `ai_drama_runtime/shot_prompt_canonical.py`
- `ai_drama_runtime/shot_prompt_renderer.py`
- `ai_drama_runtime/shot_prompt_bundle.py`
- `ai_drama_runtime/validators.py`
- `ai_drama_runtime/services.py`
- `ai_drama_runtime/cli.py`
- `ai_drama_runtime/manifest.py`
- `ai_drama_runtime/runtime.py`
- `ai_drama_runtime/request.py`
- `tools/verify_phase3_shot_prompt_canonical_foundation.py`
- any Skill package path
- any Phase 3 verifier path
- any `reports/` path

## Existing Repository Evidence

- `ai_drama_runtime/store.py:RuntimeStore.__init__(self, db_path, objects_root)`
- `ai_drama_runtime/store.py:RuntimeStore._init_schema(self)`
- `ai_drama_runtime/store.py:RuntimeStore._ensure_columns(self)`
- `ai_drama_runtime/store.py:RuntimeStore.ensure_artifact(self, artifact_id, artifact_type, project_id, chapter_id)`
- `ai_drama_runtime/store.py:RuntimeStore.create_run(self, **values)`
- `ai_drama_runtime/store.py:RuntimeStore.insert_revision(self, **values)`
- `ai_drama_runtime/store.py:RuntimeStore.insert_validation(self, **values)`
- `ai_drama_runtime/store.py:RuntimeStore.approval_record(self, record_id)`
- `ai_drama_runtime/store.py:RuntimeStore.latest_approval(self, revision_id)`
- `ai_drama_runtime/store.py:RuntimeStore.insert_revision_outputs_transaction(self, rows)`
- `ai_drama_runtime/store.py:RuntimeStore.revision_outputs(self, revision_id)`
- `ai_drama_runtime/store.py:RuntimeStore.get_revision_output(self, revision_id, logical_type)`
- `ai_drama_runtime/store.py:RuntimeStore.validation_results(self, revision_id)`
- `tests/test_storyboard_legacy_migration.py:_create_planning_baseline_legacy_db(db_path)`
- `tests/test_storyboard_legacy_migration.py:test_phase2_migration_replay_is_idempotent(tmp_path)`

## Frozen Phase 3A Store Contract

```python
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
REVIEW_EVENT_TYPES = ("opened", "resolved", "reopened", "voided")
```

All table rebuild helpers in Phase 3A are connection-local helpers. They use `conn.execute(...)` statements only and never open, commit, roll back, close, toggle foreign keys, or run script execution. The only transaction owner is `apply_phase3_store_migration(db_path)`.

## Task Dependency Map

| Task | Depends on | First symbols produced |
| --- | --- | --- |
| 1 | repository baseline | Store test support and schema snapshots |
| 2 | Task 1 | deterministic Phase 3A preview |
| 3 | Tasks 1-2 | artifact business key schema and Store APIs |
| 4 | Tasks 1-3 | expanded `revision_outputs` rebuild |
| 5 | Tasks 1-4 | `revisions.approval_status` rebuild |
| 6 | Tasks 1-5 | `approval_records.action` rebuild |
| 7 | Tasks 1-6 | approval record dataclass and row mapping |
| 8 | Tasks 1-7 | review table schema |
| 9 | Tasks 1-8 | atomic review creation and event APIs |
| 10 | Tasks 1-9 | latest validation query APIs |
| 11 | Tasks 1-10 | atomic Phase 3 output insertion primitive |
| 12 | Tasks 1-11 | migration orchestrator |
| 13 | Tasks 1-12 | fresh-vs-migrated schema parity |
| 14 | Tasks 1-13 | Phase 3A acceptance |

### Task 1: Store Test Support And Schema Snapshot

**Depends on:** repository baseline

**Files:**
- Create: `tests/shot_prompt_store_support.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_support_creates_phase2_legacy_database -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, normalized_schema_snapshot, snapshot_database, table_columns
from tests.test_storyboard_legacy_migration import _create_planning_baseline_legacy_db as create_real_phase2_legacy_db


def test_phase3a_support_creates_phase2_legacy_database(tmp_path):
    db_path = tmp_path / "runtime.db"
    real_db_path = tmp_path / "real-runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)
    create_real_phase2_legacy_db(real_db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    real_conn = sqlite3.connect(real_db_path)
    real_conn.row_factory = sqlite3.Row
    try:
        artifact_columns = set(table_columns(conn, "artifacts"))
        assert {
            "artifact_id",
            "artifact_type",
            "project_id",
            "chapter_id",
            "created_at",
        } <= artifact_columns
        assert "business_key_type" not in artifact_columns
        assert "business_key_value" not in artifact_columns
        snapshot = snapshot_database(conn)
        assert snapshot["tables"]["artifacts"]["row_count"] == 1
        assert snapshot["foreign_key_check"] == []
        assert snapshot["transient_tables"] == []
        assert normalized_schema_snapshot(conn) == normalized_schema_snapshot(real_conn)
    finally:
        conn.close()
        real_conn.close()

    with RuntimeStore(db_path, objects_root) as store:
        assert store.get_revision("legacy-revision").revision_id == "legacy-revision"
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_support_creates_phase2_legacy_database -q
```

Expected:

```text
FAIL because tests.shot_prompt_store_support is not defined
```

- [ ] **Step 3: Implement the minimal test support**

```python
def table_columns(conn, table_name):
    return {row["name"]: dict(row) for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()}


def index_sql(conn, table_name):
    return {
        row["name"]: row["sql"]
        for row in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'index' AND tbl_name = ? ORDER BY name",
            (table_name,),
        ).fetchall()
    }


def table_sql(conn, table_name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return "" if row is None else row["sql"]


def _normalized_sql_tokens(sql):
    return sorted(set(sql.replace("\n", " ").replace("(", " ( ").replace(")", " ) ").replace(",", " , ").split()))


def normalized_schema_snapshot(conn):
    table_names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    result = {}
    for name in table_names:
        result[name] = {
            "columns": [
                {
                    "name": row["name"],
                    "type": row["type"].upper(),
                    "notnull": row["notnull"],
                    "default": row["dflt_value"],
                    "pk": row["pk"],
                }
                for row in conn.execute("PRAGMA table_info(%s)" % name).fetchall()
            ],
            "foreign_keys": [dict(row) for row in conn.execute("PRAGMA foreign_key_list(%s)" % name).fetchall()],
            "indexes": index_sql(conn, name),
            "check_tokens": _normalized_sql_tokens(table_sql(conn, name)),
        }
    return result


def snapshot_database(conn):
    table_names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    tables = {}
    for name in table_names:
        tables[name] = {
            "columns": list(table_columns(conn, name)),
            "schema": normalized_schema_snapshot(conn).get(name, {}),
            "indexes": index_sql(conn, name),
            "row_count": conn.execute("SELECT COUNT(*) AS count FROM %s" % name).fetchone()["count"],
        }
    return {
        "tables": tables,
        "foreign_key_check": [dict(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()],
        "transient_tables": [name for name in table_names if name.endswith("_old") or name.endswith("_new")],
        "legacy_revision": dict(conn.execute("SELECT * FROM revisions WHERE revision_id = 'legacy-revision'").fetchone()),
    }


def create_phase2_legacy_db(db_path):
    from tests.test_storyboard_legacy_migration import _create_planning_baseline_legacy_db

    _create_planning_baseline_legacy_db(db_path)
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_support_creates_phase2_legacy_database -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py::test_phase2_migration_replay_is_idempotent -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/shot_prompt_store_support.py tests/test_shot_prompt_store_migration.py
git commit -m "test: add phase 3a store migration support"
```

### Task 2: Inventory And Preview

**Depends on:** Task 1

**Files:**
- Create: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_each_contract_check_without_mutation -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from ai_drama_runtime.shot_prompt_migration import preview_phase3_store_migration
from tests.shot_prompt_store_support import create_phase2_legacy_db, snapshot_database


def test_phase3_preview_reports_each_contract_check_without_mutation(tmp_path):
    db_path = tmp_path / "runtime.db"
    create_phase2_legacy_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    before = snapshot_database(conn)
    conn.close()

    preview = preview_phase3_store_migration(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    after = snapshot_database(conn)
    conn.close()

    assert before == after
    assert preview["status"] == "NEEDS_MIGRATION"
    assert preview["checks"]["artifact_business_key"]["status"] == "MISSING"
    assert preview["checks"]["revision_outputs_check"]["status"] == "MISSING"
    assert preview["checks"]["revision_status_check"]["status"] == "MISSING"
    assert preview["checks"]["approval_action_check"]["status"] == "MISSING"
    assert preview["checks"]["approval_evidence_columns"]["status"] == "MISSING"
    assert preview["checks"]["review_tables"]["status"] == "MISSING"
    assert preview["checks"]["review_indexes"]["status"] == "MISSING"
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_each_contract_check_without_mutation -q
```

Expected:

```text
FAIL because ai_drama_runtime.shot_prompt_migration is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
import sqlite3
from pathlib import Path


REVIEW_INDEX_SQL = {
    "review_records_revision_shot_idx": "CREATE INDEX review_records_revision_shot_idx ON review_records(revision_id, shot_id)",
    "review_records_artifact_revision_idx": "CREATE INDEX review_records_artifact_revision_idx ON review_records(artifact_id, revision_id)",
    "review_record_events_review_id_created_event_idx": "CREATE INDEX review_record_events_review_id_created_event_idx ON review_record_events(review_id, created_at, event_id)",
}


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _table_sql(conn, name):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)).fetchone()
    return "" if row is None else row["sql"]


def _index_sql(conn, name):
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?", (name,)).fetchone()
    return "" if row is None else row["sql"]


def _columns(conn, table_name):
    return {row["name"] for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()}


def _check(status):
    return {"status": "OK" if status else "MISSING"}


def preview_phase3_store_migration(db_path):
    conn = _connect(db_path)
    try:
        artifact_sql = _index_sql(conn, "one_shot_prompt_set_per_source_storyboard_revision")
        revision_output_sql = _table_sql(conn, "revision_outputs")
        revisions_sql = _table_sql(conn, "revisions")
        approval_sql = _table_sql(conn, "approval_records")
        review_sql = _table_sql(conn, "review_records")
        event_sql = _table_sql(conn, "review_record_events")
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
            "revision_status_check": _check(all(value in revisions_sql for value in REVISION_APPROVAL_STATUSES)),
            "approval_action_check": _check(all(value in approval_sql for value in APPROVAL_ACTIONS)),
            "approval_evidence_columns": _check(set(APPROVAL_EVIDENCE_COLUMNS) <= approval_columns),
            "review_tables": _check(
                "shot_id TEXT" in review_sql
                and "scope = 'set' AND shot_id IS NULL" in review_sql
                and all(value in event_sql for value in REVIEW_EVENT_TYPES)
            ),
            "review_indexes": _check(
                all(_index_sql(conn, name) == sql for name, sql in REVIEW_INDEX_SQL.items())
            ),
            "foreign_key_check": _check(conn.execute("PRAGMA foreign_key_check").fetchall() == []),
        }
        status = "CURRENT" if all(item["status"] == "OK" for item in checks.values()) else "NEEDS_MIGRATION"
        return {"status": status, "database_path": str(Path(db_path)), "checks": checks}
    finally:
        conn.close()
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_each_contract_check_without_mutation -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_support_creates_phase2_legacy_database -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add phase 3a store migration preview"
```

### Task 3: Artifact Business Key Schema And APIs

**Depends on:** Tasks 1-2

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_sql, table_columns


def test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        first = store.ensure_shot_prompt_artifact(
            project_id="project-1",
            chapter_id="chapter-1",
            source_storyboard_revision_id="storyboard-revision-1",
        )
        second = store.ensure_shot_prompt_artifact(
            project_id="project-1",
            chapter_id="chapter-1",
            source_storyboard_revision_id="storyboard-revision-1",
        )
        assert first["artifact_id"] == second["artifact_id"]
        assert first["artifact_id"] != "storyboard-revision-1"
        assert store.artifact_by_business_key(
            "shot_prompt_set",
            "source_storyboard_revision_id",
            "storyboard-revision-1",
        )["artifact_id"] == first["artifact_id"]
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO artifacts
                (artifact_id, artifact_type, project_id, chapter_id, business_key_type, business_key_value, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("dup", "shot_prompt_set", "project-1", "chapter-1", "source_storyboard_revision_id", "storyboard-revision-1", "2026-07-03T00:00:00Z"),
            )
        assert {"business_key_type", "business_key_value"} <= set(table_columns(store.conn, "artifacts"))
        assert "artifact_type = 'shot_prompt_set'" in index_sql(store.conn, "artifacts")["one_shot_prompt_set_per_source_storyboard_revision"]
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated -q
```

Expected:

```text
FAIL because RuntimeStore.ensure_shot_prompt_artifact is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _ensure_artifact_business_key_columns_for_conn(conn):
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(artifacts)").fetchall()}
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


def artifact_by_business_key(self, artifact_type, business_key_type, business_key_value):
    row = self.conn.execute(
        """
        SELECT * FROM artifacts
        WHERE artifact_type = ? AND business_key_type = ? AND business_key_value = ?
        ORDER BY created_at, artifact_id LIMIT 1
        """,
        (artifact_type, business_key_type, business_key_value),
    ).fetchone()
    return None if row is None else dict(row)


def ensure_shot_prompt_artifact(self, *, project_id, chapter_id, source_storyboard_revision_id):
    existing = self.artifact_by_business_key("shot_prompt_set", "source_storyboard_revision_id", source_storyboard_revision_id)
    if existing is not None:
        return existing
    artifact_id = uuid.uuid4().hex
    try:
        self.conn.execute(
            """
            INSERT INTO artifacts
            (artifact_id, artifact_type, project_id, chapter_id, business_key_type, business_key_value, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, "shot_prompt_set", project_id, chapter_id, "source_storyboard_revision_id", source_storyboard_revision_id, now_iso()),
        )
        self.conn.commit()
    except sqlite3.IntegrityError:
        self.conn.rollback()
    return self.artifact_by_business_key("shot_prompt_set", "source_storyboard_revision_id", source_storyboard_revision_id)
```

Wire `_ensure_artifact_business_key_columns_for_conn(self.conn)` into `RuntimeStore._ensure_columns(self)`. Use the same artifact columns and partial unique index in `RuntimeStore._init_schema(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py::test_phase2_migration_replay_is_idempotent tests/test_runtime_lifecycle.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py
git commit -m "feat: add shot prompt artifact business keys"
```

### Task 4: Revision Outputs Rebuild

**Depends on:** Tasks 1-3

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_exact_logical_types_and_preserve_schema -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_sql, table_sql


def test_revision_outputs_accept_exact_logical_types_and_preserve_schema(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        object_id = store.write_text_object("{}")
        revision = store.get_revision("legacy-revision")
        rows = [
            {
                "revision_id": revision.revision_id,
                "logical_type": logical_type,
                "object_id": object_id,
                "content_hash": object_id,
                "media_type": "application/json",
                "generator": "test",
                "generator_version": "1.0.0",
            }
            for logical_type in PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
        ]
        inserted = store.insert_revision_outputs_transaction(rows)
        assert [item.logical_type for item in inserted] == list(PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES)
        with pytest.raises(sqlite3.IntegrityError):
            store.insert_revision_outputs_transaction([dict(rows[0], logical_type="unknown")])
        sql = table_sql(store.conn, "revision_outputs")
        for logical_type in REVISION_OUTPUT_LOGICAL_TYPES:
            assert logical_type in sql
        indexes = index_sql(store.conn, "revision_outputs")
        assert "revision_outputs_content_hash_idx" in indexes
        assert "revision_outputs_object_id_idx" in indexes
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_exact_logical_types_and_preserve_schema -q
```

Expected:

```text
FAIL because the current revision_outputs CHECK rejects Phase 3 logical types
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _quoted(values):
    return ", ".join("'%s'" % value for value in values)


def _revision_output_check_sql():
    return "logical_type TEXT NOT NULL CHECK (logical_type IN (%s))" % _quoted(REVISION_OUTPUT_LOGICAL_TYPES)


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
    if all(value in current_sql for value in REVISION_OUTPUT_LOGICAL_TYPES):
        return
    conn.execute("ALTER TABLE revision_outputs RENAME TO revision_outputs_old")
    _create_revision_outputs_table(conn)
    conn.execute(
        """
        INSERT INTO revision_outputs
        (revision_output_id, revision_id, logical_type, object_id, content_hash, media_type, generator, generator_version, created_at)
        SELECT revision_output_id, revision_id, logical_type, object_id, content_hash, media_type, generator, generator_version, created_at
        FROM revision_outputs_old
        ORDER BY created_at, revision_output_id
        """
    )
    conn.execute("DROP TABLE revision_outputs_old")
    conn.execute("CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx ON revision_outputs(content_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx ON revision_outputs(object_id)")
```

Use `_create_revision_outputs_table(self.conn)` in `RuntimeStore._init_schema(self)` and `_rebuild_revision_outputs_for_phase3(self.conn)` in `_ensure_columns(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_exact_logical_types_and_preserve_schema -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py::test_revision_outputs_public_api_is_append_only -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py
git commit -m "feat: extend revision output logical types"
```

### Task 5: Revision Status Rebuild

**Depends on:** Tasks 1-4

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_preserves_schema_and_approved_index -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_sql, table_sql


def test_revision_status_check_preserves_schema_and_approved_index(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        for status in REVISION_APPROVAL_STATUSES:
            store.conn.execute("UPDATE revisions SET approval_status = ? WHERE revision_id = ?", (status, "legacy-revision"))
            store.conn.commit()
            assert store.get_revision("legacy-revision").approval_status == status
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute("UPDATE revisions SET approval_status = 'unknown' WHERE revision_id = 'legacy-revision'")
        sql = table_sql(store.conn, "revisions")
        assert "approval_status TEXT NOT NULL CHECK" in sql
        assert "FOREIGN KEY(run_id) REFERENCES runs(run_id)" in sql
        approved_index = index_sql(store.conn, "revisions")["one_current_approved_revision"]
        assert "WHERE approval_status = 'approved'" in approved_index
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_preserves_schema_and_approved_index -q
```

Expected:

```text
FAIL because revisions.approval_status has no CHECK
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _revision_status_check_sql():
    return "approval_status TEXT NOT NULL CHECK (approval_status IN (%s))" % _quoted(REVISION_APPROVAL_STATUSES)


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
    if all(value in current_sql for value in REVISION_APPROVAL_STATUSES) and "approval_status TEXT NOT NULL CHECK" in current_sql:
        return
    conn.execute("DROP INDEX IF EXISTS one_current_approved_revision")
    conn.execute("ALTER TABLE revisions RENAME TO revisions_old")
    _create_revisions_table(conn)
    conn.execute(
        """
        INSERT INTO revisions
        (revision_id, artifact_id, artifact_type, project_id, chapter_id, run_id, skill_id, skill_version,
         skill_package_hash, runtime_provider, runtime_model, number, content_object_id, content_hash,
         raw_response_object_id, parser_version, content_profile, derivation_type, supersedes_revision_id,
         approval_status, created_at)
        SELECT revision_id, artifact_id, artifact_type, project_id, chapter_id, run_id, skill_id, skill_version,
               skill_package_hash, runtime_provider, runtime_model, number, content_object_id, content_hash,
               raw_response_object_id, parser_version, content_profile, derivation_type, supersedes_revision_id,
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
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_preserves_schema_and_approved_index -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_runtime_lifecycle.py tests/test_approval_ordering_resources.py::test_latest_approval_order_is_deterministic_after_restart -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py
git commit -m "feat: add phase 3 revision statuses"
```

### Task 6: Approval Action Rebuild

**Depends on:** Tasks 1-5

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_actions_accept_old_and_phase3_values_only -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_sql


def test_approval_actions_accept_old_and_phase3_values_only(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        for action in APPROVAL_ACTIONS:
            store.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("record-" + action, "legacy-revision", "artifact-1", action, "tester", "", "2026-07-03T00:00:00Z"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO approval_records
                (record_id, revision_id, artifact_id, action, reviewer, note, created_at)
                VALUES ('bad', 'legacy-revision', 'artifact-1', 'unknown', 'tester', '', '2026-07-03T00:00:00Z')
                """
            )
        assert "shot_prompt_approval_revoked" in table_sql(store.conn, "approval_records")
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_actions_accept_old_and_phase3_values_only -q
```

Expected:

```text
FAIL because approval_records.action has no CHECK for Phase 3 actions
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _approval_action_check_sql():
    return "action TEXT NOT NULL CHECK (action IN (%s))" % _quoted(APPROVAL_ACTIONS)


def _create_approval_records_table(conn):
    evidence_sql = ", ".join("%s TEXT NOT NULL DEFAULT ''" % name for name in APPROVAL_EVIDENCE_COLUMNS)
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
        % (_approval_action_check_sql(), evidence_sql)
    )


def _rebuild_approval_records_for_phase3(conn):
    current_sql = _table_sql(conn, "approval_records")
    has_actions = all(action in current_sql for action in APPROVAL_ACTIONS)
    has_evidence = all(column in _columns(conn, "approval_records") for column in APPROVAL_EVIDENCE_COLUMNS)
    if has_actions and has_evidence:
        return
    existing_columns = _columns(conn, "approval_records")
    conn.execute("ALTER TABLE approval_records RENAME TO approval_records_old")
    _create_approval_records_table(conn)
    select_values = []
    for column in APPROVAL_EVIDENCE_COLUMNS:
        select_values.append(column if column in existing_columns else "'' AS %s" % column)
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
```

Use `_create_approval_records_table(self.conn)` in `RuntimeStore._init_schema(self)` and `_rebuild_approval_records_for_phase3(self.conn)` in `_ensure_columns(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_actions_accept_old_and_phase3_values_only -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_validators_approval_export.py::test_validator_statuses_and_required_approval_block tests/test_approval_ordering_resources.py::test_latest_approval_order_is_deterministic_after_restart -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py
git commit -m "feat: extend approval action storage"
```

### Task 7: ApprovalRecord Mapping APIs

**Depends on:** Tasks 1-6

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_map_exact_evidence_columns_with_defaults -q`

- [ ] **Step 1: Write the failing test**

```python
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_columns


def test_approval_records_map_exact_evidence_columns_with_defaults(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        columns = table_columns(store.conn, "approval_records")
        for name in APPROVAL_EVIDENCE_COLUMNS:
            assert columns[name]["dflt_value"] == "''"
        assert set(APPROVAL_EVIDENCE_COLUMNS) == {
            "source_storyboard_revision_id",
            "canonical_content_hash",
            "bundle_manifest_hash",
            "qualification_report_hash",
            "qualification_report_object_id",
            "renderer_profile_id",
            "renderer_profile_version",
            "qualification_profile_id",
            "qualification_profile_version",
        }
        revision = store.get_revision("legacy-revision")
        approval = store.approve_in_transaction(revision, "tester", "legacy approval")
        assert approval.source_storyboard_revision_id == ""
        assert approval.canonical_content_hash == ""
        assert approval.renderer_profile_id == ""
        assert approval.qualification_profile_version == ""
        store.conn.execute(
            """
            INSERT INTO approval_records
            (record_id, revision_id, artifact_id, action, reviewer, note, created_at,
             source_storyboard_revision_id, canonical_content_hash, bundle_manifest_hash,
             qualification_report_hash, qualification_report_object_id, renderer_profile_id,
             renderer_profile_version, qualification_profile_id, qualification_profile_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "shot-prompt-record",
                "legacy-revision",
                "artifact-1",
                "shot_prompt_approved",
                "reviewer",
                "",
                "2026-07-03T00:00:00Z",
                "storyboard-revision",
                "canonical-hash",
                "bundle-hash",
                "qualification-hash",
                "qualification-object",
                "shot_prompt_standard",
                "1.0.0",
                "shot_prompt_approval_qualification",
                "1.0.0",
            ),
        )
        mapped = store.approval_record("shot-prompt-record")
        assert mapped.action == "shot_prompt_approved"
        assert mapped.source_storyboard_revision_id == "storyboard-revision"
        assert mapped.canonical_content_hash == "canonical-hash"
        assert mapped.renderer_profile_id == "shot_prompt_standard"
        assert store.latest_approval("legacy-revision").record_id == "shot-prompt-record"
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_map_exact_evidence_columns_with_defaults -q
```

Expected:

```text
FAIL because ApprovalRecord row mapping lacks the exact Phase 3 approval evidence fields
```

- [ ] **Step 3: Implement the minimal production change**

```python
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

def _approval_from_row(self, row):
    return None if row is None else ApprovalRecord(**dict(row))
```

Task 6 owns approval table schema for both fresh and legacy databases. Task 7 only updates `ApprovalRecord` and `_approval_from_row(self, row)` so `approval_record()`, `latest_approval()`, and existing script/storyboard approval flows can read the nine evidence fields with empty-string defaults.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_map_exact_evidence_columns_with_defaults -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_validators_approval_export.py::test_validator_statuses_and_required_approval_block tests/test_approval_ordering_resources.py::test_latest_approval_order_is_deterministic_after_restart -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py
git commit -m "feat: map shot prompt approval evidence"
```

### Task 8: Review Table Schema

**Depends on:** Tasks 1-7

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_tables_enforce_scope_events_and_indexes -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_sql, table_sql


def test_review_tables_enforce_scope_events_and_indexes(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        set_review_id = "review-set"
        shot_review_id = "review-shot"
        store.conn.execute(
            """
            INSERT INTO review_records
            (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
            VALUES (?, 'artifact-1', 'legacy-revision', 'set', NULL, 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
            """,
            (set_review_id,),
        )
        store.conn.execute(
            """
            INSERT INTO review_records
            (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
            VALUES (?, 'artifact-1', 'legacy-revision', 'shot', 'SHOT_001', 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
            """,
            (shot_review_id,),
        )
        for event_type in REVIEW_EVENT_TYPES:
            store.conn.execute(
                """
                INSERT INTO review_record_events
                (event_id, review_id, event_type, actor, note, created_at)
                VALUES (?, ?, ?, 'tester', '', '2026-07-03T00:00:00Z')
                """,
                ("event-" + event_type, shot_review_id, event_type),
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_records
                (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
                VALUES ('bad-set', 'artifact-1', 'legacy-revision', 'set', 'SHOT_001', 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_records
                (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
                VALUES ('bad-shot', 'artifact-1', 'legacy-revision', 'shot', NULL, 'body', 'hash', 1, 'tester', '2026-07-03T00:00:00Z')
                """
            )
        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                """
                INSERT INTO review_record_events
                (event_id, review_id, event_type, actor, note, created_at)
                VALUES ('bad-event', 'review-shot', 'note_added', 'tester', '', '2026-07-03T00:00:00Z')
                """
            )
        assert "scope = 'set' AND shot_id IS NULL" in table_sql(store.conn, "review_records")
        indexes = index_sql(store.conn, "review_records")
        assert "review_records_revision_shot_idx" in indexes
        assert "review_records_artifact_revision_idx" in indexes
        event_indexes = index_sql(store.conn, "review_record_events")
        assert "review_record_events_review_id_created_event_idx" in event_indexes
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_tables_enforce_scope_events_and_indexes -q
```

Expected:

```text
FAIL because review_records and review_record_events do not exist
```

- [ ] **Step 3: Implement the minimal production change**

```python
@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    artifact_id: str
    revision_id: str
    scope: str
    shot_id: str | None
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
          event_type TEXT NOT NULL CHECK (event_type IN ('opened','resolved','reopened','voided')),
          actor TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(review_id) REFERENCES review_records(review_id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS review_records_revision_shot_idx ON review_records(revision_id, shot_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS review_records_artifact_revision_idx ON review_records(artifact_id, revision_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS review_record_events_review_id_created_event_idx ON review_record_events(review_id, created_at, event_id)")
```

Call `_ensure_review_tables_for_conn(self.conn)` from both `RuntimeStore._init_schema(self)` and `_ensure_columns(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_tables_enforce_scope_events_and_indexes -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py::test_phase2_migration_replay_is_idempotent tests/test_approval_ordering_resources.py::test_store_closes_database_so_file_can_be_removed -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_review_records.py ai_drama_runtime/store.py
git commit -m "feat: add shot prompt review table schema"
```

### Task 9: Atomic Review Creation And Events

**Depends on:** Tasks 1-8

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_record_creation_always_creates_opened_event_atomically -q`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db


def test_review_record_creation_always_creates_opened_event_atomically(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        review = store.insert_review_record_with_opened_event(
            artifact_id="artifact-1",
            revision_id="legacy-revision",
            scope="set",
            shot_id=None,
            body="Set-level issue",
            blocking=True,
            created_by="reviewer-a",
            note="opened",
        )
        assert review.body_hash
        assert store.review_status(review.review_id) == "opened"
        assert store.open_blocking_review_count("legacy-revision") == 1
        store.insert_review_event(review_id=review.review_id, event_type="voided", actor="reviewer-a", note="")
        assert store.open_blocking_review_count("legacy-revision") == 0
        store.insert_review_event(review_id=review.review_id, event_type="reopened", actor="reviewer-a", note="")
        assert store.open_blocking_review_count("legacy-revision") == 1
        store.insert_review_event(review_id=review.review_id, event_type="resolved", actor="reviewer-b", note="")
        assert store.open_blocking_review_count("legacy-revision") == 0


def test_review_record_creation_rolls_back_when_opened_event_fails(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        def fail_event_insert(**_values):
            raise RuntimeError("forced opened event insert failure")

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(store, "_insert_review_event_row", fail_event_insert)
        with pytest.raises(RuntimeError):
            store.insert_review_record_with_opened_event(
                artifact_id="artifact-1",
                revision_id="legacy-revision",
                scope="set",
                shot_id=None,
                body="Set-level issue",
                blocking=True,
                created_by="reviewer-a",
                note="opened",
            )
        monkeypatch.undo()
        assert store.conn.execute("SELECT COUNT(*) AS count FROM review_records").fetchone()["count"] == 0
        assert store.conn.execute("SELECT COUNT(*) AS count FROM review_record_events").fetchone()["count"] == 0


def test_review_status_uses_event_id_as_same_timestamp_tie_breaker(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        review = store.insert_review_record_with_opened_event(
            artifact_id="artifact-1",
            revision_id="legacy-revision",
            scope="shot",
            shot_id="SHOT_001",
            body="Shot-level issue",
            blocking=True,
            created_by="reviewer-a",
            note="opened",
        )
        with store.conn:
            store._insert_review_event_row(
                review_id=review.review_id,
                event_type="resolved",
                actor="reviewer-a",
                note="",
                event_id="event-a",
                created_at="2026-07-03T00:00:00.000000Z",
            )
            store._insert_review_event_row(
                review_id=review.review_id,
                event_type="reopened",
                actor="reviewer-b",
                note="",
                event_id="event-b",
                created_at="2026-07-03T00:00:00.000000Z",
            )
        assert store.review_status(review.review_id) == "reopened"
        assert store.open_blocking_review_count("legacy-revision") == 1
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_record_creation_always_creates_opened_event_atomically tests/test_shot_prompt_review_records.py::test_review_record_creation_rolls_back_when_opened_event_fails tests/test_shot_prompt_review_records.py::test_review_status_uses_event_id_as_same_timestamp_tie_breaker -q
```

Expected:

```text
FAIL because RuntimeStore.insert_review_record_with_opened_event is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
def _review_from_row(self, row):
    if row is None:
        return None
    data = dict(row)
    data["blocking"] = bool(data["blocking"])
    return ReviewRecord(**data)


def _review_event_from_row(self, row):
    return None if row is None else ReviewEventRecord(**dict(row))


def review_record(self, review_id):
    return self._review_from_row(
        self.conn.execute("SELECT * FROM review_records WHERE review_id = ?", (review_id,)).fetchone()
    )


def review_event(self, event_id):
    return self._review_event_from_row(
        self.conn.execute("SELECT * FROM review_record_events WHERE event_id = ?", (event_id,)).fetchone()
    )


def review_events(self, review_id):
    rows = self.conn.execute(
        "SELECT * FROM review_record_events WHERE review_id = ? ORDER BY created_at, event_id",
        (review_id,),
    ).fetchall()
    return [self._review_event_from_row(row) for row in rows]


def _insert_review_event_row(self, *, review_id, event_type, actor, note="", event_id=None, created_at=None):
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
        return self._insert_review_event_row(review_id=review_id, event_type=event_type, actor=actor, note=note)


def _insert_review_record_row(self, *, review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at):
    self.conn.execute(
        """
        INSERT INTO review_records
        (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, int(blocking), created_by, created_at),
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
    return sum(1 for row in rows if self.review_status(row["review_id"]) not in {"resolved", "voided"})
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_record_creation_always_creates_opened_event_atomically tests/test_shot_prompt_review_records.py::test_review_record_creation_rolls_back_when_opened_event_fails tests/test_shot_prompt_review_records.py::test_review_status_uses_event_id_as_same_timestamp_tie_breaker -q
```

Expected:

```text
3 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py::test_review_tables_enforce_scope_events_and_indexes -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_review_records.py ai_drama_runtime/store.py
git commit -m "feat: add atomic shot prompt review creation"
```

### Task 10: Latest Validation Query APIs

**Depends on:** Tasks 1-9

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_latest_validation_queries_are_deterministic -q`

- [ ] **Step 1: Write the failing test**

```python
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db


def test_latest_validation_queries_are_deterministic(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        empty = store.write_text_object("")
        report = store.write_text_object("{}")
        store.insert_validation(
            revision_id="legacy-revision",
            validator_id="shot_prompt_schema",
            validator_name="schema",
            status="FAIL",
            required=1,
            exit_code=1,
            error_code="ERR",
            duration_ms=1,
            stdout_object_id=empty,
            stderr_object_id=empty,
            report_object_id=report,
            created_at="2026-07-03T00:00:00.000000Z",
        )
        store.insert_validation(
            revision_id="legacy-revision",
            validator_id="shot_prompt_schema",
            validator_name="schema",
            status="PASS",
            required=1,
            exit_code=0,
            error_code="",
            duration_ms=1,
            stdout_object_id=empty,
            stderr_object_id=empty,
            report_object_id=report,
            created_at="2026-07-03T00:00:01.000000Z",
        )
        assert store.latest_validation_result("legacy-revision", "shot_prompt_schema").status == "PASS"
        assert store.latest_validation_results("legacy-revision")["shot_prompt_schema"].status == "PASS"
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_latest_validation_queries_are_deterministic -q
```

Expected:

```text
FAIL because RuntimeStore.latest_validation_result is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
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
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_latest_validation_queries_are_deterministic -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_validators_approval_export.py::test_required_failed_validator_blocks_approval -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py
git commit -m "feat: add latest validation store queries"
```

### Task 11: Atomic Phase 3 Output Insertion Primitive

**Depends on:** Tasks 1-10

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_output_insert_validates_inputs_and_rolls_back_new_rows -q`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db


def _phase3_rows(store, revision_id):
    object_id = store.write_text_object("{}")
    return [
        {
            "revision_id": revision_id,
            "logical_type": logical_type,
            "object_id": object_id,
            "content_hash": object_id,
            "media_type": "application/json",
            "generator": "shot-prompt-test",
            "generator_version": "1.0.0",
        }
        for logical_type in PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES
    ]


def test_phase3_output_insert_validates_inputs_and_rolls_back_new_rows(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        rows = _phase3_rows(store, "legacy-revision")
        unordered_rows = [rows[3], rows[0], rows[6], rows[2], rows[4], rows[1], rows[5]]
        with pytest.raises(ValueError):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", rows[:-1])
        with pytest.raises(ValueError):
            store.insert_phase3_revision_outputs_atomically("missing-revision", rows)
        bad_rows = list(rows)
        bad_rows[3] = dict(bad_rows[3], logical_type="unknown")
        with pytest.raises(Exception):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", bad_rows)
        assert store.revision_outputs("legacy-revision") == []
        inserted = store.insert_phase3_revision_outputs_atomically("legacy-revision", unordered_rows)
        assert [item.logical_type for item in inserted] == list(PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES)
        with pytest.raises(Exception):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", rows)
        assert len(store.revision_outputs("legacy-revision")) == 7


def test_phase3_output_insert_rolls_back_when_row_helper_fails(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        rows = _phase3_rows(store, "legacy-revision")
        original = store._insert_revision_output_rows_no_commit

        def fail_after_one_row(items):
            original(items[:1])
            raise RuntimeError("forced row insert failure")

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(store, "_insert_revision_output_rows_no_commit", fail_after_one_row)
        with pytest.raises(RuntimeError):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", rows)
        monkeypatch.undo()
        assert store.revision_outputs("legacy-revision") == []
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_output_insert_validates_inputs_and_rolls_back_new_rows tests/test_shot_prompt_store_migration.py::test_phase3_output_insert_rolls_back_when_row_helper_fails -q
```

Expected:

```text
FAIL because RuntimeStore.insert_phase3_revision_outputs_atomically is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
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
    ordered_rows = sorted(rows, key=lambda row: PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES.index(row["logical_type"]))
    with self.conn:
        return self._insert_revision_output_rows_no_commit(ordered_rows)


def _insert_revision_output_rows_no_commit(self, rows):
    return self.insert_revision_outputs_transaction(rows)
```

`RuntimeStore.insert_revision_outputs_transaction(self, rows)` in the current repository inserts rows and returns records without calling `commit()` and without opening a transaction context. Phase 3A keeps that method as a no-commit row helper and makes `insert_phase3_revision_outputs_atomically()` the only transaction owner for this primitive. It accepts unordered input, validates exact set/no duplicates/same revision/revision exists, sorts rows internally by `PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES`, and never deletes or overwrites existing rows.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_output_insert_validates_inputs_and_rolls_back_new_rows tests/test_shot_prompt_store_migration.py::test_phase3_output_insert_rolls_back_when_row_helper_fails -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py::test_revision_outputs_public_api_is_append_only -q
```

Expected:

```text
1 passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py ai_drama_runtime/store.py
git commit -m "feat: add atomic shot prompt output insertion"
```

### Task 12: Migration Orchestrator

**Depends on:** Tasks 1-11

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_transactional -q`

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

import ai_drama_runtime.shot_prompt_migration as shot_prompt_migration
from ai_drama_runtime.shot_prompt_migration import Phase3StoreMigrationError, apply_phase3_store_migration, preview_phase3_store_migration
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, snapshot_database


def test_apply_phase3_store_migration_is_idempotent_and_transactional(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    first = apply_phase3_store_migration(db_path)
    second = apply_phase3_store_migration(db_path)

    assert first["status"] == "APPLIED"
    assert second["status"] == "ALREADY_CURRENT"
    preview = preview_phase3_store_migration(db_path)
    assert preview["status"] == "CURRENT"

    with RuntimeStore(db_path, objects_root) as store:
        runtime_store_fk_enabled = bool(store.conn.execute("PRAGMA foreign_keys").fetchone()[0])
        assert runtime_store_fk_enabled
        assert store.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        snapshot = snapshot_database(store.conn)
        assert snapshot["transient_tables"] == []
        assert snapshot["legacy_revision"]["revision_id"] == "legacy-revision"


def test_apply_phase3_store_migration_rolls_back_to_logical_snapshot(tmp_path, monkeypatch):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    before = snapshot_database(conn)
    conn.close()

    original = shot_prompt_migration._rebuild_approval_records_for_phase3

    def fail_after_approval_actions(conn):
        original(conn)
        raise RuntimeError("injected migration failure")

    monkeypatch.setattr(
        shot_prompt_migration,
        "_rebuild_approval_records_for_phase3",
        fail_after_approval_actions,
    )
    with pytest.raises(Phase3StoreMigrationError):
        apply_phase3_store_migration(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        after = snapshot_database(conn)
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    assert after == before

    with RuntimeStore(db_path, objects_root) as store:
        assert bool(store.conn.execute("PRAGMA foreign_keys").fetchone()[0])
        assert store.conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert snapshot_database(store.conn)["transient_tables"] == []
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_transactional tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_rolls_back_to_logical_snapshot -q
```

Expected:

```text
FAIL because apply_phase3_store_migration is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
class Phase3StoreMigrationError(RuntimeError):
    pass


def _migration_is_current(db_path):
    return preview_phase3_store_migration(db_path)["status"] == "CURRENT"


def apply_phase3_store_migration(db_path):
    db_path = Path(db_path)
    if _migration_is_current(db_path):
        return {"status": "ALREADY_CURRENT", "database_path": str(db_path)}
    conn = _connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("BEGIN IMMEDIATE")
        try:
            _ensure_artifact_business_key_columns_for_conn(conn)
            _rebuild_revisions_for_phase3(conn)
            _rebuild_revision_outputs_for_phase3(conn)
            _rebuild_approval_records_for_phase3(conn)
            _ensure_approval_evidence_columns_for_conn(conn)
            _ensure_review_tables_for_conn(conn)
            failures = conn.execute("PRAGMA foreign_key_check").fetchall()
            if failures:
                raise Phase3StoreMigrationError("foreign key check failed")
            conn.commit()
        except Exception as exc:
            conn.rollback()
            transient = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND (name LIKE '%_old' OR name LIKE '%_new')"
            ).fetchall()
            if transient:
                raise Phase3StoreMigrationError("rollback left transient migration tables")
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
    "approval_actions",
    "approval_evidence",
    "review_tables",
    "foreign_key_check",
)
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_transactional tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_rolls_back_to_logical_snapshot -q
```

Expected:

```text
2 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py tests/test_approval_ordering_resources.py::test_store_closes_database_so_file_can_be_removed -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add replay-safe phase 3 store migration"
```

### Task 13: Fresh-Vs-Migrated Schema Parity

**Depends on:** Tasks 1-12

**Files:**
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_fresh_runtime_store_schema_matches_migrated_legacy_schema -q`

- [ ] **Step 1: Write the failing parity test**

```python
import sqlite3

from ai_drama_runtime.shot_prompt_migration import apply_phase3_store_migration
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, normalized_schema_snapshot


def test_fresh_runtime_store_schema_matches_migrated_legacy_schema(tmp_path):
    fresh_db = tmp_path / "fresh.db"
    legacy_db = tmp_path / "legacy.db"
    create_phase2_legacy_db(legacy_db)

    with RuntimeStore(fresh_db, tmp_path / "fresh-objects") as fresh_store:
        fresh_schema = normalized_schema_snapshot(fresh_store.conn)

    apply_phase3_store_migration(legacy_db)
    conn = sqlite3.connect(legacy_db)
    conn.row_factory = sqlite3.Row
    try:
        migrated_legacy_schema = normalized_schema_snapshot(conn)
    finally:
        conn.close()

    assert fresh_schema == migrated_legacy_schema
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_fresh_runtime_store_schema_matches_migrated_legacy_schema -q
```

Expected:

```text
PASS because Tasks 3-8 already wire the same schema helpers into fresh DB creation and legacy migration
```

- [ ] **Step 3: Confirm no production change is required**

No production change. This task is an acceptance-only test task.

```bash
git diff --name-only -- ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py
```

Expected:

```text
no output
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_fresh_runtime_store_schema_matches_migrated_legacy_schema -q
```

Expected:

```text
1 passed
```

- [ ] **Step 5: Run related regressions**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py
git commit -m "test: verify fresh and migrated phase 3a schema parity"
```

### Task 14: Phase 3A Acceptance

**Depends on:** Tasks 1-13

**Files:**
- Test: `tests/test_shot_prompt_store_migration.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py -q`

- [ ] **Step 1: Write the scope guard test**

```python
from pathlib import Path


def test_phase3a_scope_does_not_create_later_phase_files():
    repo_root = Path(__file__).resolve().parents[1]
    forbidden = [
        "ai_drama_runtime/shot_prompt_canonical.py",
        "ai_drama_runtime/shot_prompt_renderer.py",
        "ai_drama_runtime/shot_prompt_bundle.py",
        "skills/ai-drama-shot-prompt-canonical-skill/v0.1.0/skill.json",
        "tools/verify_phase3_shot_prompt_canonical_foundation.py",
    ]
    assert [path for path in forbidden if (repo_root / path).exists()] == []
```

- [ ] **Step 2: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_scope_does_not_create_later_phase_files -q
```

Expected:

```text
1 passed
```

- [ ] **Step 3: Run Phase 3A focused tests**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 4: Run Phase 0-2 Store regressions**

```bash
python3 -m pytest tests/test_storyboard_legacy_migration.py tests/test_runtime_lifecycle.py tests/test_validators_approval_export.py tests/test_approval_ordering_resources.py -q
```

Expected:

```text
all selected tests passed
```

- [ ] **Step 5: Run full test suite**

```bash
python3 -m pytest -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py
git commit -m "test: cover phase 3a store migration acceptance"
```

## Semantic Contract Coverage

- A01: Task 1 checks real `artifacts` columns and absence of business-key columns in the legacy DB.
- A02: Task 7 uses exactly nine approved approval evidence columns.
- A03: Task 6 rebuilds approval action storage for legacy and Shot Prompt actions.
- A04: Task 8 freezes Review DDL, event enum, conditional scope check, and exact indexes.
- A05: Task 9 creates review records with an `opened` event atomically.
- A06: Task 9 provides complete Store methods called by tests.
- A07: Table rebuild helpers use `conn.execute(...)` statements and do not own transactions.
- A08: Task 12 owns foreign-key toggle and transaction boundaries.
- A09: Task 12 compares deterministic logical snapshots for rollback.
- A10: Task 2 preview checks every Phase 3A schema contract and Task 12 uses preview for current detection.
- A11: Task 13 proves fresh and migrated schema parity.
- A12: Task 4 preserves revision output columns, FK, uniqueness, indexes, old types, and Phase 3 types.
- A13: Task 5 preserves revisions columns, run FK, and approved partial unique index.
- A14: Task 11 freezes the Store primitive boundary and leaves bundle outcome classification to Phase 3C.
- A15: The audit gate includes semantic contract checks in addition to symbol checks.

## Mechanical And Semantic Audit Gate

The Phase 3A plan must pass a mechanical and semantic audit before review handoff. The audit report for this planning revision is generated outside the repository under `/tmp/phase3a-plan-audit/`.

Required zero-count checks:

```text
future_dependencies = 0
undefined_plan_symbols = 0
repository_signature_mismatches = 0
syntax_or_definition_order = 0
task_local_failures = 0
schema_drift = 0
migration_contract_failures = 0
semantic_contract_failures = 0
```

The audit must classify Python builtins, imported library symbols, attribute methods, `pytest` APIs, SQLite cursor APIs, and string methods as non-plan symbols. It must also check exact approval evidence fields, review event enum, approval action enum, absence of script execution in migration helpers, semantic test assertions, and fresh-vs-migrated schema parity coverage.

## Verification

Planning-time verification before committing this document:

```bash
python3 /tmp/phase3a-plan-audit/audit_phase3a_plan.py
git diff --check
git diff --cached --check
python3 -m pytest -q
```

Run the revision-prompt semantic scans from the shell before staging, so the scan patterns do not appear in this plan and cannot self-match.

Expected final planning state:

```text
Program Status: SPLIT_PLAN_PROGRAM_PENDING_USER_REVIEW
Phase 3A: IMPLEMENTATION_PLAN_PENDING_USER_REVIEW
Phase 3B-3E: PLANNING_NOT_STARTED
Implementation: IMPLEMENTATION_NOT_AUTHORIZED
Phase 4: PHASE4_NOT_AUTHORIZED
```
