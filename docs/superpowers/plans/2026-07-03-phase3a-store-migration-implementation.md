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
- `ai_drama_runtime/storyboard_migration.py:legacy_markdown_to_canonical(markdown, *, source_revision, source_artifact_id, source_content_hash)`
- `ai_drama_runtime/storyboard_migration.py:write_migration_preview(candidate, output_dir)`
- `tests/test_storyboard_legacy_migration.py:_create_planning_baseline_legacy_db(db_path)`
- `tests/test_storyboard_legacy_migration.py:test_phase2_migration_replay_is_idempotent(tmp_path)`
- `tools/verify_phase2_minimal_bundle_foundation.py:final_checks(execution_start_commit: str = EXECUTION_START_COMMIT)`

## Store Contract

Phase 3A freezes these Store-level constants:

```python
SHOT_PROMPT_ARTIFACT_TYPE = "shot_prompt_set"
SHOT_PROMPT_BUSINESS_KEY_TYPE = "source_storyboard_revision_id"
SHOT_PROMPT_REVISION_STATUSES = ("pending", "approved", "rejected", "superseded", "revoked")
SHOT_PROMPT_LOGICAL_TYPES = (
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)
```

Phase 3A adds storage for these concepts and no higher-layer behavior:

- artifact business key columns and partial unique index;
- expanded `revision_outputs.logical_type` CHECK;
- revision approval status CHECK compatible with existing statuses;
- approval evidence columns with safe empty-string defaults;
- `review_records` and `review_record_events`;
- latest validation query helpers;
- one atomic Phase 3 output insertion primitive;
- deterministic inventory, preview, apply, replay, rollback, and `PRAGMA foreign_key_check`.

## Task Dependency Map

| Task | Depends on | First symbols produced |
| --- | --- | --- |
| 1 | repository baseline | `tests/shot_prompt_store_support.py` helpers |
| 2 | Task 1 | `preview_phase3_store_migration` |
| 3 | Tasks 1-2 | artifact business key schema and Store APIs |
| 4 | Tasks 1-3 | expanded `revision_outputs` rebuild |
| 5 | Tasks 1-4 | revision status rebuild |
| 6 | Tasks 1-5 | approval evidence columns and dataclass mapping |
| 7 | Tasks 1-6 | review records, review events, review status APIs |
| 8 | Tasks 1-7 | latest validation query APIs |
| 9 | Tasks 1-8 | atomic Phase 3 output insertion primitive |
| 10 | Tasks 1-9 | `apply_phase3_store_migration` and replay checks |
| 11 | Tasks 1-10 | Phase 3A acceptance coverage |

### Task 1: Store Migration Test Support

**Depends on:** repository baseline

**Existing repository evidence:**
- `tests/test_storyboard_legacy_migration.py:_create_planning_baseline_legacy_db(db_path)`
- `ai_drama_runtime/store.py:RuntimeStore(db_path, objects_root)`

**Files:**
- Create: `tests/shot_prompt_store_support.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_support_creates_phase2_legacy_database -q`

**Design requirements covered:**
- Phase 3A must use real Store patterns.
- Phase 3A test helpers must not include Service, Renderer, CLI, or lifecycle orchestration.

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_names, table_columns


def test_phase3a_support_creates_phase2_legacy_database(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"

    create_phase2_legacy_db(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        assert "artifacts" in table_columns(conn, "artifacts")
        assert "business_key_type" not in table_columns(conn, "artifacts")
        assert "one_current_approved_revision" in index_names(conn, "revisions")
    finally:
        conn.close()

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
import sqlite3


def table_columns(conn, table_name):
    return {row["name"]: row for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()}


def index_names(conn, table_name):
    return {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = ?",
            (table_name,),
        ).fetchall()
    }


def table_sql(conn, table_name):
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return "" if row is None else row["sql"]


def create_phase2_legacy_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE artifacts (
          artifact_id TEXT PRIMARY KEY,
          artifact_type TEXT NOT NULL,
          project_id TEXT NOT NULL,
          chapter_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE runs (
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
          approval_status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES runs(run_id)
        );
        CREATE TABLE validation_results (
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
        CREATE TABLE revision_outputs (
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
        );
        CREATE UNIQUE INDEX one_current_approved_revision
          ON revisions(artifact_id)
          WHERE approval_status = 'approved';
        CREATE INDEX revision_outputs_content_hash_idx ON revision_outputs(content_hash);
        CREATE INDEX revision_outputs_object_id_idx ON revision_outputs(object_id);
        INSERT INTO artifacts VALUES ('artifact-1', 'storyboard', 'project-1', 'chapter-1', '2026-06-30T00:00:00Z');
        INSERT INTO runs VALUES (
          'run-1', 'artifact-1', 'project-1', 'chapter-1', 'skill', 'v1', 'hash',
          'test-runtime', 'mock', 'mock', 'SUCCEEDED', 'request-object', 'response-object',
          'input-hash', 'request-hash', 'NOT_PROVIDED', 0, 0, 0, '', '', '',
          '2026-06-30T00:00:00Z', '2026-06-30T00:00:00Z', 0, '2026-06-30T00:00:00Z'
        );
        INSERT INTO revisions VALUES (
          'legacy-revision', 'artifact-1', 'storyboard', 'project-1', 'chapter-1',
          'run-1', 'skill', 'v1', 'hash', 'mock', 'mock', 1,
          'content-object', 'legacy-content-hash', 'response-object',
          'storyboard-canonical-json-v1', 'storyboard-canonical-v1',
          'model_generation', '', 'pending', '2026-06-30T00:00:00Z'
        );
        """
    )
    conn.commit()
    conn.close()
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

**Existing repository evidence:**
- `ai_drama_runtime/storyboard_migration.py:write_migration_preview(candidate, output_dir)`
- `ai_drama_runtime/store.py:RuntimeStore._init_schema(self)`

**Files:**
- Create: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_missing_schema_items_without_mutation -q`

**Design requirements covered:**
- deterministic inventory and preview;
- preview does not mutate database files.

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

from ai_drama_runtime.shot_prompt_migration import preview_phase3_store_migration
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_columns


def test_phase3_preview_reports_missing_schema_items_without_mutation(tmp_path):
    db_path = tmp_path / "runtime.db"
    create_phase2_legacy_db(db_path)

    before = db_path.read_bytes()
    preview = preview_phase3_store_migration(db_path)
    after = db_path.read_bytes()

    assert before == after
    assert preview["status"] == "PREVIEW"
    assert preview["database_path"] == str(db_path)
    assert preview["missing_columns"]["artifacts"] == ["business_key_type", "business_key_value"]
    assert "one_shot_prompt_set_per_source_storyboard_revision" in preview["missing_indexes"]
    assert "review_records" in preview["missing_tables"]
    assert "review_record_events" in preview["missing_tables"]

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        assert "business_key_type" not in table_columns(conn, "artifacts")
    finally:
        conn.close()
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_missing_schema_items_without_mutation -q
```

Expected:

```text
FAIL because ai_drama_runtime.shot_prompt_migration is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
import sqlite3
from pathlib import Path


PHASE3_ARTIFACT_COLUMNS = {
    "business_key_type": "TEXT NOT NULL DEFAULT ''",
    "business_key_value": "TEXT NOT NULL DEFAULT ''",
}
PHASE3_REQUIRED_TABLES = ("review_records", "review_record_events")
PHASE3_REQUIRED_INDEXES = ("one_shot_prompt_set_per_source_storyboard_revision",)


def _connect(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _columns(conn, table_name):
    return {row["name"]: row for row in conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()}


def _table_names(conn):
    return {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    }


def _index_names(conn):
    return {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'index'").fetchall()
    }


def preview_phase3_store_migration(db_path):
    db_path = Path(db_path)
    conn = _connect(db_path)
    try:
        artifact_columns = _columns(conn, "artifacts")
        missing_columns = {
            "artifacts": [
                name
                for name in PHASE3_ARTIFACT_COLUMNS
                if name not in artifact_columns
            ]
        }
        tables = _table_names(conn)
        indexes = _index_names(conn)
        return {
            "status": "PREVIEW",
            "database_path": str(db_path),
            "missing_columns": missing_columns,
            "missing_tables": [name for name in PHASE3_REQUIRED_TABLES if name not in tables],
            "missing_indexes": [name for name in PHASE3_REQUIRED_INDEXES if name not in indexes],
        }
    finally:
        conn.close()
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_preview_reports_missing_schema_items_without_mutation -q
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
git commit -m "feat: add phase 3a migration preview"
```

### Task 3: Artifact Business Key Schema And APIs

**Depends on:** Tasks 1-2

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore.ensure_artifact(self, artifact_id, artifact_type, project_id, chapter_id)`
- `ai_drama_runtime/store.py:RuntimeStore.artifacts(self)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_shot_prompt_artifact_business_key_is_unique_and_internal_id_is_generated -q`

**Design requirements covered:**
- generated internal `artifact_id`;
- business uniqueness by partial unique index;
- concurrent insert conflict recovery;
- legacy rows preserved.

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_names, table_columns


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
        other = store.ensure_shot_prompt_artifact(
            project_id="project-1",
            chapter_id="chapter-1",
            source_storyboard_revision_id="storyboard-revision-2",
        )

        assert first["artifact_id"] == second["artifact_id"]
        assert first["artifact_id"] != "storyboard-revision-1"
        assert other["artifact_id"] != first["artifact_id"]
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
                (
                    "manual-duplicate",
                    "shot_prompt_set",
                    "project-1",
                    "chapter-1",
                    "source_storyboard_revision_id",
                    "storyboard-revision-1",
                    "2026-07-03T00:00:00Z",
                ),
            )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        columns = table_columns(conn, "artifacts")
        assert columns["business_key_type"]["dflt_value"] == "''"
        assert columns["business_key_value"]["dflt_value"] == "''"
        assert "one_shot_prompt_set_per_source_storyboard_revision" in index_names(conn, "artifacts")
    finally:
        conn.close()
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
SHOT_PROMPT_ARTIFACT_TYPE = "shot_prompt_set"
SHOT_PROMPT_BUSINESS_KEY_TYPE = "source_storyboard_revision_id"

# Add these columns to CREATE TABLE artifacts in RuntimeStore._init_schema:
# business_key_type TEXT NOT NULL DEFAULT ''
# business_key_value TEXT NOT NULL DEFAULT ''

# Add this index to RuntimeStore._init_schema after one_current_approved_revision:
# CREATE UNIQUE INDEX IF NOT EXISTS one_shot_prompt_set_per_source_storyboard_revision
#   ON artifacts(artifact_type, business_key_type, business_key_value)
#   WHERE artifact_type = 'shot_prompt_set'
#     AND business_key_type = 'source_storyboard_revision_id';


def _ensure_artifact_business_key_columns(self):
    columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(artifacts)").fetchall()}
    additions = {
        "business_key_type": "TEXT NOT NULL DEFAULT ''",
        "business_key_value": "TEXT NOT NULL DEFAULT ''",
    }
    for name, spec in additions.items():
        if name not in columns:
            self.conn.execute("ALTER TABLE artifacts ADD COLUMN %s %s" % (name, spec))
    self.conn.execute(
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
        WHERE artifact_type = ?
          AND business_key_type = ?
          AND business_key_value = ?
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
            (artifact_id, artifact_type, project_id, chapter_id, business_key_type, business_key_value, created_at)
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
```

Wire `_ensure_artifact_business_key_columns(self)` into `RuntimeStore._ensure_columns(self)` after existing artifact table creation checks. Add `artifact_by_business_key` and `ensure_shot_prompt_artifact` as `RuntimeStore` methods using the signatures shown above.

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
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add shot prompt artifact business keys"
```

### Task 4: Revision Outputs Logical Types

**Depends on:** Tasks 1-3

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore.insert_revision_outputs_transaction(self, rows)`
- `ai_drama_runtime/store.py:RuntimeStore.get_revision_output(self, revision_id, logical_type)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_phase3_logical_types_and_preserve_legacy_rows -q`

**Design requirements covered:**
- all Phase 3 logical types accepted;
- old logical types preserved;
- explicit table rebuild columns;
- indexes and foreign keys preserved.

- [ ] **Step 1: Write the failing test**

```python
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_sql


def test_revision_outputs_accept_phase3_logical_types_and_preserve_legacy_rows(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        object_id = store.write_text_object("phase3 output")
        revision = store.get_revision("legacy-revision")
        records = store.insert_revision_outputs_transaction(
            [
                {
                    "revision_id": revision.revision_id,
                    "logical_type": "shot_prompt_positive_prompts",
                    "object_id": object_id,
                    "content_hash": object_id,
                    "media_type": "application/json",
                    "generator": "shot-prompt-renderer",
                    "generator_version": "1.0.0",
                },
                {
                    "revision_id": revision.revision_id,
                    "logical_type": "bundle_manifest",
                    "object_id": object_id,
                    "content_hash": object_id,
                    "media_type": "application/json",
                    "generator": "shot-prompt-bundle",
                    "generator_version": "1.0.0",
                },
            ]
        )
        assert [item.logical_type for item in records] == [
            "shot_prompt_positive_prompts",
            "bundle_manifest",
        ]
        assert store.get_revision_output(revision.revision_id, "bundle_manifest").content_hash == object_id
        sql = table_sql(store.conn, "revision_outputs")
        assert "shot_prompt_validation_report" in sql
        assert "rendered_markdown" in sql
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_phase3_logical_types_and_preserve_legacy_rows -q
```

Expected:

```text
FAIL because the revision_outputs CHECK rejects shot_prompt_positive_prompts
```

- [ ] **Step 3: Implement the minimal production change**

```python
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


def _revision_output_check_sql():
    quoted = ", ".join("'%s'" % item for item in REVISION_OUTPUT_LOGICAL_TYPES)
    return "logical_type TEXT NOT NULL CHECK (logical_type IN (%s))" % quoted


def _rebuild_revision_outputs_for_phase3(conn):
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'revision_outputs'"
    ).fetchone()["sql"]
    if "shot_prompt_validation_report" in sql:
        return
    conn.executescript(
        """
        ALTER TABLE revision_outputs RENAME TO revision_outputs_old;
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
        );
        INSERT INTO revision_outputs
        (revision_output_id, revision_id, logical_type, object_id, content_hash, media_type, generator, generator_version, created_at)
        SELECT revision_output_id, revision_id, logical_type, object_id, content_hash, media_type, generator, generator_version, created_at
        FROM revision_outputs_old
        ORDER BY created_at, revision_output_id;
        DROP TABLE revision_outputs_old;
        CREATE INDEX IF NOT EXISTS revision_outputs_content_hash_idx ON revision_outputs(content_hash);
        CREATE INDEX IF NOT EXISTS revision_outputs_object_id_idx ON revision_outputs(object_id);
        """
        % _revision_output_check_sql()
    )
```

Use `_revision_output_check_sql()` in both `RuntimeStore._init_schema(self)` and `_ensure_columns(self)`. Call `_rebuild_revision_outputs_for_phase3(self.conn)` from `_ensure_columns(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_outputs_accept_phase3_logical_types_and_preserve_legacy_rows -q
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
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: extend revision output logical types"
```

### Task 5: Revision Status Rebuild

**Depends on:** Tasks 1-4

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore.insert_revision(self, **values)`
- `ai_drama_runtime/store.py:RuntimeStore.current_approved(self, artifact_id)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_accepts_revoked_and_preserves_current_approved_index -q`

**Design requirements covered:**
- revision statuses include `pending`, `approved`, `rejected`, `superseded`, `revoked`;
- `one_current_approved_revision` remains authoritative.

- [ ] **Step 1: Write the failing test**

```python
import sqlite3

import pytest

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_sql


def test_revision_status_check_accepts_revoked_and_preserves_current_approved_index(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        row = store.conn.execute(
            "UPDATE revisions SET approval_status = 'revoked' WHERE revision_id = ?",
            ("legacy-revision",),
        )
        assert row.rowcount == 1
        store.conn.commit()
        assert store.get_revision("legacy-revision").approval_status == "revoked"

        with pytest.raises(sqlite3.IntegrityError):
            store.conn.execute(
                "UPDATE revisions SET approval_status = 'unknown' WHERE revision_id = ?",
                ("legacy-revision",),
            )

        sql = table_sql(store.conn, "revisions")
        assert "approval_status TEXT NOT NULL CHECK" in sql
        assert "superseded" in sql
        assert "revoked" in sql
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_accepts_revoked_and_preserves_current_approved_index -q
```

Expected:

```text
FAIL because revisions.approval_status has no CHECK
```

- [ ] **Step 3: Implement the minimal production change**

```python
REVISION_APPROVAL_STATUSES = ("pending", "approved", "rejected", "superseded", "revoked")


def _revision_status_check_sql():
    quoted = ", ".join("'%s'" % item for item in REVISION_APPROVAL_STATUSES)
    return "approval_status TEXT NOT NULL CHECK (approval_status IN (%s))" % quoted


def _rebuild_revisions_for_phase3(conn):
    sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'revisions'"
    ).fetchone()["sql"]
    if "approval_status TEXT NOT NULL CHECK" in sql and "revoked" in sql:
        return
    conn.executescript(
        """
        DROP INDEX IF EXISTS one_current_approved_revision;
        ALTER TABLE revisions RENAME TO revisions_old;
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
        );
        INSERT INTO revisions
        SELECT revision_id, artifact_id, artifact_type, project_id, chapter_id, run_id,
               skill_id, skill_version, skill_package_hash, runtime_provider, runtime_model,
               number, content_object_id, content_hash, raw_response_object_id, parser_version,
               content_profile, derivation_type, supersedes_revision_id, approval_status, created_at
        FROM revisions_old
        ORDER BY artifact_id, number;
        DROP TABLE revisions_old;
        CREATE UNIQUE INDEX IF NOT EXISTS one_current_approved_revision
          ON revisions(artifact_id)
          WHERE approval_status = 'approved';
        """
        % _revision_status_check_sql()
    )
```

Use `_revision_status_check_sql()` in `RuntimeStore._init_schema(self)` and call `_rebuild_revisions_for_phase3(self.conn)` from `_ensure_columns(self)`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_revision_status_check_accepts_revoked_and_preserves_current_approved_index -q
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
git add ai_drama_runtime/store.py ai_drama_runtime/shot_prompt_migration.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add phase 3 revision statuses"
```

### Task 6: Approval Evidence Columns

**Depends on:** Tasks 1-5

**Existing repository evidence:**
- `ai_drama_runtime/store.py:ApprovalRecord`
- `ai_drama_runtime/store.py:RuntimeStore.approval_record(self, record_id)`
- `ai_drama_runtime/store.py:RuntimeStore.latest_approval(self, revision_id)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_gain_evidence_columns_with_legacy_defaults -q`

**Design requirements covered:**
- Approval references qualification-report evidence;
- Phase 3A stores evidence fields only;
- old records receive safe defaults.

- [ ] **Step 1: Write the failing test**

```python
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, table_columns


def test_approval_records_gain_evidence_columns_with_legacy_defaults(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        columns = table_columns(store.conn, "approval_records")
        for name in (
            "qualification_profile_id",
            "qualification_profile_version",
            "qualification_report_object_id",
            "qualification_report_hash",
            "bundle_manifest_hash",
            "render_provenance_hash",
            "source_approval_record_id",
        ):
            assert columns[name]["dflt_value"] == "''"

        revision = store.get_revision("legacy-revision")
        approval = store.approve_in_transaction(revision, "tester", "legacy approval")
        assert approval.qualification_profile_id == ""
        assert approval.qualification_report_hash == ""
        assert store.latest_approval(revision.revision_id).record_id == approval.record_id
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_gain_evidence_columns_with_legacy_defaults -q
```

Expected:

```text
FAIL because ApprovalRecord has no qualification evidence fields
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
    qualification_profile_id: str
    qualification_profile_version: str
    qualification_report_object_id: str
    qualification_report_hash: str
    bundle_manifest_hash: str
    render_provenance_hash: str
    source_approval_record_id: str


def _ensure_approval_evidence_columns(self):
    columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(approval_records)").fetchall()}
    additions = {
        "qualification_profile_id": "TEXT NOT NULL DEFAULT ''",
        "qualification_profile_version": "TEXT NOT NULL DEFAULT ''",
        "qualification_report_object_id": "TEXT NOT NULL DEFAULT ''",
        "qualification_report_hash": "TEXT NOT NULL DEFAULT ''",
        "bundle_manifest_hash": "TEXT NOT NULL DEFAULT ''",
        "render_provenance_hash": "TEXT NOT NULL DEFAULT ''",
        "source_approval_record_id": "TEXT NOT NULL DEFAULT ''",
    }
    for name, spec in additions.items():
        if name not in columns:
            self.conn.execute("ALTER TABLE approval_records ADD COLUMN %s %s" % (name, spec))
```

Call `_ensure_approval_evidence_columns(self)` from `RuntimeStore._ensure_columns(self)`. Keep `approve_in_transaction` and `record_rejection` unchanged except for relying on column defaults.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_approval_records_gain_evidence_columns_with_legacy_defaults -q
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
git add ai_drama_runtime/store.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: store approval qualification evidence"
```

### Task 7: Review Tables And Store APIs

**Depends on:** Tasks 1-6

**Existing repository evidence:**
- `ai_drama_runtime/store.py:ApprovalRecord`
- `ai_drama_runtime/store.py:RuntimeStore.approval_record(self, record_id)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_review_records.py -q`

**Design requirements covered:**
- review fields are `body`, `body_hash`, `created_by`;
- Event actor is stored as `actor`;
- Review Records are append-only storage;
- current review status and open blocking count are Store APIs.

- [ ] **Step 1: Write the failing test**

```python
import hashlib

from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db


def test_review_records_and_events_are_append_only_and_queryable(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        body = "Shot 1 needs clearer continuity."
        review = store.insert_review_record(
            artifact_id="artifact-1",
            revision_id="legacy-revision",
            scope="shot",
            shot_id="SHOT_001",
            body=body,
            blocking=True,
            created_by="reviewer-a",
        )
        assert review.body == body
        assert review.body_hash == hashlib.sha256(body.encode("utf-8")).hexdigest()
        assert review.blocking is True
        assert review.created_by == "reviewer-a"

        opened = store.insert_review_event(
            review_id=review.review_id,
            event_type="opened",
            actor="reviewer-a",
            note="needs fix",
        )
        resolved = store.insert_review_event(
            review_id=review.review_id,
            event_type="resolved",
            actor="reviewer-b",
            note="fixed",
        )

        assert store.review_events(review.review_id) == [opened, resolved]
        assert store.review_status(review.review_id) == "resolved"
        assert store.open_blocking_review_count("legacy-revision") == 0
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py -q
```

Expected:

```text
FAIL because RuntimeStore.insert_review_record is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
@dataclass(frozen=True)
class ReviewRecord:
    review_id: str
    artifact_id: str
    revision_id: str
    scope: str
    shot_id: str
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


def _ensure_review_tables(self):
    self.conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS review_records (
          review_id TEXT PRIMARY KEY,
          artifact_id TEXT NOT NULL,
          revision_id TEXT NOT NULL,
          scope TEXT NOT NULL CHECK (scope IN ('set','shot')),
          shot_id TEXT NOT NULL,
          body TEXT NOT NULL,
          body_hash TEXT NOT NULL,
          blocking INTEGER NOT NULL CHECK (blocking IN (0,1)),
          created_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(revision_id) REFERENCES revisions(revision_id)
        );
        CREATE TABLE IF NOT EXISTS review_record_events (
          event_id TEXT PRIMARY KEY,
          review_id TEXT NOT NULL,
          event_type TEXT NOT NULL CHECK (event_type IN ('opened','commented','resolved','reopened')),
          actor TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(review_id) REFERENCES review_records(review_id)
        );
        CREATE INDEX IF NOT EXISTS review_records_revision_idx ON review_records(revision_id);
        CREATE INDEX IF NOT EXISTS review_record_events_review_idx ON review_record_events(review_id, created_at, event_id);
        """
    )


def insert_review_record(self, *, artifact_id, revision_id, scope, shot_id="", body, blocking, created_by):
    review_id = uuid.uuid4().hex
    body_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    self.conn.execute(
        """
        INSERT INTO review_records
        (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, blocking, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (review_id, artifact_id, revision_id, scope, shot_id, body, body_hash, int(blocking), created_by, now_iso()),
    )
    self.conn.commit()
    return self.review_record(review_id)


def insert_review_event(self, *, review_id, event_type, actor, note=""):
    event_id = uuid.uuid4().hex
    self.conn.execute(
        """
        INSERT INTO review_record_events
        (event_id, review_id, event_type, actor, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (event_id, review_id, event_type, actor, note, now_iso()),
    )
    self.conn.commit()
    return self.review_event(event_id)
```

Add `review_record`, `review_event`, `review_events`, `review_status`, `open_blocking_review_count`, `_review_from_row`, and `_review_event_from_row` Store methods using the same row-to-dataclass style as `_approval_from_row`. `review_status(review_id)` returns the latest event type by `(created_at, event_id)`. `open_blocking_review_count(revision_id)` counts blocking review records whose latest event type is not `resolved`.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_review_records.py -q
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
git add ai_drama_runtime/store.py tests/test_shot_prompt_review_records.py
git commit -m "feat: add shot prompt review records"
```

### Task 8: Latest Validation Query APIs

**Depends on:** Tasks 1-7

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore.insert_validation(self, **values)`
- `ai_drama_runtime/store.py:RuntimeStore.validation_results(self, revision_id)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_latest_validation_queries_are_deterministic -q`

**Design requirements covered:**
- Store supports persisted validation results for later Phase 3B validators;
- latest query is Store-only and does not run validators.

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

        latest = store.latest_validation_result("legacy-revision", "shot_prompt_schema")
        assert latest.status == "PASS"
        by_id = store.latest_validation_results("legacy-revision")
        assert by_id["shot_prompt_schema"].status == "PASS"
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
git add ai_drama_runtime/store.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add latest validation store queries"
```

### Task 9: Atomic Phase 3 Revision Output Insertion

**Depends on:** Tasks 1-8

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore.insert_revision_outputs_transaction(self, rows)`
- `ai_drama_runtime/store.py:RuntimeStore.revision_outputs(self, revision_id)`

**Files:**
- Modify: `ai_drama_runtime/store.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_outputs_insert_atomically_and_rollback_on_conflict -q`

**Design requirements covered:**
- formal Phase 3 output rows are inserted together;
- partial insert rolls back to zero rows;
- conflicting existing data is not deleted.

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
        for logical_type in (
            "shot_prompt_positive_prompts",
            "shot_prompt_negative_prompts",
            "shot_prompt_asset_requirements",
            "shot_prompt_render_provenance",
            "shot_prompt_review_markdown",
            "shot_prompt_validation_report",
            "bundle_manifest",
        )
    ]


def test_phase3_outputs_insert_atomically_and_rollback_on_conflict(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        rows = _phase3_rows(store, "legacy-revision")
        inserted = store.insert_phase3_revision_outputs_atomically("legacy-revision", rows)
        assert [item.logical_type for item in inserted] == [row["logical_type"] for row in rows]

        with pytest.raises(ValueError):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", rows[:-1])

        assert len(store.revision_outputs("legacy-revision")) == 7


def test_phase3_outputs_rollback_zero_rows_when_mid_insert_fails(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    with RuntimeStore(db_path, objects_root) as store:
        rows = _phase3_rows(store, "legacy-revision")
        rows[3] = dict(rows[3], logical_type="not_allowed")

        with pytest.raises(Exception):
            store.insert_phase3_revision_outputs_atomically("legacy-revision", rows)

        assert store.revision_outputs("legacy-revision") == []
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_outputs_insert_atomically_and_rollback_on_conflict tests/test_shot_prompt_store_migration.py::test_phase3_outputs_rollback_zero_rows_when_mid_insert_fails -q
```

Expected:

```text
FAIL because RuntimeStore.insert_phase3_revision_outputs_atomically is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES = (
    "shot_prompt_positive_prompts",
    "shot_prompt_negative_prompts",
    "shot_prompt_asset_requirements",
    "shot_prompt_render_provenance",
    "shot_prompt_review_markdown",
    "shot_prompt_validation_report",
    "bundle_manifest",
)


def insert_phase3_revision_outputs_atomically(self, revision_id, rows):
    rows = [dict(row) for row in rows]
    logical_types = [row.get("logical_type") for row in rows]
    if logical_types != list(PHASE3_FORMAL_OUTPUT_LOGICAL_TYPES):
        raise ValueError("phase3 outputs must match required logical type order")
    for row in rows:
        if row.get("revision_id") != revision_id:
            raise ValueError("phase3 output revision_id mismatch")
    with self.conn:
        return self.insert_revision_outputs_transaction(rows)
```

The existing `insert_revision_outputs_transaction(self, rows)` must not call `commit()`. It is already transaction-friendly. Leave existing rows untouched when validation fails before entering the transaction.

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3_outputs_insert_atomically_and_rollback_on_conflict tests/test_shot_prompt_store_migration.py::test_phase3_outputs_rollback_zero_rows_when_mid_insert_fails -q
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
git add ai_drama_runtime/store.py tests/test_shot_prompt_store_migration.py
git commit -m "feat: add atomic shot prompt output insertion"
```

### Task 10: Migration Apply, Replay, And Rollback

**Depends on:** Tasks 1-9

**Existing repository evidence:**
- `ai_drama_runtime/store.py:RuntimeStore._ensure_columns(self)`
- `tests/test_storyboard_legacy_migration.py:test_phase2_migration_replay_is_idempotent(tmp_path)`

**Files:**
- Modify: `ai_drama_runtime/shot_prompt_migration.py`
- Test: `tests/test_shot_prompt_store_migration.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_leaves_no_temp_tables -q`

**Design requirements covered:**
- single transaction owner;
- replay idempotency;
- injected failure rollback;
- no transient `_new` tables;
- foreign key check;
- Store can reopen after migration.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from ai_drama_runtime.shot_prompt_migration import Phase3StoreMigrationError, apply_phase3_store_migration
from ai_drama_runtime.store import RuntimeStore
from tests.shot_prompt_store_support import create_phase2_legacy_db, index_names, table_columns


def test_apply_phase3_store_migration_is_idempotent_and_leaves_no_temp_tables(tmp_path):
    db_path = tmp_path / "runtime.db"
    objects_root = tmp_path / "objects"
    create_phase2_legacy_db(db_path)

    first = apply_phase3_store_migration(db_path)
    second = apply_phase3_store_migration(db_path)

    assert first["status"] == "APPLIED"
    assert second["status"] == "ALREADY_CURRENT"

    with RuntimeStore(db_path, objects_root) as store:
        assert "business_key_value" in table_columns(store.conn, "artifacts")
        assert "one_shot_prompt_set_per_source_storyboard_revision" in index_names(store.conn, "artifacts")
        temp_tables = [
            row["name"]
            for row in store.conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE '%_new'"
            ).fetchall()
        ]
        assert temp_tables == []
        assert store.conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_apply_phase3_store_migration_rolls_back_injected_failure(tmp_path):
    db_path = tmp_path / "runtime.db"
    create_phase2_legacy_db(db_path)
    before = db_path.read_bytes()

    with pytest.raises(Phase3StoreMigrationError):
        apply_phase3_store_migration(db_path, fail_after_step="artifact_business_key")

    after = db_path.read_bytes()
    assert after == before
```

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_leaves_no_temp_tables tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_rolls_back_injected_failure -q
```

Expected:

```text
FAIL because apply_phase3_store_migration is not defined
```

- [ ] **Step 3: Implement the minimal production change**

```python
class Phase3StoreMigrationError(RuntimeError):
    pass


def _migration_is_current(conn):
    preview = {
        "missing_columns": {
            "artifacts": [
                name
                for name in PHASE3_ARTIFACT_COLUMNS
                if name not in _columns(conn, "artifacts")
            ]
        },
        "missing_tables": [name for name in PHASE3_REQUIRED_TABLES if name not in _table_names(conn)],
        "missing_indexes": [name for name in PHASE3_REQUIRED_INDEXES if name not in _index_names(conn)],
    }
    return not preview["missing_columns"]["artifacts"] and not preview["missing_tables"] and not preview["missing_indexes"]


def _foreign_key_check(conn):
    failures = conn.execute("PRAGMA foreign_key_check").fetchall()
    if failures:
        raise Phase3StoreMigrationError("foreign key check failed")


def apply_phase3_store_migration(db_path, *, fail_after_step=""):
    conn = _connect(db_path)
    try:
        if _migration_is_current(conn):
            return {"status": "ALREADY_CURRENT", "database_path": str(Path(db_path))}
        try:
            conn.execute("BEGIN")
            _ensure_artifact_business_key_columns_for_conn(conn)
            if fail_after_step == "artifact_business_key":
                raise Phase3StoreMigrationError("injected failure after artifact_business_key")
            _rebuild_revisions_for_phase3(conn)
            _rebuild_revision_outputs_for_phase3(conn)
            _ensure_approval_evidence_columns_for_conn(conn)
            _ensure_review_tables_for_conn(conn)
            _foreign_key_check(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return {"status": "APPLIED", "database_path": str(Path(db_path))}
    finally:
        conn.close()
```

Define `MIGRATION_STEPS` only after all helper functions are defined:

```python
MIGRATION_STEPS = (
    "artifact_business_key",
    "revisions_status",
    "revision_outputs",
    "approval_evidence",
    "review_tables",
    "foreign_key_check",
)
```

- [ ] **Step 4: Run the focused test**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_is_idempotent_and_leaves_no_temp_tables tests/test_shot_prompt_store_migration.py::test_apply_phase3_store_migration_rolls_back_injected_failure -q
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

### Task 11: Phase 3A Acceptance

**Depends on:** Tasks 1-10

**Existing repository evidence:**
- `tools/verify_phase2_minimal_bundle_foundation.py:final_checks(execution_start_commit: str = EXECUTION_START_COMMIT)`
- `tests/test_storyboard_legacy_migration.py:test_phase2_migration_replay_is_idempotent(tmp_path)`

**Files:**
- Test: `tests/test_shot_prompt_store_migration.py`
- Test: `tests/test_shot_prompt_review_records.py`
- Verify: `python3 -m pytest tests/test_shot_prompt_store_migration.py tests/test_shot_prompt_review_records.py -q`

**Design requirements covered:**
- Phase 3A focused acceptance;
- Phase 0-2 Store regressions remain green;
- no Store/Migration scope leakage.

- [ ] **Step 1: Write the failing acceptance test**

```python
from pathlib import Path


def test_phase3a_plan_scope_does_not_create_later_phase_files():
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

- [ ] **Step 2: Run the focused test and verify failure**

```bash
python3 -m pytest tests/test_shot_prompt_store_migration.py::test_phase3a_plan_scope_does_not_create_later_phase_files -q
```

Expected:

```text
PASS when Tasks 1-10 did not create later-phase files
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

## Mechanical Audit Gate

The Phase 3A plan must pass a mechanical audit before review handoff. The audit report for this planning revision is generated outside the repository under `/tmp/phase3a-plan-audit/`.

Required zero-count checks:

```text
future_dependencies = 0
undefined_plan_symbols = 0
repository_signature_mismatches = 0
syntax_or_definition_order = 0
task_local_failures = 0
schema_drift = 0
migration_contract_failures = 0
```

The audit must classify Python builtins, imported library symbols, attribute methods, `pytest` APIs, SQLite cursor APIs, and string methods as non-plan symbols.

## Verification

Planning-time verification before committing this document:

```bash
python3 /tmp/phase3a-plan-audit/audit_phase3a_plan.py
git diff --check
python3 -m pytest -q
```

Expected final planning state:

```text
Phase 3A: IMPLEMENTATION_PLAN_PENDING_USER_REVIEW
Implementation: IMPLEMENTATION_NOT_AUTHORIZED
Phase 3B+: NOT_AUTHORIZED
Phase 4: PHASE4_NOT_AUTHORIZED
```
