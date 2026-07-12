import json
import uuid
import hashlib

from ai_drama_runtime.services import NotFound
from ai_drama_runtime.store import RuntimeStore, now_iso

from .models import (
    AssetBindingRecord,
    AssetRecord,
    ChapterRecord,
    ChapterSourceRevisionRecord,
    GenerationJobRecord,
    GenerationResultRecord,
    ProductionProfileRecord,
    ProjectRecord,
    RerunRecord,
    ResultReviewRecord,
    ShotResultSelectionRecord,
)
from .suppliers.models import (
    ConfigRevisionRecord,
    RevisionConflict,
    SupplierRecord,
    SupplierVersionRecord,
)


GENERATION_JOB_TRANSITIONS = {
    "draft": {"queued"},
    "queued": {"submitting", "cancelled"},
    "submitting": {"submitted", "failed"},
    "submitted": {"polling", "completed", "failed"},
    "polling": {"polling", "completed", "failed"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}

M6A_SUPPLIER_MIGRATION_ID = "m6a_supplier_core_v1"
M6A_SUPPLIER_FINGERPRINT_MIGRATION_ID = "m6a_supplier_runtime_fingerprint_v2"
BUILTIN_SUPPLIERS = (
    ("agnes", "Agnes"),
    ("anthropic", "Anthropic"),
    ("deepseek", "DeepSeek"),
    ("openai", "OpenAI"),
    ("xai", "xAI Grok"),
)


class ProductStore:
    def __init__(self, runtime_store: RuntimeStore):
        self.runtime = runtime_store
        self.conn = runtime_store.conn
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS projects (
              project_id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT NOT NULL,
              series_canon TEXT NOT NULL,
              characters_context TEXT NOT NULL,
              production_brief TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chapters (
              chapter_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              title TEXT NOT NULL,
              position INTEGER NOT NULL,
              current_source_revision_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(project_id, position)
            );
            CREATE TABLE IF NOT EXISTS chapter_source_revisions (
              source_revision_id TEXT PRIMARY KEY,
              chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
              number INTEGER NOT NULL,
              object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(chapter_id, number)
            );
            CREATE TABLE IF NOT EXISTS production_profiles (
              profile_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL DEFAULT '',
              profile_type TEXT NOT NULL CHECK (profile_type IN ('character','scene','prop','style')),
              name TEXT NOT NULL,
              payload_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS production_profiles_scope_idx
              ON production_profiles(project_id, chapter_id, profile_type, name);
            CREATE TABLE IF NOT EXISTS assets (
              asset_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL DEFAULT '',
              asset_type TEXT NOT NULL CHECK (asset_type IN ('character_reference','character_outfit','scene_reference','scene_angle','prop_reference','shot_keyframe')),
              name TEXT NOT NULL,
              object_id TEXT NOT NULL,
              media_type TEXT NOT NULL,
              width INTEGER NOT NULL DEFAULT 0,
              height INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL CHECK (status IN ('draft','generating','usable','rejected','failed')),
              source_type TEXT NOT NULL CHECK (source_type IN ('upload','agnes','derived')),
              source_job_id TEXT NOT NULL DEFAULT '',
              metadata_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS asset_bindings (
              binding_id TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL REFERENCES assets(asset_id) ON DELETE RESTRICT,
              project_id TEXT NOT NULL DEFAULT '',
              chapter_id TEXT NOT NULL DEFAULT '',
              target_type TEXT NOT NULL CHECK (target_type IN ('character','scene','prop','shot')),
              target_id TEXT NOT NULL,
              role TEXT NOT NULL,
              is_current INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              UNIQUE(asset_id, target_type, target_id, role)
            );
            CREATE TABLE IF NOT EXISTS asset_requirement_sets (
              requirement_set_id TEXT PRIMARY KEY,
              chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
              storyboard_revision_id TEXT NOT NULL,
              content_object_id TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS generation_jobs (
              job_id TEXT PRIMARY KEY,
              provider TEXT NOT NULL,
              job_type TEXT NOT NULL CHECK (job_type IN ('image','video')),
              project_id TEXT NOT NULL,
              chapter_id TEXT NOT NULL,
              shot_id TEXT NOT NULL DEFAULT '',
              prompt_revision_id TEXT NOT NULL DEFAULT '',
              provider_job_id TEXT NOT NULL DEFAULT '',
              provider_result_id TEXT NOT NULL DEFAULT '',
              internal_status TEXT NOT NULL CHECK (internal_status IN ('draft','queued','submitting','submitted','polling','completed','failed','cancelled')),
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              request_object_id TEXT NOT NULL,
              response_object_id TEXT NOT NULL DEFAULT '',
              attempt_number INTEGER NOT NULL,
              error_code TEXT NOT NULL DEFAULT '',
              error_message TEXT NOT NULL DEFAULT '',
              submitted_at TEXT NOT NULL DEFAULT '',
              next_poll_at TEXT NOT NULL DEFAULT '',
              completed_at TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(provider, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS generation_jobs_chapter_idx
              ON generation_jobs(chapter_id, shot_id, created_at, job_id);
            CREATE TABLE IF NOT EXISTS generation_results (
              result_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL,
              shot_id TEXT NOT NULL,
              object_id TEXT NOT NULL,
              media_type TEXT NOT NULL,
              source_url TEXT NOT NULL,
              source_url_state TEXT NOT NULL DEFAULT 'source_url_active',
              metadata_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS generation_results_shot_idx
              ON generation_results(chapter_id, shot_id, created_at, result_id);
            CREATE TABLE IF NOT EXISTS shot_result_selections (
              chapter_id TEXT NOT NULL,
              shot_id TEXT NOT NULL,
              result_id TEXT NOT NULL REFERENCES generation_results(result_id) ON DELETE RESTRICT,
              selected_at TEXT NOT NULL,
              PRIMARY KEY(chapter_id, shot_id)
            );
            CREATE TABLE IF NOT EXISTS result_reviews (
              review_id TEXT PRIMARY KEY,
              result_id TEXT NOT NULL REFERENCES generation_results(result_id) ON DELETE RESTRICT,
              decision TEXT NOT NULL CHECK (decision IN ('passed','failed')),
              failure_category TEXT NOT NULL DEFAULT '',
              note TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS rerun_records (
              rerun_id TEXT PRIMARY KEY,
              source_job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
              new_job_id TEXT NOT NULL REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
              overrides_object_id TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS schema_migrations (
              migration_id TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS suppliers (
              supplier_id TEXT PRIMARY KEY,
              slug TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL,
              source TEXT NOT NULL CHECK (source IN ('built_in','custom')),
              enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
              current_supplier_version_id TEXT NOT NULL DEFAULT '',
              current_config_revision_id TEXT NOT NULL DEFAULT '',
              current_credential_version_id TEXT NOT NULL DEFAULT '',
              revision INTEGER NOT NULL DEFAULT 1,
              config_revision INTEGER NOT NULL DEFAULT 0,
              credential_revision INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_versions (
              supplier_version_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              revision INTEGER NOT NULL,
              source_object_id TEXT NOT NULL,
              source_hash TEXT NOT NULL,
              compiled_artifact_object_id TEXT NOT NULL,
              compiled_artifact_hash TEXT NOT NULL,
              manifest_hash TEXT NOT NULL,
              adapter_contract_version TEXT NOT NULL DEFAULT '',
              worker_protocol_version TEXT NOT NULL DEFAULT '',
              worker_runtime_version TEXT NOT NULL DEFAULT '',
              compiler_name TEXT NOT NULL DEFAULT '',
              compiler_version TEXT NOT NULL DEFAULT '',
              compiler_options_hash TEXT NOT NULL DEFAULT '',
              helper_api_version TEXT NOT NULL DEFAULT '',
              built_in INTEGER NOT NULL DEFAULT 0 CHECK (built_in IN (0,1)),
              created_at TEXT NOT NULL,
              UNIQUE(supplier_id, revision)
            );
            CREATE TABLE IF NOT EXISTS supplier_config_revisions (
              config_revision_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              revision INTEGER NOT NULL,
              config_object_id TEXT NOT NULL,
              config_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(supplier_id, revision)
            );
            CREATE TABLE IF NOT EXISTS credential_versions (
              credential_version_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              revision INTEGER NOT NULL,
              state TEXT NOT NULL CHECK (state IN ('pending_finalize','ready','pending_delete','credential_storage_corrupt')),
              secret_path TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(supplier_id, revision)
            );
            CREATE TABLE IF NOT EXISTS credential_migration_journal (
              operation_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              credential_version_id TEXT NOT NULL,
              operation TEXT NOT NULL CHECK (operation IN ('replace','delete')),
              state TEXT NOT NULL,
              temp_path TEXT NOT NULL,
              final_path TEXT NOT NULL,
              content_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_creation_requests (
              idempotency_key TEXT PRIMARY KEY,
              request_hash TEXT NOT NULL,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              created_at TEXT NOT NULL
            );
            """
        )
        self._ensure_column("asset_bindings", "is_current", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("asset_bindings", "project_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("asset_bindings", "chapter_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_results", "source_url_state", "TEXT NOT NULL DEFAULT 'source_url_active'")
        self._ensure_column("supplier_versions", "adapter_contract_version", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "worker_protocol_version", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "worker_runtime_version", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "compiler_name", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "compiler_version", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "compiler_options_hash", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "helper_api_version", "TEXT NOT NULL DEFAULT ''")
        self._backfill_asset_binding_scope()
        self._normalize_current_asset_bindings()
        self.conn.execute("DROP INDEX IF EXISTS asset_bindings_current_role_idx")
        self.conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS asset_bindings_current_role_idx
              ON asset_bindings(project_id, chapter_id, target_type, target_id, role)
              WHERE is_current = 1
            """
        )
        self._apply_supplier_core_migration()
        self._apply_supplier_runtime_fingerprint_migration()
        self.conn.commit()

    def _apply_supplier_core_migration(self):
        if self.conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (M6A_SUPPLIER_MIGRATION_ID,),
        ).fetchone():
            return
        created_at = now_iso()
        for slug, display_name in BUILTIN_SUPPLIERS:
            supplier_id = uuid.uuid5(uuid.NAMESPACE_URL, "ai-drama:supplier:%s" % slug).hex
            config_revision_id = uuid.uuid5(
                uuid.NAMESPACE_URL, "ai-drama:supplier:%s:config:1" % slug
            ).hex
            self.conn.execute(
                """
                INSERT OR IGNORE INTO suppliers
                (supplier_id, slug, display_name, source, enabled,
                 current_config_revision_id, revision, config_revision,
                 credential_revision, created_at, updated_at)
                VALUES (?, ?, ?, 'built_in', 1, ?, 1, 1, 0, ?, ?)
                """,
                (supplier_id, slug, display_name, config_revision_id, created_at, created_at),
            )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO supplier_config_revisions
                (config_revision_id, supplier_id, revision, config_object_id,
                 config_hash, created_at)
                VALUES (?, ?, 1, '', '', ?)
                """,
                (config_revision_id, supplier_id, created_at),
            )
        self.conn.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (M6A_SUPPLIER_MIGRATION_ID, created_at),
        )

    def _apply_supplier_runtime_fingerprint_migration(self):
        if self.conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (M6A_SUPPLIER_FINGERPRINT_MIGRATION_ID,),
        ).fetchone():
            return
        created_at = now_iso()
        for slug, _display_name in BUILTIN_SUPPLIERS:
            supplier = self.conn.execute(
                "SELECT * FROM suppliers WHERE slug = ?", (slug,)
            ).fetchone()
            if supplier is None:
                continue
            version = self.conn.execute(
                "SELECT supplier_version_id FROM supplier_versions WHERE supplier_id = ? AND built_in = 1",
                (supplier["supplier_id"],),
            ).fetchone()
            if version is None:
                vendor = {
                    "id": slug,
                    "version": "m6a-template-1",
                    "name": supplier["display_name"],
                    "author": "AI Drama",
                    "adapterContractVersion": "ai-drama-supplier-v1",
                    "helperApiVersion": "ai-drama-helper-v1",
                    "rateLimitBucketKey": slug,
                    "inputs": [],
                    "inputValues": {},
                    "models": [],
                }
                manifest = json.dumps(
                    vendor, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                source = "export const vendor = %s;\n" % manifest
                compiled = "module.exports.vendor = %s;\n" % manifest
                source_object_id = self.runtime.write_text_object(source)
                compiled_object_id = self.runtime.write_text_object(compiled)
                supplier_version_id = uuid.uuid5(
                    uuid.NAMESPACE_URL, "ai-drama:supplier:%s:version:1" % slug
                ).hex
                self.conn.execute(
                    """
                    INSERT INTO supplier_versions
                    (supplier_version_id, supplier_id, revision, source_object_id,
                     source_hash, compiled_artifact_object_id, compiled_artifact_hash,
                     manifest_hash, adapter_contract_version, worker_protocol_version,
                     worker_runtime_version, compiler_name, compiler_version,
                     compiler_options_hash, helper_api_version, built_in, created_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, 'ai-drama-supplier-v1', '1',
                            'unavailable-m6a-template', 'builtin-template', '1', ?,
                            'ai-drama-helper-v1', 1, ?)
                    """,
                    (
                        supplier_version_id,
                        supplier["supplier_id"],
                        source_object_id,
                        _sha256(source),
                        compiled_object_id,
                        _sha256(compiled),
                        _sha256(manifest),
                        _sha256("{}"),
                        created_at,
                    ),
                )
                version = {"supplier_version_id": supplier_version_id}
            self.conn.execute(
                "UPDATE suppliers SET current_supplier_version_id = ? WHERE supplier_id = ?",
                (version["supplier_version_id"], supplier["supplier_id"]),
            )
        self.conn.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (M6A_SUPPLIER_FINGERPRINT_MIGRATION_ID, created_at),
        )

    def create_supplier(self, *, slug, display_name):
        if self.conn.execute("SELECT 1 FROM suppliers WHERE slug = ?", (slug,)).fetchone():
            raise ValueError("supplier slug already exists: %s" % slug)
        supplier_id = uuid.uuid4().hex
        config_revision_id = uuid.uuid4().hex
        created_at = now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO suppliers
                (supplier_id, slug, display_name, source, enabled,
                 current_config_revision_id, revision, config_revision,
                 credential_revision, created_at, updated_at)
                VALUES (?, ?, ?, 'custom', 1, ?, 1, 1, 0, ?, ?)
                """,
                (supplier_id, slug, display_name, config_revision_id, created_at, created_at),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_config_revisions
                (config_revision_id, supplier_id, revision, config_object_id,
                 config_hash, created_at)
                VALUES (?, ?, 1, '', '', ?)
                """,
                (config_revision_id, supplier_id, created_at),
            )
        return self.get_supplier(supplier_id)

    def get_supplier(self, supplier_id):
        row = self.conn.execute(
            "SELECT * FROM suppliers WHERE supplier_id = ?", (supplier_id,)
        ).fetchone()
        return None if row is None else SupplierRecord(**dict(row))

    def list_suppliers(self):
        rows = self.conn.execute("SELECT * FROM suppliers ORDER BY slug").fetchall()
        return [SupplierRecord(**dict(row)) for row in rows]

    def replace_supplier_version(
        self,
        supplier_id,
        *,
        source_object_id,
        source_hash,
        compiled_artifact_object_id,
        compiled_artifact_hash,
        manifest_hash,
        adapter_contract_version="ai-drama-supplier-v1",
        worker_protocol_version="1",
        worker_runtime_version="unavailable",
        compiler_name="unknown",
        compiler_version="unknown",
        compiler_options_hash="",
        helper_api_version="ai-drama-helper-v1",
        expected_revision,
        built_in=False,
    ):
        supplier_version_id = uuid.uuid4().hex
        created_at = now_iso()
        with self.conn:
            supplier = self.get_supplier(supplier_id)
            if supplier is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            if supplier.revision != expected_revision:
                raise RevisionConflict("supplier revision conflict")
            revision = expected_revision + 1
            self.conn.execute(
                """
                INSERT INTO supplier_versions
                (supplier_version_id, supplier_id, revision, source_object_id,
                 source_hash, compiled_artifact_object_id, compiled_artifact_hash,
                 manifest_hash, adapter_contract_version, worker_protocol_version,
                 worker_runtime_version, compiler_name, compiler_version,
                 compiler_options_hash, helper_api_version, built_in, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    supplier_version_id,
                    supplier_id,
                    revision,
                    source_object_id,
                    source_hash,
                    compiled_artifact_object_id,
                    compiled_artifact_hash,
                    manifest_hash,
                    adapter_contract_version,
                    worker_protocol_version,
                    worker_runtime_version,
                    compiler_name,
                    compiler_version,
                    compiler_options_hash,
                    helper_api_version,
                    int(built_in),
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE suppliers
                SET current_supplier_version_id = ?, revision = ?, updated_at = ?
                WHERE supplier_id = ?
                """,
                (supplier_version_id, revision, created_at, supplier_id),
            )
        return self.get_supplier_version(supplier_version_id)

    def get_supplier_version(self, supplier_version_id):
        row = self.conn.execute(
            "SELECT * FROM supplier_versions WHERE supplier_version_id = ?",
            (supplier_version_id,),
        ).fetchone()
        return None if row is None else SupplierVersionRecord(**dict(row))

    def replace_supplier_config(
        self, supplier_id, *, config_object_id, config_hash, expected_revision
    ):
        config_revision_id = uuid.uuid4().hex
        created_at = now_iso()
        with self.conn:
            supplier = self.get_supplier(supplier_id)
            if supplier is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            if supplier.config_revision != expected_revision:
                raise RevisionConflict("supplier config revision conflict")
            revision = expected_revision + 1
            self.conn.execute(
                """
                INSERT INTO supplier_config_revisions
                (config_revision_id, supplier_id, revision, config_object_id,
                 config_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    config_revision_id,
                    supplier_id,
                    revision,
                    config_object_id,
                    config_hash,
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE suppliers
                SET current_config_revision_id = ?, config_revision = ?, updated_at = ?
                WHERE supplier_id = ?
                """,
                (config_revision_id, revision, created_at, supplier_id),
            )
        return self.get_config_revision(config_revision_id)

    def get_config_revision(self, config_revision_id):
        row = self.conn.execute(
            "SELECT * FROM supplier_config_revisions WHERE config_revision_id = ?",
            (config_revision_id,),
        ).fetchone()
        return None if row is None else ConfigRevisionRecord(**dict(row))

    def update_supplier(
        self, supplier_id, *, display_name=None, enabled=None, expected_revision
    ):
        updated_at = now_iso()
        cursor = self.conn.execute(
            """
            UPDATE suppliers
            SET display_name = COALESCE(?, display_name),
                enabled = COALESCE(?, enabled),
                revision = revision + 1,
                updated_at = ?
            WHERE supplier_id = ? AND revision = ?
            """,
            (
                display_name,
                None if enabled is None else int(enabled),
                updated_at,
                supplier_id,
                expected_revision,
            ),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            if self.get_supplier(supplier_id) is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            raise RevisionConflict("supplier revision conflict")
        return self.get_supplier(supplier_id)

    def restore_builtin_supplier_version(self, supplier_id, *, expected_revision):
        supplier = self.get_supplier(supplier_id)
        if supplier is None:
            raise NotFound("supplier not found: %s" % supplier_id)
        if supplier.revision != expected_revision:
            raise RevisionConflict("supplier revision conflict")
        row = self.conn.execute(
            """
            SELECT supplier_version_id
            FROM supplier_versions
            WHERE supplier_id = ? AND built_in = 1
            ORDER BY revision DESC
            LIMIT 1
            """,
            (supplier_id,),
        ).fetchone()
        if row is None:
            raise NotFound("built-in supplier version not found")
        self.conn.execute(
            """
            UPDATE suppliers
            SET current_supplier_version_id = ?, revision = ?, updated_at = ?
            WHERE supplier_id = ?
            """,
            (row["supplier_version_id"], expected_revision + 1, now_iso(), supplier_id),
        )
        self.conn.commit()
        return self.get_supplier(supplier_id)

    def get_supplier_creation_request(self, idempotency_key):
        return self.conn.execute(
            "SELECT * FROM supplier_creation_requests WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()

    def record_supplier_creation_request(self, idempotency_key, request_hash, supplier_id):
        self.conn.execute(
            """
            INSERT INTO supplier_creation_requests
            (idempotency_key, request_hash, supplier_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (idempotency_key, request_hash, supplier_id, now_iso()),
        )
        self.conn.commit()

    def create_supplier_idempotent(
        self, *, slug, display_name, idempotency_key, request_hash
    ):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.get_supplier_creation_request(idempotency_key)
            if replay:
                if replay["request_hash"] != request_hash:
                    raise RevisionConflict("supplier creation idempotency conflict")
                self.conn.commit()
                return self.get_supplier(replay["supplier_id"]), False
            if self.conn.execute(
                "SELECT 1 FROM suppliers WHERE slug = ?", (slug,)
            ).fetchone():
                raise ValueError("supplier slug already exists: %s" % slug)
            supplier_id = uuid.uuid4().hex
            config_revision_id = uuid.uuid4().hex
            created_at = now_iso()
            self.conn.execute(
                """
                INSERT INTO suppliers
                (supplier_id, slug, display_name, source, enabled,
                 current_config_revision_id, revision, config_revision,
                 credential_revision, created_at, updated_at)
                VALUES (?, ?, ?, 'custom', 1, ?, 1, 1, 0, ?, ?)
                """,
                (supplier_id, slug, display_name, config_revision_id, created_at, created_at),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_config_revisions
                (config_revision_id, supplier_id, revision, config_object_id,
                 config_hash, created_at)
                VALUES (?, ?, 1, '', '', ?)
                """,
                (config_revision_id, supplier_id, created_at),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_creation_requests
                (idempotency_key, request_hash, supplier_id, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (idempotency_key, request_hash, supplier_id, created_at),
            )
            self.conn.commit()
            return self.get_supplier(supplier_id), True
        except Exception:
            self.conn.rollback()
            raise

    def _ensure_column(self, table_name, column_name, definition):
        rows = self.conn.execute("PRAGMA table_info(%s)" % table_name).fetchall()
        if any(row["name"] == column_name for row in rows):
            return
        self.conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table_name, column_name, definition))

    def _normalize_current_asset_bindings(self):
        self.conn.execute(
            """
            WITH ranked AS (
              SELECT
                binding_id,
                ROW_NUMBER() OVER (
                  PARTITION BY project_id, chapter_id, target_type, target_id, role
                  ORDER BY created_at DESC, binding_id DESC
                ) AS current_rank
              FROM asset_bindings
              WHERE is_current = 1
            )
            UPDATE asset_bindings
            SET is_current = 0
            WHERE binding_id IN (
              SELECT binding_id FROM ranked WHERE current_rank > 1
            )
            """
        )

    def _backfill_asset_binding_scope(self):
        self.conn.execute(
            """
            UPDATE asset_bindings
            SET
              project_id = (
                SELECT assets.project_id FROM assets WHERE assets.asset_id = asset_bindings.asset_id
              ),
              chapter_id = (
                SELECT assets.chapter_id FROM assets WHERE assets.asset_id = asset_bindings.asset_id
              )
            WHERE project_id = '' OR chapter_id = ''
            """
        )

    def create_project(
        self,
        *,
        name,
        description="",
        series_canon="",
        characters_context="",
        production_brief="",
    ):
        created_at = now_iso()
        project_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO projects
            (project_id, name, description, series_canon, characters_context,
             production_brief, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                name,
                description,
                series_canon,
                characters_context,
                production_brief,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_project(project_id)

    def create_chapter(self, project_id, title, position):
        created_at = now_iso()
        chapter_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO chapters
            (chapter_id, project_id, title, position, current_source_revision_id,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, '', ?, ?)
            """,
            (chapter_id, project_id, title, position, created_at, created_at),
        )
        self.conn.commit()
        return self.get_chapter(chapter_id)

    def create_source_revision(self, chapter_id, content):
        object_id = self.runtime.write_text_object(content)
        created_at = now_iso()
        source_revision_id = uuid.uuid4().hex
        with self.conn:
            row = self.conn.execute(
                """
                SELECT COALESCE(MAX(number), 0) + 1 AS n
                FROM chapter_source_revisions
                WHERE chapter_id = ?
                """,
                (chapter_id,),
            ).fetchone()
            self.conn.execute(
                """
                INSERT INTO chapter_source_revisions
                (source_revision_id, chapter_id, number, object_id, content_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source_revision_id, chapter_id, int(row["n"]), object_id, object_id, created_at),
            )
            self.conn.execute(
                """
                UPDATE chapters
                SET current_source_revision_id = ?, updated_at = ?
                WHERE chapter_id = ?
                """,
                (source_revision_id, created_at, chapter_id),
            )
        return self.get_source_revision(source_revision_id)

    def get_project(self, project_id):
        row = self.conn.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return None if row is None else ProjectRecord(**dict(row))

    def get_chapter(self, chapter_id):
        row = self.conn.execute("SELECT * FROM chapters WHERE chapter_id = ?", (chapter_id,)).fetchone()
        return None if row is None else ChapterRecord(**dict(row))

    def list_chapters(self, project_id):
        if self.get_project(project_id) is None:
            raise NotFound("project not found: %s" % project_id)
        rows = self.conn.execute(
            """
            SELECT *
            FROM chapters
            WHERE project_id = ?
            ORDER BY position ASC, created_at ASC, chapter_id ASC
            """,
            (project_id,),
        ).fetchall()
        return [ChapterRecord(**dict(row)) for row in rows]

    def get_source_revision(self, source_revision_id):
        row = self.conn.execute(
            "SELECT * FROM chapter_source_revisions WHERE source_revision_id = ?",
            (source_revision_id,),
        ).fetchone()
        return None if row is None else ChapterSourceRevisionRecord(**dict(row))

    def create_production_profile(self, *, project_id, chapter_id, profile_type, name, payload):
        created_at = now_iso()
        profile_id = uuid.uuid4().hex
        payload_object_id = self.runtime.write_text_object(_normalized_json(payload))
        self.conn.execute(
            """
            INSERT INTO production_profiles
            (profile_id, project_id, chapter_id, profile_type, name,
             payload_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                project_id,
                chapter_id,
                profile_type,
                name,
                payload_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_production_profile(profile_id)

    def get_production_profile(self, profile_id):
        row = self.conn.execute(
            "SELECT * FROM production_profiles WHERE profile_id = ?",
            (profile_id,),
        ).fetchone()
        return None if row is None else ProductionProfileRecord(**dict(row))

    def list_production_profiles(self, project_id, *, chapter_id=None, profile_type=None):
        conditions = ["project_id = ?"]
        params = [project_id]
        if chapter_id is not None:
            conditions.append("chapter_id = ?")
            params.append(chapter_id)
        if profile_type is not None:
            conditions.append("profile_type = ?")
            params.append(profile_type)
        rows = self.conn.execute(
            """
            SELECT *
            FROM production_profiles
            WHERE %s
            ORDER BY chapter_id ASC, profile_type ASC, name ASC, created_at ASC, profile_id ASC
            """
            % " AND ".join(conditions),
            params,
        ).fetchall()
        return [ProductionProfileRecord(**dict(row)) for row in rows]

    def update_production_profile_payload(self, profile_id, *, name, payload):
        updated_at = now_iso()
        payload_object_id = self.runtime.write_text_object(_normalized_json(payload))
        cursor = self.conn.execute(
            """
            UPDATE production_profiles
            SET name = ?, payload_object_id = ?, updated_at = ?
            WHERE profile_id = ?
            """,
            (name, payload_object_id, updated_at, profile_id),
        )
        self.conn.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_production_profile(profile_id)

    def delete_production_profile(self, profile_id):
        cursor = self.conn.execute(
            "DELETE FROM production_profiles WHERE profile_id = ?",
            (profile_id,),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def create_uploaded_asset(self, *, project_id, chapter_id, asset_type, name, data, media_type, metadata):
        created_at = now_iso()
        asset_id = uuid.uuid4().hex
        object_id = self.runtime.write_bytes_object(data)
        metadata_object_id = self.runtime.write_text_object(_normalized_json(metadata))
        self.conn.execute(
            """
            INSERT INTO assets
            (asset_id, project_id, chapter_id, asset_type, name, object_id,
             media_type, width, height, status, source_type, source_job_id,
             metadata_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'draft', 'upload', '', ?, ?, ?)
            """,
            (
                asset_id,
                project_id,
                chapter_id,
                asset_type,
                name,
                object_id,
                media_type,
                metadata_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_asset(asset_id)

    def create_generated_asset(
        self,
        *,
        project_id,
        chapter_id,
        asset_type,
        name,
        data,
        media_type,
        source_job_id,
        metadata,
    ):
        created_at = now_iso()
        asset_id = uuid.uuid4().hex
        object_id = self.runtime.write_bytes_object(data)
        metadata_object_id = self.runtime.write_text_object(_normalized_json(metadata))
        self.conn.execute(
            """
            INSERT INTO assets
            (asset_id, project_id, chapter_id, asset_type, name, object_id,
             media_type, width, height, status, source_type, source_job_id,
             metadata_object_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 'draft', 'agnes', ?, ?, ?, ?)
            """,
            (
                asset_id,
                project_id,
                chapter_id,
                asset_type,
                name,
                object_id,
                media_type,
                source_job_id,
                metadata_object_id,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_asset(asset_id)

    def get_asset(self, asset_id):
        row = self.conn.execute(
            "SELECT * FROM assets WHERE asset_id = ?",
            (asset_id,),
        ).fetchone()
        return None if row is None else AssetRecord(**dict(row))

    def list_assets_for_chapter(self, chapter_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM assets
            WHERE chapter_id = ?
            ORDER BY created_at ASC, asset_id ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [AssetRecord(**dict(row)) for row in rows]

    def list_asset_bindings(self, asset_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM asset_bindings
            WHERE asset_id = ?
            ORDER BY is_current DESC, created_at ASC, binding_id ASC
            """,
            (asset_id,),
        ).fetchall()
        return [AssetBindingRecord(**dict(row)) for row in rows]

    def update_asset_status(self, asset_id, status, *, metadata=None):
        updated_at = now_iso()
        metadata_object_id = None if metadata is None else self.runtime.write_text_object(_normalized_json(metadata))
        if metadata_object_id is not None:
            cursor = self.conn.execute(
                """
                UPDATE assets
                SET status = ?, metadata_object_id = ?, updated_at = ?
                WHERE asset_id = ?
                """,
                (status, metadata_object_id, updated_at, asset_id),
            )
        else:
            cursor = self.conn.execute(
                """
                UPDATE assets
                SET status = ?, updated_at = ?
                WHERE asset_id = ?
                """,
                (status, updated_at, asset_id),
            )
        self.conn.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_asset(asset_id)

    def create_asset_binding(self, *, asset_id, target_type, target_id, role, is_current=False):
        asset = self.get_asset(asset_id)
        if asset is None:
            return None
        created_at = now_iso()
        binding_id = uuid.uuid4().hex
        current_value = 1 if is_current else 0
        with self.conn:
            if current_value:
                self.conn.execute(
                    """
                    UPDATE asset_bindings
                    SET is_current = 0
                    WHERE project_id = ? AND chapter_id = ?
                      AND target_type = ? AND target_id = ? AND role = ? AND is_current = 1
                    """,
                    (asset.project_id, asset.chapter_id, target_type, target_id, role),
                )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO asset_bindings
                (binding_id, asset_id, project_id, chapter_id, target_type, target_id, role, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    binding_id,
                    asset_id,
                    asset.project_id,
                    asset.chapter_id,
                    target_type,
                    target_id,
                    role,
                    current_value,
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE asset_bindings
                SET is_current = ?, project_id = ?, chapter_id = ?
                WHERE asset_id = ? AND target_type = ? AND target_id = ? AND role = ?
                """,
                (current_value, asset.project_id, asset.chapter_id, asset_id, target_type, target_id, role),
            )
        row = self.conn.execute(
            """
            SELECT *
            FROM asset_bindings
            WHERE asset_id = ? AND target_type = ? AND target_id = ? AND role = ?
            """,
            (asset_id, target_type, target_id, role),
        ).fetchone()
        return AssetBindingRecord(**dict(row))

    def asset_has_current_binding(self, asset_id):
        row = self.conn.execute(
            """
            SELECT 1
            FROM asset_bindings
            WHERE asset_id = ? AND is_current = 1
            LIMIT 1
            """,
            (asset_id,),
        ).fetchone()
        return row is not None

    def clear_current_asset_bindings(self, asset_id):
        self.conn.execute(
            """
            UPDATE asset_bindings
            SET is_current = 0
            WHERE asset_id = ? AND is_current = 1
            """,
            (asset_id,),
        )
        self.conn.commit()

    def asset_bindings_for_requirement(self, *, project_id, chapter_id, target_type, target_id, role, asset_type):
        rows = self.conn.execute(
            """
            SELECT
              assets.asset_id,
              assets.asset_type,
              assets.status,
              assets.chapter_id,
              asset_bindings.binding_id,
              asset_bindings.target_type,
              asset_bindings.target_id,
              asset_bindings.role,
              asset_bindings.is_current,
              asset_bindings.created_at
            FROM asset_bindings
            JOIN assets ON assets.asset_id = asset_bindings.asset_id
            WHERE assets.project_id = ?
              AND asset_bindings.target_type = ?
              AND asset_bindings.target_id = ?
              AND asset_bindings.role = ?
              AND assets.asset_type = ?
              AND assets.chapter_id IN ('', ?)
            ORDER BY asset_bindings.is_current DESC, assets.updated_at DESC, asset_bindings.created_at DESC, assets.asset_id ASC
            """,
            (project_id, target_type, target_id, role, asset_type, chapter_id),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_asset_requirement_set(self, *, chapter_id, storyboard_revision_id, payload):
        created_at = now_iso()
        requirement_set_id = uuid.uuid4().hex
        content_text = _normalized_json(payload)
        content_object_id = self.runtime.write_text_object(content_text)
        content_hash = content_object_id
        self.conn.execute(
            """
            INSERT INTO asset_requirement_sets
            (requirement_set_id, chapter_id, storyboard_revision_id, content_object_id, content_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (requirement_set_id, chapter_id, storyboard_revision_id, content_object_id, content_hash, created_at),
        )
        self.conn.commit()
        return {
            "requirement_set_id": requirement_set_id,
            "chapter_id": chapter_id,
            "storyboard_revision_id": storyboard_revision_id,
            "content_object_id": content_object_id,
            "content_hash": content_hash,
            "created_at": created_at,
            "payload": payload,
        }

    def latest_asset_requirement_set(self, chapter_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM asset_requirement_sets
            WHERE chapter_id = ?
            ORDER BY created_at DESC, requirement_set_id DESC
            LIMIT 1
            """,
            (chapter_id,),
        ).fetchone()
        if row is None:
            return None
        data = dict(row)
        data["payload"] = json.loads(self.runtime.read_text(data["content_object_id"]))
        return data

    def create_generation_job(
        self,
        *,
        provider,
        job_type,
        project_id,
        chapter_id,
        shot_id,
        prompt_revision_id,
        idempotency_key,
        request_hash,
        request_object_id,
        attempt_number,
    ):
        existing = self._generation_job_by_idempotency(provider, idempotency_key)
        if existing is not None:
            return existing
        created_at = now_iso()
        job_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO generation_jobs
            (job_id, provider, job_type, project_id, chapter_id, shot_id,
             prompt_revision_id, provider_job_id, provider_result_id,
             internal_status, idempotency_key, request_hash, request_object_id,
             response_object_id, attempt_number, error_code, error_message,
             submitted_at, next_poll_at, completed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, '', '', 'draft', ?, ?, ?, '', ?, '', '', '', '', '', ?, ?)
            """,
            (
                job_id,
                provider,
                job_type,
                project_id,
                chapter_id,
                shot_id,
                prompt_revision_id,
                idempotency_key,
                request_hash,
                request_object_id,
                attempt_number,
                created_at,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_generation_job(job_id)

    def get_generation_job(self, job_id):
        row = self.conn.execute("SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else GenerationJobRecord(**dict(row))

    def _generation_job_by_idempotency(self, provider, idempotency_key):
        row = self.conn.execute(
            """
            SELECT *
            FROM generation_jobs
            WHERE provider = ? AND idempotency_key = ?
            """,
            (provider, idempotency_key),
        ).fetchone()
        return None if row is None else GenerationJobRecord(**dict(row))

    def list_generation_jobs_for_chapter(self, chapter_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM generation_jobs
            WHERE chapter_id = ?
            ORDER BY created_at ASC, job_id ASC
            """,
            (chapter_id,),
        ).fetchall()
        return [GenerationJobRecord(**dict(row)) for row in rows]

    def transition_generation_job(
        self,
        job_id,
        next_status,
        *,
        error_code="",
        error_message="",
        next_poll_at=None,
        provider_result_id=None,
        response_object_id=None,
    ):
        current = self.get_generation_job(job_id)
        if current is None:
            return None
        allowed = GENERATION_JOB_TRANSITIONS[current.internal_status]
        if next_status not in allowed:
            raise ValueError(
                "invalid generation job transition: %s -> %s"
                % (current.internal_status, next_status)
            )
        updated_at = now_iso()
        submitted_at = current.submitted_at
        completed_at = current.completed_at
        if current.internal_status == "queued" and next_status == "submitting":
            submitted_at = updated_at
        if next_status in {"completed", "failed", "cancelled"}:
            completed_at = updated_at
        self.conn.execute(
            """
            UPDATE generation_jobs
            SET internal_status = ?,
                error_code = ?,
                error_message = ?,
                next_poll_at = ?,
                provider_result_id = ?,
                response_object_id = ?,
                submitted_at = ?,
                completed_at = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (
                next_status,
                error_code,
                error_message,
                current.next_poll_at if next_poll_at is None else next_poll_at,
                current.provider_result_id if provider_result_id is None else provider_result_id,
                current.response_object_id if response_object_id is None else response_object_id,
                submitted_at,
                completed_at,
                updated_at,
                job_id,
            ),
        )
        self.conn.commit()
        return self.get_generation_job(job_id)

    def attach_generation_provider_job(self, job_id, *, provider_job_id, response_object_id):
        current = self.get_generation_job(job_id)
        if current is None:
            return None
        if current.internal_status != "submitting":
            raise ValueError(
                "invalid generation job transition: %s -> submitted"
                % current.internal_status
            )
        updated_at = now_iso()
        self.conn.execute(
            """
            UPDATE generation_jobs
            SET internal_status = 'submitted',
                provider_job_id = ?,
                response_object_id = ?,
                updated_at = ?
            WHERE job_id = ?
            """,
            (provider_job_id, response_object_id, updated_at, job_id),
        )
        self.conn.commit()
        return self.get_generation_job(job_id)

    def next_generation_attempt_number(self, *, chapter_id, shot_id, provider, job_type):
        row = self.conn.execute(
            """
            SELECT COALESCE(MAX(attempt_number), 0) + 1 AS next_attempt
            FROM generation_jobs
            WHERE chapter_id = ? AND shot_id = ? AND provider = ? AND job_type = ?
            """,
            (chapter_id, shot_id, provider, job_type),
        ).fetchone()
        return int(row["next_attempt"])

    def create_generation_result(
        self,
        *,
        job_id,
        chapter_id,
        shot_id,
        object_id,
        media_type,
        source_url,
        metadata_object_id,
        source_url_state="source_url_active",
    ):
        created_at = now_iso()
        result_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO generation_results
            (result_id, job_id, chapter_id, shot_id, object_id, media_type,
             source_url, source_url_state, metadata_object_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result_id,
                job_id,
                chapter_id,
                shot_id,
                object_id,
                media_type,
                source_url,
                source_url_state,
                metadata_object_id,
                created_at,
            ),
        )
        self.conn.commit()
        return self.get_generation_result(result_id)

    def complete_generation_job_with_result(
        self,
        *,
        job_id,
        object_id,
        media_type,
        source_url,
        metadata_object_id,
        source_url_state="source_url_active",
    ):
        current = self.get_generation_job(job_id)
        if current is None:
            return None
        if current.internal_status not in {"submitted", "polling"}:
            raise ValueError(
                "invalid generation job transition: %s -> completed"
                % current.internal_status
            )
        created_at = now_iso()
        result_id = uuid.uuid4().hex
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO generation_results
                (result_id, job_id, chapter_id, shot_id, object_id, media_type,
                 source_url, source_url_state, metadata_object_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    current.job_id,
                    current.chapter_id,
                    current.shot_id,
                    object_id,
                    media_type,
                    source_url,
                    source_url_state,
                    metadata_object_id,
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE generation_jobs
                SET internal_status = 'completed',
                    provider_result_id = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (result_id, created_at, created_at, current.job_id),
            )
        return self.get_generation_job(current.job_id)

    def get_generation_result(self, result_id):
        row = self.conn.execute(
            "SELECT * FROM generation_results WHERE result_id = ?",
            (result_id,),
        ).fetchone()
        return None if row is None else GenerationResultRecord(**dict(row))

    def list_generation_results_for_shot(self, chapter_id, shot_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM generation_results
            WHERE chapter_id = ? AND shot_id = ?
            ORDER BY created_at ASC, result_id ASC
            """,
            (chapter_id, shot_id),
        ).fetchall()
        return [GenerationResultRecord(**dict(row)) for row in rows]

    def select_generation_result(self, chapter_id, shot_id, result_id):
        selected_at = now_iso()
        with self.conn:
            self.conn.execute(
                """
                INSERT INTO shot_result_selections
                (chapter_id, shot_id, result_id, selected_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chapter_id, shot_id)
                DO UPDATE SET result_id = excluded.result_id,
                              selected_at = excluded.selected_at
                """,
                (chapter_id, shot_id, result_id, selected_at),
            )
        return self.current_generation_result_selection(chapter_id, shot_id)

    def current_generation_result_selection(self, chapter_id, shot_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM shot_result_selections
            WHERE chapter_id = ? AND shot_id = ?
            """,
            (chapter_id, shot_id),
        ).fetchone()
        return None if row is None else ShotResultSelectionRecord(**dict(row))

    def create_result_review(self, *, result_id, decision, failure_category="", note=""):
        created_at = now_iso()
        review_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO result_reviews
            (review_id, result_id, decision, failure_category, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (review_id, result_id, decision, failure_category, note, created_at),
        )
        self.conn.commit()
        return self.get_result_review(review_id)

    def get_result_review(self, review_id):
        row = self.conn.execute(
            "SELECT * FROM result_reviews WHERE review_id = ?",
            (review_id,),
        ).fetchone()
        return None if row is None else ResultReviewRecord(**dict(row))

    def create_rerun_record(self, *, source_job_id, new_job_id, overrides_object_id):
        created_at = now_iso()
        rerun_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO rerun_records
            (rerun_id, source_job_id, new_job_id, overrides_object_id, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (rerun_id, source_job_id, new_job_id, overrides_object_id, created_at),
        )
        self.conn.commit()
        return self.get_rerun_record(rerun_id)

    def get_rerun_record(self, rerun_id):
        row = self.conn.execute(
            "SELECT * FROM rerun_records WHERE rerun_id = ?",
            (rerun_id,),
        ).fetchone()
        return None if row is None else RerunRecord(**dict(row))

def _normalized_json(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
