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
    CredentialVersionRecord,
    RevisionConflict,
    SupplierRecord,
    SupplierModelRecord,
    SupplierModelRevisionRecord,
    ProjectModelBindingRecord,
    ModelNameConflict,
    ModelReferenced,
    stable_builtin_model_id,
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
M6B_MODEL_CATALOG_MIGRATION_ID = "m6b_model_catalog_binding_v1"
M6C_ADAPTER_CUTOVER_MIGRATION_ID = "m6c_adapter_cutover_v1"
M6C_SUBMISSION_STATE_MIGRATION_ID = "m6c_submission_state_v2"
STREAMING_SCRIPT_GENERATION_MIGRATION_ID = "streaming_script_generation_v1"
BUILTIN_SUPPLIERS = (
    ("agnes", "Agnes"),
    ("anthropic", "Anthropic"),
    ("deepseek", "DeepSeek"),
    ("openai", "OpenAI"),
    ("xai", "xAI Grok"),
)


class ScriptGenerationConflict(RuntimeError):
    pass


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
            CREATE TABLE IF NOT EXISTS generation_submission_attempts (
              attempt_id TEXT PRIMARY KEY,
              job_id TEXT NOT NULL UNIQUE REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
              attempt_number INTEGER NOT NULL,
              state TEXT NOT NULL CHECK (state IN ('prepared','submitting','accepted','committed','unknown_outcome','failed')),
              provider_job_id TEXT NOT NULL DEFAULT '',
              evidence_object_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_text_runs (
              run_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL,
              operation_key TEXT NOT NULL,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              snapshot_hash TEXT NOT NULL REFERENCES execution_snapshots(snapshot_hash) ON DELETE RESTRICT,
              snapshot_object_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              request_object_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('prepared','completed','failed')),
              result_object_id TEXT NOT NULL DEFAULT '',
              evidence_object_id TEXT NOT NULL DEFAULT '',
              error_code TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS script_generation_runs (
              run_id TEXT PRIMARY KEY,
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              chapter_id TEXT NOT NULL REFERENCES chapters(chapter_id) ON DELETE RESTRICT,
              source_revision_id TEXT NOT NULL REFERENCES chapter_source_revisions(source_revision_id) ON DELETE RESTRICT,
              runtime_run_id TEXT NOT NULL UNIQUE,
              supplier_text_run_id TEXT NOT NULL DEFAULT '',
              snapshot_hash TEXT NOT NULL DEFAULT '',
              idempotency_key TEXT NOT NULL UNIQUE,
              status TEXT NOT NULL CHECK (status IN ('prepared','submitting','streaming','finalizing','completed','failed','unknown_outcome')),
              last_sequence INTEGER NOT NULL DEFAULT 0,
              character_count INTEGER NOT NULL DEFAULT 0,
              revision_id TEXT NOT NULL DEFAULT '',
              error_code TEXT NOT NULL DEFAULT '',
              evidence_object_id TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS script_generation_runs_status_idx
              ON script_generation_runs(status, created_at, run_id);
            CREATE TABLE IF NOT EXISTS script_generation_events (
              run_id TEXT NOT NULL REFERENCES script_generation_runs(run_id) ON DELETE RESTRICT,
              sequence INTEGER NOT NULL,
              event_type TEXT NOT NULL CHECK (event_type IN ('stage','text_delta','usage','failed','revision_completed')),
              payload_object_id TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              byte_length INTEGER NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY (run_id, sequence)
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
              manifest_object_id TEXT NOT NULL DEFAULT '',
              rate_limit_bucket_key TEXT NOT NULL DEFAULT '',
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
            CREATE TABLE IF NOT EXISTS supplier_models (
              supplier_model_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              current_model_revision_id TEXT NOT NULL DEFAULT '',
              source TEXT NOT NULL CHECK (source IN ('built_in','overlay')),
              enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
              revision INTEGER NOT NULL DEFAULT 1,
              archived_at TEXT NOT NULL DEFAULT '',
              archive_reason TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS supplier_models_supplier_idx
              ON supplier_models(supplier_id, enabled, supplier_model_id);
            CREATE TABLE IF NOT EXISTS supplier_model_revisions (
              model_revision_id TEXT PRIMARY KEY,
              supplier_model_id TEXT NOT NULL REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              revision INTEGER NOT NULL,
              provider_model_name TEXT NOT NULL,
              display_name TEXT NOT NULL,
              capability TEXT NOT NULL CHECK (capability IN ('text','image','video')),
              definition_object_id TEXT NOT NULL,
              definition_hash TEXT NOT NULL,
              created_at TEXT NOT NULL,
              UNIQUE(supplier_model_id, revision)
            );
            CREATE TABLE IF NOT EXISTS project_model_bindings (
              project_id TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE RESTRICT,
              default_text_model_id TEXT REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              default_image_model_id TEXT REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              default_video_model_id TEXT REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              binding_set_revision INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_model_operation_overrides (
              project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
              operation_key TEXT NOT NULL,
              supplier_model_id TEXT NOT NULL REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              PRIMARY KEY(project_id, operation_key)
            );
            CREATE TABLE IF NOT EXISTS execution_snapshots (
              snapshot_hash TEXT PRIMARY KEY,
              snapshot_object_id TEXT NOT NULL UNIQUE,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              supplier_model_id TEXT NOT NULL REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              model_revision_id TEXT NOT NULL REFERENCES supplier_model_revisions(model_revision_id) ON DELETE RESTRICT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS supplier_model_test_runs (
              test_run_id TEXT PRIMARY KEY,
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              supplier_model_id TEXT NOT NULL REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              credential_version_id TEXT NOT NULL,
              snapshot_hash TEXT NOT NULL REFERENCES execution_snapshots(snapshot_hash) ON DELETE RESTRICT,
              snapshot_object_id TEXT NOT NULL,
              capability TEXT NOT NULL CHECK (capability IN ('text','image')),
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              request_object_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK (status IN ('queued','submitting','completed','failed','submission_outcome_unknown')),
              attempt_count INTEGER NOT NULL DEFAULT 0,
              lease_owner TEXT NOT NULL DEFAULT '',
              lease_expires_at TEXT NOT NULL DEFAULT '',
              normalized_result_object_id TEXT NOT NULL DEFAULT '',
              sanitized_evidence_object_id TEXT NOT NULL DEFAULT '',
              content_object_id TEXT NOT NULL DEFAULT '',
              media_type TEXT NOT NULL DEFAULT '',
              byte_size INTEGER NOT NULL DEFAULT 0,
              error_code TEXT NOT NULL DEFAULT '',
              error_message TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              started_at TEXT NOT NULL DEFAULT '',
              finished_at TEXT NOT NULL DEFAULT '',
              UNIQUE(supplier_model_id, capability, idempotency_key)
            );
            CREATE INDEX IF NOT EXISTS supplier_model_test_runs_status_idx
              ON supplier_model_test_runs(status, created_at, test_run_id);
            CREATE INDEX IF NOT EXISTS supplier_model_test_runs_credential_idx
              ON supplier_model_test_runs(credential_version_id, status);
            CREATE TABLE IF NOT EXISTS model_creation_requests (
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              supplier_model_id TEXT NOT NULL REFERENCES supplier_models(supplier_model_id) ON DELETE RESTRICT,
              created_at TEXT NOT NULL,
              PRIMARY KEY(supplier_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS supplier_idempotency_records (
              supplier_id TEXT NOT NULL REFERENCES suppliers(supplier_id) ON DELETE RESTRICT,
              capability TEXT NOT NULL CHECK (capability IN ('text','image','video')),
              idempotency_key TEXT NOT NULL,
              request_hash TEXT NOT NULL,
              existing_id TEXT NOT NULL,
              created_at TEXT NOT NULL,
              PRIMARY KEY(supplier_id, capability, idempotency_key)
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
        self._ensure_column("supplier_versions", "manifest_object_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_versions", "rate_limit_bucket_key", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("suppliers", "model_catalog_revision", "INTEGER NOT NULL DEFAULT 0")
        self._ensure_column("supplier_models", "archived_at", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("supplier_models", "archive_reason", "TEXT NOT NULL DEFAULT ''")
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
        self._apply_model_catalog_binding_migration()
        self._apply_m6c_adapter_cutover_migration()
        self._apply_m6c_submission_state_migration()
        self._apply_streaming_script_generation_migration()
        self.conn.commit()

    def _apply_streaming_script_generation_migration(self):
        if self.conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (STREAMING_SCRIPT_GENERATION_MIGRATION_ID,),
        ).fetchone():
            return
        self.conn.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (STREAMING_SCRIPT_GENERATION_MIGRATION_ID, now_iso()),
        )

    def _apply_m6c_submission_state_migration(self):
        if self.conn.execute("SELECT 1 FROM schema_migrations WHERE migration_id = ?", (M6C_SUBMISSION_STATE_MIGRATION_ID,)).fetchone():
            return
        definition = self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='generation_submission_attempts'").fetchone()
        if definition is not None and "unknown_outcome" not in definition["sql"]:
            self.conn.executescript(
                """
                ALTER TABLE generation_submission_attempts RENAME TO generation_submission_attempts_v1;
                CREATE TABLE generation_submission_attempts (
                  attempt_id TEXT PRIMARY KEY,
                  job_id TEXT NOT NULL UNIQUE REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
                  attempt_number INTEGER NOT NULL,
                  state TEXT NOT NULL CHECK (state IN ('prepared','submitting','accepted','committed','unknown_outcome','failed')),
                  provider_job_id TEXT NOT NULL DEFAULT '',
                  evidence_object_id TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                INSERT INTO generation_submission_attempts
                SELECT attempt_id, job_id, attempt_number,
                       CASE state WHEN 'submitted' THEN 'accepted' WHEN 'unknown' THEN 'unknown_outcome' ELSE state END,
                       provider_job_id, evidence_object_id, created_at, updated_at
                FROM generation_submission_attempts_v1;
                DROP TABLE generation_submission_attempts_v1;
                """
            )
        self.conn.execute("INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)", (M6C_SUBMISSION_STATE_MIGRATION_ID, now_iso()))

    def _apply_m6c_adapter_cutover_migration(self):
        if self.conn.execute("SELECT 1 FROM schema_migrations WHERE migration_id = ?", (M6C_ADAPTER_CUTOVER_MIGRATION_ID,)).fetchone():
            return
        self._ensure_column("generation_jobs", "snapshot_hash", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "snapshot_object_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "resolved_snapshot_object_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "source_job_id", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "rerun_resolution_mode", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "legacy_backfill_state", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("generation_jobs", "legacy_backfill_version", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("rerun_records", "resolution_mode", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("rerun_records", "source_snapshot_hash", "TEXT NOT NULL DEFAULT ''")
        self._ensure_column("rerun_records", "new_snapshot_hash", "TEXT NOT NULL DEFAULT ''")
        self.conn.execute("INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)", (M6C_ADAPTER_CUTOVER_MIGRATION_ID, now_iso()))

    def _apply_model_catalog_binding_migration(self):
        if self.conn.execute(
            "SELECT 1 FROM schema_migrations WHERE migration_id = ?",
            (M6B_MODEL_CATALOG_MIGRATION_ID,),
        ).fetchone():
            return
        for supplier in self.list_suppliers():
            if not supplier.current_supplier_version_id:
                continue
            version = self.get_supplier_version(supplier.current_supplier_version_id)
            if version is None:
                continue
            try:
                source = self.runtime.read_text(version.source_object_id)
                vendor = self._read_migration_vendor(source)
            except Exception as exc:
                raise RuntimeError("M6B_MANIFEST_MIGRATION_FAILED") from exc
            manifest_text = json.dumps(
                vendor,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            manifest_object_id = self.runtime.write_text_object(manifest_text)
            self.conn.execute(
                """
                UPDATE supplier_versions
                SET manifest_object_id = ?, rate_limit_bucket_key = ?
                WHERE supplier_version_id = ?
                """,
                (
                    manifest_object_id,
                    vendor["rateLimitBucketKey"],
                    version.supplier_version_id,
                ),
            )
            self._sync_manifest_models_locked(supplier.supplier_id, vendor.get("models", []))
        self.conn.execute(
            "INSERT INTO schema_migrations (migration_id, applied_at) VALUES (?, ?)",
            (M6B_MODEL_CATALOG_MIGRATION_ID, now_iso()),
        )

    def _read_migration_vendor(self, source):
        prefix = "export const vendor = "
        stripped = source.strip()
        if stripped.startswith(prefix) and stripped.endswith(";"):
            try:
                return json.loads(stripped[len(prefix) : -1])
            except json.JSONDecodeError:
                pass
        from .suppliers.compiler import compile_supplier

        return compile_supplier(source, runtime_store=self.runtime).vendor

    def _sync_manifest_models_locked(self, supplier_id, declarations):
        changed = False
        active_ids = set()
        created_at = now_iso()
        for declaration in declarations:
            capability = str(declaration.get("capability") or "")
            provider_name = str(
                declaration.get("providerModelName")
                or declaration.get("provider_model_name")
                or ""
            )
            display_name = str(
                declaration.get("displayName")
                or declaration.get("display_name")
                or provider_name
            )
            if capability not in {"text", "image", "video"} or not provider_name:
                raise ValueError("invalid supplier model declaration")
            declared_id = declaration.get("supplierModelId") or declaration.get("supplier_model_id")
            try:
                supplier_model_id = uuid.UUID(str(declared_id)).hex if declared_id else ""
            except ValueError:
                supplier_model_id = ""
            if not supplier_model_id:
                declaration_key = str(declared_id or "%s:%s" % (capability, provider_name))
                supplier_model_id = stable_builtin_model_id(supplier_id, declaration_key)
            active_ids.add(supplier_model_id)
            normalized_declaration = dict(declaration)
            normalized_declaration["supplierModelId"] = supplier_model_id
            definition_text = json.dumps(
                normalized_declaration,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            definition_object_id = self.runtime.write_text_object(definition_text)
            definition_hash = hashlib.sha256(definition_text.encode("utf-8")).hexdigest()
            model = self.get_supplier_model(supplier_model_id)
            duplicate = self.find_active_model_name(
                supplier_id, capability, provider_name, exclude_id=supplier_model_id
            )
            if duplicate:
                raise ModelNameConflict("MODEL_NAME_CONFLICT")
            if model is None:
                model_revision_id = uuid.uuid4().hex
                self.conn.execute(
                    """
                    INSERT INTO supplier_models
                    (supplier_model_id, supplier_id, current_model_revision_id, source,
                     enabled, revision, created_at, updated_at)
                    VALUES (?, ?, ?, 'built_in', 1, 1, ?, ?)
                    """,
                    (supplier_model_id, supplier_id, model_revision_id, created_at, created_at),
                )
                self.conn.execute(
                    """
                    INSERT INTO supplier_model_revisions
                    (model_revision_id, supplier_model_id, revision, provider_model_name,
                     display_name, capability, definition_object_id, definition_hash, created_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model_revision_id,
                        supplier_model_id,
                        provider_name,
                        display_name,
                        capability,
                        definition_object_id,
                        definition_hash,
                        created_at,
                    ),
                )
                changed = True
                continue
            if model.source != "built_in":
                raise ModelNameConflict("MODEL_IDENTITY_CONFLICT")
            current = self.get_supplier_model_revision(model.current_model_revision_id)
            if (
                current.provider_model_name != provider_name
                or current.display_name != display_name
                or current.capability != capability
                or current.definition_hash != definition_hash
                or not model.enabled
            ):
                next_revision = model.revision + 1
                model_revision_id = uuid.uuid4().hex
                self.conn.execute(
                    """
                    INSERT INTO supplier_model_revisions
                    (model_revision_id, supplier_model_id, revision, provider_model_name,
                     display_name, capability, definition_object_id, definition_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        model_revision_id,
                        supplier_model_id,
                        next_revision,
                        provider_name,
                        display_name,
                        capability,
                        definition_object_id,
                        definition_hash,
                        created_at,
                    ),
                )
                self.conn.execute(
                    """
                    UPDATE supplier_models
                    SET current_model_revision_id = ?, enabled = 1,
                        revision = ?, updated_at = ?
                    WHERE supplier_model_id = ?
                    """,
                    (model_revision_id, next_revision, created_at, supplier_model_id),
                )
                changed = True
        for model in self.list_supplier_models(supplier_id):
            if model.source == "built_in" and model.supplier_model_id not in active_ids and model.enabled:
                self.conn.execute(
                    """
                    UPDATE supplier_models SET enabled = 0, revision = revision + 1, updated_at = ?
                    WHERE supplier_model_id = ?
                    """,
                    (created_at, model.supplier_model_id),
                )
                changed = True
        if changed:
            self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ?
                """,
                (created_at, supplier_id),
            )

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

    def create_supplier_model(
        self,
        supplier_id,
        *,
        supplier_model_id,
        source,
        provider_model_name,
        display_name,
        capability,
        definition,
        expected_catalog_revision,
    ):
        normalized = json.dumps(
            definition, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        definition_object_id = self.runtime.write_text_object(normalized)
        definition_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        model_revision_id = uuid.uuid4().hex
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            supplier = self.get_supplier(supplier_id)
            if supplier is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            if supplier.model_catalog_revision != expected_catalog_revision:
                raise RevisionConflict("model catalog revision conflict")
            if self.find_active_model_name(supplier_id, capability, provider_model_name):
                raise ModelNameConflict("MODEL_NAME_CONFLICT")
            self.conn.execute(
                """
                INSERT INTO supplier_models
                (supplier_model_id, supplier_id, current_model_revision_id, source,
                 enabled, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (supplier_model_id, supplier_id, model_revision_id, source, created_at, created_at),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_model_revisions
                (model_revision_id, supplier_model_id, revision, provider_model_name,
                 display_name, capability, definition_object_id, definition_hash, created_at)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_revision_id,
                    supplier_model_id,
                    provider_model_name,
                    display_name,
                    capability,
                    definition_object_id,
                    definition_hash,
                    created_at,
                ),
            )
            cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (created_at, supplier_id, expected_catalog_revision),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict("model catalog revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id)

    def create_supplier_model_idempotent(
        self,
        supplier_id,
        *,
        supplier_model_id,
        source,
        provider_model_name,
        display_name,
        capability,
        definition,
        expected_catalog_revision,
        idempotency_key,
        request_hash,
    ):
        normalized = json.dumps(
            definition, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        definition_object_id = self.runtime.write_text_object(normalized)
        definition_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        model_revision_id = uuid.uuid4().hex
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.conn.execute(
                "SELECT * FROM model_creation_requests WHERE supplier_id = ? AND idempotency_key = ?",
                (supplier_id, idempotency_key),
            ).fetchone()
            if replay:
                if replay["request_hash"] != request_hash:
                    raise RevisionConflict("model creation idempotency conflict")
                self.conn.commit()
                return self.get_supplier_model(replay["supplier_model_id"]), False
            supplier = self.get_supplier(supplier_id)
            if supplier is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            if supplier.model_catalog_revision != expected_catalog_revision:
                raise RevisionConflict("model catalog revision conflict")
            if self.find_active_model_name(supplier_id, capability, provider_model_name):
                raise ModelNameConflict("MODEL_NAME_CONFLICT")
            self.conn.execute(
                """
                INSERT INTO supplier_models
                (supplier_model_id, supplier_id, current_model_revision_id, source,
                 enabled, revision, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (supplier_model_id, supplier_id, model_revision_id, source, created_at, created_at),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_model_revisions
                (model_revision_id, supplier_model_id, revision, provider_model_name,
                 display_name, capability, definition_object_id, definition_hash, created_at)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_revision_id,
                    supplier_model_id,
                    provider_model_name,
                    display_name,
                    capability,
                    definition_object_id,
                    definition_hash,
                    created_at,
                ),
            )
            cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (created_at, supplier_id, expected_catalog_revision),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict("model catalog revision conflict")
            self.conn.execute(
                """
                INSERT INTO model_creation_requests
                (supplier_id, idempotency_key, request_hash, supplier_model_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (supplier_id, idempotency_key, request_hash, supplier_model_id, created_at),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id), True

    def get_supplier_model(self, supplier_model_id):
        row = self.conn.execute(
            "SELECT * FROM supplier_models WHERE supplier_model_id = ?",
            (supplier_model_id,),
        ).fetchone()
        return None if row is None else SupplierModelRecord(**dict(row))

    def get_supplier_model_revision(self, model_revision_id):
        row = self.conn.execute(
            "SELECT * FROM supplier_model_revisions WHERE model_revision_id = ?",
            (model_revision_id,),
        ).fetchone()
        return None if row is None else SupplierModelRevisionRecord(**dict(row))

    def get_credential_version(self, credential_version_id):
        row = self.conn.execute(
            "SELECT * FROM credential_versions WHERE credential_version_id = ?",
            (credential_version_id,),
        ).fetchone()
        return None if row is None else CredentialVersionRecord(**dict(row))

    def list_supplier_models(self, supplier_id, *, include_archived=False):
        archived_filter = "" if include_archived else " AND archived_at = ''"
        rows = self.conn.execute(
            "SELECT * FROM supplier_models WHERE supplier_id = ?%s ORDER BY created_at, supplier_model_id"
            % archived_filter,
            (supplier_id,),
        ).fetchall()
        return [SupplierModelRecord(**dict(row)) for row in rows]

    def find_active_model_name(self, supplier_id, capability, provider_model_name, *, exclude_id=""):
        return self.conn.execute(
            """
            SELECT m.supplier_model_id
            FROM supplier_models AS m
            JOIN supplier_model_revisions AS r
              ON r.model_revision_id = m.current_model_revision_id
            WHERE m.supplier_id = ? AND m.enabled = 1
              AND r.capability = ? AND r.provider_model_name = ?
              AND m.supplier_model_id <> ?
            LIMIT 1
            """,
            (supplier_id, capability, provider_model_name, exclude_id),
        ).fetchone()

    def revise_supplier_model(
        self,
        supplier_model_id,
        *,
        provider_model_name,
        display_name,
        capability,
        definition,
        expected_catalog_revision,
        expected_model_revision,
        acknowledged_binding_count=0,
    ):
        normalized = json.dumps(
            definition, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        definition_object_id = self.runtime.write_text_object(normalized)
        definition_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        model_revision_id = uuid.uuid4().hex
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            model = self.get_supplier_model(supplier_model_id)
            if model is None:
                raise NotFound("model not found: %s" % supplier_model_id)
            supplier = self.get_supplier(model.supplier_id)
            if (
                model.revision != expected_model_revision
                or supplier.model_catalog_revision != expected_catalog_revision
            ):
                raise RevisionConflict("model revision conflict")
            if self.count_project_binding_references(supplier_model_id) != acknowledged_binding_count:
                raise RevisionConflict("affected binding acknowledgement conflict")
            if model.enabled and self.find_active_model_name(
                model.supplier_id,
                capability,
                provider_model_name,
                exclude_id=supplier_model_id,
            ):
                raise ModelNameConflict("MODEL_NAME_CONFLICT")
            next_revision = model.revision + 1
            self.conn.execute(
                """
                INSERT INTO supplier_model_revisions
                (model_revision_id, supplier_model_id, revision, provider_model_name,
                 display_name, capability, definition_object_id, definition_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    model_revision_id,
                    supplier_model_id,
                    next_revision,
                    provider_model_name,
                    display_name,
                    capability,
                    definition_object_id,
                    definition_hash,
                    created_at,
                ),
            )
            model_cursor = self.conn.execute(
                """
                UPDATE supplier_models
                SET current_model_revision_id = ?, revision = revision + 1, updated_at = ?
                WHERE supplier_model_id = ? AND revision = ?
                """,
                (model_revision_id, created_at, supplier_model_id, expected_model_revision),
            )
            supplier_cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (created_at, model.supplier_id, expected_catalog_revision),
            )
            if model_cursor.rowcount != 1 or supplier_cursor.rowcount != 1:
                raise RevisionConflict("model revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id)

    def set_supplier_model_enabled(
        self, supplier_model_id, *, enabled, expected_catalog_revision, expected_model_revision
    ):
        updated_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            model = self.get_supplier_model(supplier_model_id)
            if model is None:
                raise NotFound("model not found: %s" % supplier_model_id)
            if enabled:
                revision = self.get_supplier_model_revision(model.current_model_revision_id)
                if self.find_active_model_name(
                    model.supplier_id,
                    revision.capability,
                    revision.provider_model_name,
                    exclude_id=supplier_model_id,
                ):
                    raise ModelNameConflict("MODEL_NAME_CONFLICT")
            model_cursor = self.conn.execute(
                """
                UPDATE supplier_models
                SET enabled = ?, revision = revision + 1, updated_at = ?
                WHERE supplier_model_id = ? AND revision = ?
                """,
                (int(enabled), updated_at, supplier_model_id, expected_model_revision),
            )
            supplier_cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (updated_at, model.supplier_id, expected_catalog_revision),
            )
            if model_cursor.rowcount != 1 or supplier_cursor.rowcount != 1:
                raise RevisionConflict("model revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id)

    def count_model_references(self, supplier_model_id):
        row = self.conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM project_model_bindings
               WHERE default_text_model_id = ? OR default_image_model_id = ? OR default_video_model_id = ?)
              + (SELECT COUNT(*) FROM project_model_operation_overrides WHERE supplier_model_id = ?)
              + (SELECT COUNT(*) FROM execution_snapshots WHERE supplier_model_id = ?) AS n
            """,
            (supplier_model_id,) * 5,
        ).fetchone()
        return int(row["n"])

    def count_model_history_references(self, supplier_model_id):
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM execution_snapshots WHERE supplier_model_id = ?",
            (supplier_model_id,),
        ).fetchone()
        return int(row["n"])

    def count_project_binding_references(self, supplier_model_id):
        row = self.conn.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM project_model_bindings
               WHERE default_text_model_id = ? OR default_image_model_id = ? OR default_video_model_id = ?)
              + (SELECT COUNT(*) FROM project_model_operation_overrides WHERE supplier_model_id = ?) AS n
            """,
            (supplier_model_id,) * 4,
        ).fetchone()
        return int(row["n"])

    def delete_supplier_model(
        self, supplier_model_id, *, expected_catalog_revision, expected_model_revision
    ):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            model = self.get_supplier_model(supplier_model_id)
            if model is None:
                raise NotFound("model not found: %s" % supplier_model_id)
            if self.count_model_references(supplier_model_id):
                raise ModelReferenced("MODEL_REFERENCED")
            supplier = self.get_supplier(model.supplier_id)
            if (
                model.revision != expected_model_revision
                or supplier.model_catalog_revision != expected_catalog_revision
            ):
                raise RevisionConflict("model revision conflict")
            self.conn.execute(
                "DELETE FROM model_creation_requests WHERE supplier_model_id = ?",
                (supplier_model_id,),
            )
            self.conn.execute(
                "DELETE FROM supplier_model_revisions WHERE supplier_model_id = ?",
                (supplier_model_id,),
            )
            cursor = self.conn.execute(
                "DELETE FROM supplier_models WHERE supplier_model_id = ? AND revision = ?",
                (supplier_model_id, expected_model_revision),
            )
            supplier_cursor = self.conn.execute(
                """
                UPDATE suppliers SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (now_iso(), model.supplier_id, expected_catalog_revision),
            )
            if cursor.rowcount != 1 or supplier_cursor.rowcount != 1:
                raise RevisionConflict("model revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def remove_supplier_model_atomically(
        self, supplier_model_id, *, expected_catalog_revision, expected_model_revision
    ):
        """Reject, archive, or physically delete from one locked decision."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            model = self.get_supplier_model(supplier_model_id)
            if model is None:
                raise NotFound("model not found: %s" % supplier_model_id)
            supplier = self.get_supplier(model.supplier_id)
            if (
                model.revision != expected_model_revision
                or supplier.model_catalog_revision != expected_catalog_revision
            ):
                raise RevisionConflict("model revision conflict")
            if model.archived_at:
                self.conn.commit()
                return model
            if self.count_project_binding_references(supplier_model_id):
                raise ModelReferenced("MODEL_REFERENCED")

            changed_at = now_iso()
            if self.count_model_history_references(supplier_model_id):
                cursor = self.conn.execute(
                    """
                    UPDATE supplier_models
                    SET enabled = 0, revision = revision + 1,
                        archived_at = ?, archive_reason = 'historical_snapshot', updated_at = ?
                    WHERE supplier_model_id = ? AND revision = ? AND archived_at = ''
                    """,
                    (changed_at, changed_at, supplier_model_id, expected_model_revision),
                )
                if cursor.rowcount != 1:
                    raise RevisionConflict("model revision conflict")
            else:
                self.conn.execute(
                    "DELETE FROM model_creation_requests WHERE supplier_model_id = ?",
                    (supplier_model_id,),
                )
                self.conn.execute(
                    "DELETE FROM supplier_model_revisions WHERE supplier_model_id = ?",
                    (supplier_model_id,),
                )
                cursor = self.conn.execute(
                    "DELETE FROM supplier_models WHERE supplier_model_id = ? AND revision = ?",
                    (supplier_model_id, expected_model_revision),
                )
                if cursor.rowcount != 1:
                    raise RevisionConflict("model revision conflict")
            supplier_cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (changed_at, model.supplier_id, expected_catalog_revision),
            )
            if supplier_cursor.rowcount != 1:
                raise RevisionConflict("model revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id)

    def archive_supplier_model(
        self,
        supplier_model_id,
        *,
        expected_catalog_revision,
        expected_model_revision,
        archive_reason,
    ):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            model = self.get_supplier_model(supplier_model_id)
            if model is None:
                raise NotFound("model not found: %s" % supplier_model_id)
            supplier = self.get_supplier(model.supplier_id)
            if (
                model.revision != expected_model_revision
                or supplier.model_catalog_revision != expected_catalog_revision
            ):
                raise RevisionConflict("model revision conflict")
            if model.archived_at:
                self.conn.commit()
                return model
            if self.count_project_binding_references(supplier_model_id):
                raise ModelReferenced("MODEL_REFERENCED")
            archived_at = now_iso()
            model_cursor = self.conn.execute(
                """
                UPDATE supplier_models
                SET enabled = 0, revision = revision + 1,
                    archived_at = ?, archive_reason = ?, updated_at = ?
                WHERE supplier_model_id = ? AND revision = ? AND archived_at = ''
                """,
                (
                    archived_at,
                    str(archive_reason),
                    archived_at,
                    supplier_model_id,
                    expected_model_revision,
                ),
            )
            supplier_cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET model_catalog_revision = model_catalog_revision + 1, updated_at = ?
                WHERE supplier_id = ? AND model_catalog_revision = ?
                """,
                (archived_at, model.supplier_id, expected_catalog_revision),
            )
            if model_cursor.rowcount != 1 or supplier_cursor.rowcount != 1:
                raise RevisionConflict("model revision conflict")
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model(supplier_model_id)

    def get_project_model_binding(self, project_id):
        row = self.conn.execute(
            "SELECT * FROM project_model_bindings WHERE project_id = ?", (project_id,)
        ).fetchone()
        return None if row is None else ProjectModelBindingRecord(**dict(row))

    def get_project_model_overrides(self, project_id):
        rows = self.conn.execute(
            """
            SELECT operation_key, supplier_model_id
            FROM project_model_operation_overrides
            WHERE project_id = ? ORDER BY operation_key
            """,
            (project_id,),
        ).fetchall()
        return {row["operation_key"]: row["supplier_model_id"] for row in rows}

    def replace_project_model_bindings(
        self, project_id, *, defaults, overrides, expected_revision
    ):
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            from .suppliers.operations import OPERATION_CAPABILITIES

            for capability, model_id in defaults.items():
                if model_id:
                    self._assert_model_capability_locked(model_id, capability)
            for operation_key, model_id in overrides.items():
                capability = OPERATION_CAPABILITIES.get(operation_key)
                if capability is None:
                    raise ValueError("UNKNOWN_OPERATION_KEY")
                self._assert_model_capability_locked(model_id, capability)
            current = self.get_project_model_binding(project_id)
            if current is None:
                if expected_revision != 0:
                    raise RevisionConflict("binding set revision conflict")
                self.conn.execute(
                    """
                    INSERT INTO project_model_bindings
                    (project_id, default_text_model_id, default_image_model_id,
                     default_video_model_id, binding_set_revision, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 1, ?, ?)
                    """,
                    (
                        project_id,
                        defaults["text"] or None,
                        defaults["image"] or None,
                        defaults["video"] or None,
                        created_at,
                        created_at,
                    ),
                )
            else:
                cursor = self.conn.execute(
                    """
                    UPDATE project_model_bindings
                    SET default_text_model_id = ?, default_image_model_id = ?,
                        default_video_model_id = ?, binding_set_revision = binding_set_revision + 1,
                        updated_at = ?
                    WHERE project_id = ? AND binding_set_revision = ?
                    """,
                    (
                        defaults["text"] or None,
                        defaults["image"] or None,
                        defaults["video"] or None,
                        created_at,
                        project_id,
                        expected_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise RevisionConflict("binding set revision conflict")
            self.conn.execute(
                "DELETE FROM project_model_operation_overrides WHERE project_id = ?", (project_id,)
            )
            self.conn.executemany(
                """
                INSERT INTO project_model_operation_overrides
                (project_id, operation_key, supplier_model_id) VALUES (?, ?, ?)
                """,
                [(project_id, key, model_id) for key, model_id in sorted(overrides.items())],
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise

    def _assert_model_capability_locked(self, supplier_model_id, capability):
        model = self.get_supplier_model(supplier_model_id)
        if model is None:
            raise ValueError("MODEL_NOT_FOUND")
        revision = self.get_supplier_model_revision(model.current_model_revision_id)
        if revision is None or revision.capability != capability:
            raise ValueError("MODEL_CAPABILITY_MISMATCH")

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
        manifest=None,
        adapter_contract_version="ai-drama-supplier-v1",
        worker_protocol_version="1",
        worker_runtime_version="unavailable",
        compiler_name="unknown",
        compiler_version="unknown",
        compiler_options_hash="",
        helper_api_version="ai-drama-helper-v1",
        rate_limit_bucket_key="",
        expected_revision,
        built_in=False,
    ):
        supplier_version_id = uuid.uuid4().hex
        created_at = now_iso()
        manifest_text = json.dumps(
            manifest or {},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        manifest_object_id = self.runtime.write_text_object(manifest_text) if manifest else ""
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
                 manifest_hash, manifest_object_id, rate_limit_bucket_key,
                 adapter_contract_version, worker_protocol_version,
                 worker_runtime_version, compiler_name, compiler_version,
                 compiler_options_hash, helper_api_version, built_in, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    manifest_object_id,
                    rate_limit_bucket_key,
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
            if manifest is not None:
                self._sync_manifest_models_locked(supplier_id, manifest.get("models", []))
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
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            supplier = self.get_supplier(supplier_id)
            if supplier is None:
                raise NotFound("supplier not found: %s" % supplier_id)
            if supplier.revision != expected_revision:
                raise RevisionConflict("supplier revision conflict")
            row = self.conn.execute(
                """
                SELECT * FROM supplier_versions
                WHERE supplier_id = ? AND built_in = 1
                ORDER BY revision DESC LIMIT 1
                """,
                (supplier_id,),
            ).fetchone()
            if row is None or not row["manifest_object_id"]:
                raise NotFound("built-in supplier version not found")
            manifest_text = self.runtime.read_text(row["manifest_object_id"])
            if hashlib.sha256(manifest_text.encode("utf-8")).hexdigest() != row["manifest_hash"]:
                raise NotFound("built-in supplier manifest unavailable")
            manifest = json.loads(manifest_text)
            cursor = self.conn.execute(
                """
                UPDATE suppliers
                SET current_supplier_version_id = ?, revision = revision + 1, updated_at = ?
                WHERE supplier_id = ? AND revision = ?
                """,
                (row["supplier_version_id"], now_iso(), supplier_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict("supplier revision conflict")
            self._sync_manifest_models_locked(supplier_id, manifest.get("models", []))
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
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
        self, *, slug, display_name, idempotency_key, request_hash, initial_version=None
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
            if initial_version:
                supplier_version_id = uuid.uuid4().hex
                manifest = initial_version["manifest"]
                manifest_text = json.dumps(
                    manifest,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                manifest_object_id = self.runtime.write_text_object(manifest_text)
                self.conn.execute(
                    """
                    INSERT INTO supplier_versions
                    (supplier_version_id, supplier_id, revision, source_object_id,
                     source_hash, compiled_artifact_object_id, compiled_artifact_hash,
                     manifest_hash, manifest_object_id, rate_limit_bucket_key,
                     adapter_contract_version, worker_protocol_version,
                     worker_runtime_version, compiler_name, compiler_version,
                     compiler_options_hash, helper_api_version, built_in, created_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        supplier_version_id,
                        supplier_id,
                        initial_version["source_object_id"],
                        initial_version["source_hash"],
                        initial_version["compiled_artifact_object_id"],
                        initial_version["compiled_artifact_hash"],
                        initial_version["manifest_hash"],
                        manifest_object_id,
                        initial_version["rate_limit_bucket_key"],
                        initial_version["adapter_contract_version"],
                        initial_version["worker_protocol_version"],
                        initial_version["worker_runtime_version"],
                        initial_version["compiler_name"],
                        initial_version["compiler_version"],
                        initial_version["compiler_options_hash"],
                        initial_version["helper_api_version"],
                        created_at,
                    ),
                )
                self.conn.execute(
                    """
                    UPDATE suppliers SET current_supplier_version_id = ?
                    WHERE supplier_id = ?
                    """,
                    (supplier_version_id, supplier_id),
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

    def enqueue_generation_job_with_snapshot(
        self, *, supplier_id, capability, provider, job_type, project_id,
        chapter_id, shot_id, prompt_revision_id, idempotency_key, request,
        snapshot, attempt_number=1, source_job_id="", rerun_resolution_mode="",
    ):
        from .suppliers.idempotency import SupplierIdempotencyConflict, canonical_request_hash
        from .suppliers.snapshots import _validate_snapshot, canonical_snapshot_json, snapshot_hash

        _validate_snapshot(self, snapshot)
        snapshot_raw = canonical_snapshot_json(snapshot)
        resolved_snapshot_hash = snapshot_hash(snapshot)
        snapshot_object_id = self.runtime.write_text_object(snapshot_raw)
        request_raw = _normalized_json(request)
        request_object_id = self.runtime.write_text_object(request_raw)
        request_hash = canonical_request_hash(request, resolved_snapshot_hash)
        created_at = now_iso()
        job_id = uuid.uuid4().hex
        attempt_id = uuid.uuid4().hex
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.conn.execute(
                "SELECT * FROM supplier_idempotency_records WHERE supplier_id = ? AND capability = ? AND idempotency_key = ?",
                (supplier_id, capability, idempotency_key),
            ).fetchone()
            if replay is not None:
                if replay["request_hash"] != request_hash:
                    raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
                self.conn.commit()
                return self.get_generation_job(replay["existing_id"]), False
            self.conn.execute(
                "INSERT OR IGNORE INTO execution_snapshots (snapshot_hash, snapshot_object_id, supplier_id, supplier_model_id, model_revision_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (resolved_snapshot_hash, snapshot_object_id, snapshot.supplier_id,
                 snapshot.supplier_model_id, snapshot.model_revision_id, snapshot.created_at),
            )
            self.conn.execute(
                """
                INSERT INTO generation_jobs
                (job_id, provider, job_type, project_id, chapter_id, shot_id,
                 prompt_revision_id, internal_status, idempotency_key, request_hash,
                 request_object_id, attempt_number, created_at, updated_at,
                 snapshot_hash, snapshot_object_id, resolved_snapshot_object_id,
                 source_job_id, rerun_resolution_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, provider, job_type, project_id, chapter_id, shot_id,
                 prompt_revision_id, idempotency_key, request_hash,
                 request_object_id, attempt_number, created_at, created_at,
                 resolved_snapshot_hash, snapshot_object_id, snapshot_object_id,
                 source_job_id, rerun_resolution_mode),
            )
            self.conn.execute(
                "INSERT INTO generation_submission_attempts (attempt_id, job_id, attempt_number, state, created_at, updated_at) VALUES (?, ?, ?, 'prepared', ?, ?)",
                (attempt_id, job_id, attempt_number, created_at, created_at),
            )
            self.conn.execute(
                "INSERT INTO supplier_idempotency_records (supplier_id, capability, idempotency_key, request_hash, existing_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (supplier_id, capability, idempotency_key, request_hash, job_id, created_at),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_generation_job(job_id), True

    def get_supplier_idempotency_record(self, supplier_id, capability, idempotency_key):
        row = self.conn.execute(
            """
            SELECT * FROM supplier_idempotency_records
            WHERE supplier_id = ? AND capability = ? AND idempotency_key = ?
            """,
            (supplier_id, capability, idempotency_key),
        ).fetchone()
        return None if row is None else dict(row)

    def create_supplier_model_test_run(
        self, *, test_run_id, supplier_id, supplier_model_id, credential_version_id,
        snapshot, capability, idempotency_key, request_hash, request_object_id,
    ):
        from .suppliers.snapshots import _validate_snapshot, canonical_snapshot_json, snapshot_hash

        _validate_snapshot(self, snapshot)
        snapshot_raw = canonical_snapshot_json(snapshot)
        digest = snapshot_hash(snapshot)
        snapshot_object_id = self.runtime.write_text_object(snapshot_raw)
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.conn.execute(
                """
                SELECT * FROM supplier_model_test_runs
                WHERE supplier_model_id = ? AND capability = ? AND idempotency_key = ?
                """,
                (supplier_model_id, capability, idempotency_key),
            ).fetchone()
            if replay is not None:
                if replay["request_hash"] != request_hash:
                    raise RevisionConflict("IDEMPOTENCY_CONFLICT")
                self.conn.commit()
                return dict(replay), False
            self.conn.execute(
                """
                INSERT OR IGNORE INTO execution_snapshots
                (snapshot_hash, snapshot_object_id, supplier_id, supplier_model_id,
                 model_revision_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    digest,
                    snapshot_object_id,
                    snapshot.supplier_id,
                    snapshot.supplier_model_id,
                    snapshot.model_revision_id,
                    snapshot.created_at,
                ),
            )
            self.conn.execute(
                """
                INSERT INTO supplier_model_test_runs
                (test_run_id, supplier_id, supplier_model_id, credential_version_id,
                 snapshot_hash, snapshot_object_id, capability, idempotency_key,
                 request_hash, request_object_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?)
                """,
                (
                    test_run_id,
                    supplier_id,
                    supplier_model_id,
                    credential_version_id,
                    digest,
                    snapshot_object_id,
                    capability,
                    idempotency_key,
                    request_hash,
                    request_object_id,
                    created_at,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_model_test_run(test_run_id), True

    def get_supplier_model_test_run(self, test_run_id):
        row = self.conn.execute(
            "SELECT * FROM supplier_model_test_runs WHERE test_run_id = ?",
            (test_run_id,),
        ).fetchone()
        return None if row is None else dict(row)

    def get_supplier_model_test_run_by_key(self, supplier_model_id, idempotency_key):
        row = self.conn.execute(
            """
            SELECT * FROM supplier_model_test_runs
            WHERE supplier_model_id = ? AND idempotency_key = ?
            ORDER BY created_at, test_run_id LIMIT 1
            """,
            (supplier_model_id, idempotency_key),
        ).fetchone()
        return None if row is None else dict(row)

    def claim_supplier_model_test_run(self, test_run_id, *, lease_owner, lease_expires_at):
        started_at = now_iso()
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE supplier_model_test_runs
                SET status = 'submitting', attempt_count = 1, lease_owner = ?,
                    lease_expires_at = ?, started_at = ?
                WHERE test_run_id = ? AND status = 'queued' AND attempt_count = 0
                """,
                (lease_owner, lease_expires_at, started_at, test_run_id),
            )
        return self.get_supplier_model_test_run(test_run_id) if cursor.rowcount == 1 else None

    def complete_supplier_model_test_run(
        self, test_run_id, *, normalized_result_object_id,
        sanitized_evidence_object_id, content_object_id="", media_type="", byte_size=0,
    ):
        finished_at = now_iso()
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE supplier_model_test_runs
                SET status = 'completed', normalized_result_object_id = ?,
                    sanitized_evidence_object_id = ?, content_object_id = ?,
                    media_type = ?, byte_size = ?, lease_owner = '',
                    lease_expires_at = '', finished_at = ?
                WHERE test_run_id = ? AND status = 'submitting' AND attempt_count = 1
                """,
                (
                    normalized_result_object_id,
                    sanitized_evidence_object_id,
                    content_object_id,
                    media_type,
                    int(byte_size),
                    finished_at,
                    test_run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict("MODEL_TEST_NOT_SUBMITTING")
        return self.get_supplier_model_test_run(test_run_id)

    def fail_supplier_model_test_run(
        self, test_run_id, *, error_code, error_message,
        sanitized_evidence_object_id="", unknown=False,
    ):
        finished_at = now_iso()
        status = "submission_outcome_unknown" if unknown else "failed"
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE supplier_model_test_runs
                SET status = ?, error_code = ?, error_message = ?,
                    sanitized_evidence_object_id = ?, lease_owner = '',
                    lease_expires_at = '', finished_at = ?
                WHERE test_run_id = ? AND status = 'submitting' AND attempt_count = 1
                """,
                (
                    status,
                    error_code,
                    str(error_message)[:299],
                    sanitized_evidence_object_id,
                    finished_at,
                    test_run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise RevisionConflict("MODEL_TEST_NOT_SUBMITTING")
        return self.get_supplier_model_test_run(test_run_id)

    def mark_interrupted_model_tests_unknown(self):
        finished_at = now_iso()
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE supplier_model_test_runs
                SET status = 'submission_outcome_unknown',
                    error_code = 'SUBMISSION_OUTCOME_UNKNOWN',
                    error_message = 'model test submission outcome is unknown',
                    lease_owner = '', lease_expires_at = '', finished_at = ?
                WHERE status = 'submitting' AND attempt_count = 1
                """,
                (finished_at,),
            )
        return cursor.rowcount

    def list_queued_supplier_model_tests(self, limit=20):
        rows = self.conn.execute(
            """
            SELECT * FROM supplier_model_test_runs
            WHERE status = 'queued' AND attempt_count = 0
            ORDER BY created_at, test_run_id LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [dict(row) for row in rows]

    def count_active_model_tests_for_credential(self, credential_version_id):
        row = self.conn.execute(
            """
            SELECT COUNT(*) AS n FROM supplier_model_test_runs
            WHERE credential_version_id = ? AND status IN ('queued','submitting')
            """,
            (credential_version_id,),
        ).fetchone()
        return int(row["n"])

    def enqueue_text_run_with_snapshot(self, *, project_id, operation_key, supplier_id,
                                       idempotency_key, request, snapshot):
        from .suppliers.idempotency import SupplierIdempotencyConflict, canonical_request_hash
        from .suppliers.snapshots import _validate_snapshot, canonical_snapshot_json, snapshot_hash

        _validate_snapshot(self, snapshot)
        snapshot_raw = canonical_snapshot_json(snapshot)
        digest = snapshot_hash(snapshot)
        snapshot_object_id = self.runtime.write_text_object(snapshot_raw)
        request_object_id = self.runtime.write_text_object(_normalized_json(request))
        request_hash = canonical_request_hash(request, digest)
        run_id = uuid.uuid4().hex
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.conn.execute(
                "SELECT * FROM supplier_idempotency_records WHERE supplier_id=? AND capability='text' AND idempotency_key=?",
                (supplier_id, idempotency_key),
            ).fetchone()
            if replay:
                if replay["request_hash"] != request_hash:
                    raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
                self.conn.commit()
                return self.get_supplier_text_run(replay["existing_id"]), False
            self.conn.execute(
                "INSERT OR IGNORE INTO execution_snapshots (snapshot_hash, snapshot_object_id, supplier_id, supplier_model_id, model_revision_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (digest, snapshot_object_id, snapshot.supplier_id, snapshot.supplier_model_id,
                 snapshot.model_revision_id, snapshot.created_at),
            )
            self.conn.execute(
                "INSERT INTO supplier_text_runs (run_id, project_id, operation_key, supplier_id, snapshot_hash, snapshot_object_id, idempotency_key, request_hash, request_object_id, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'prepared', ?, ?)",
                (run_id, project_id, operation_key, supplier_id, digest, snapshot_object_id,
                 idempotency_key, request_hash, request_object_id, created_at, created_at),
            )
            self.conn.execute(
                "INSERT INTO supplier_idempotency_records (supplier_id, capability, idempotency_key, request_hash, existing_id, created_at) VALUES (?, 'text', ?, ?, ?, ?)",
                (supplier_id, idempotency_key, request_hash, run_id, created_at),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_supplier_text_run(run_id), True

    def enqueue_script_generation_with_snapshot(
        self,
        *,
        run_id,
        project_id,
        chapter_id,
        source_revision_id,
        runtime_run_id,
        idempotency_key,
        supplier_id,
        supplier_idempotency_key,
        request,
        snapshot,
    ):
        """Create the snapshot, supplier run, and visible script session atomically."""
        from .suppliers.idempotency import (
            SupplierIdempotencyConflict,
            canonical_request_hash,
        )
        from .suppliers.snapshots import (
            _validate_snapshot,
            canonical_snapshot_json,
            snapshot_hash,
        )

        _validate_snapshot(self, snapshot)
        snapshot_raw = canonical_snapshot_json(snapshot)
        digest = snapshot_hash(snapshot)
        snapshot_object_id = self.runtime.write_text_object(snapshot_raw)
        request_object_id = self.runtime.write_text_object(_normalized_json(request))
        request_hash = canonical_request_hash(request, digest)
        supplier_run_id = uuid.uuid4().hex
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            supplier_replay = self.conn.execute(
                """
                SELECT * FROM supplier_idempotency_records
                WHERE supplier_id = ? AND capability = 'text'
                  AND idempotency_key = ?
                """,
                (supplier_id, supplier_idempotency_key),
            ).fetchone()
            if supplier_replay is not None:
                if supplier_replay["request_hash"] != request_hash:
                    raise SupplierIdempotencyConflict("IDEMPOTENCY_CONFLICT")
                supplier_run_id = supplier_replay["existing_id"]
            else:
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO execution_snapshots
                    (snapshot_hash, snapshot_object_id, supplier_id,
                     supplier_model_id, model_revision_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        digest,
                        snapshot_object_id,
                        snapshot.supplier_id,
                        snapshot.supplier_model_id,
                        snapshot.model_revision_id,
                        snapshot.created_at,
                    ),
                )
                self.conn.execute(
                    """
                    INSERT INTO supplier_text_runs
                    (run_id, project_id, operation_key, supplier_id,
                     snapshot_hash, snapshot_object_id, idempotency_key,
                     request_hash, request_object_id, status, created_at, updated_at)
                    VALUES (?, ?, 'script_adaptation', ?, ?, ?, ?, ?, ?,
                            'prepared', ?, ?)
                    """,
                    (
                        supplier_run_id,
                        project_id,
                        supplier_id,
                        digest,
                        snapshot_object_id,
                        supplier_idempotency_key,
                        request_hash,
                        request_object_id,
                        created_at,
                        created_at,
                    ),
                )
                self.conn.execute(
                    """
                    INSERT INTO supplier_idempotency_records
                    (supplier_id, capability, idempotency_key, request_hash,
                     existing_id, created_at)
                    VALUES (?, 'text', ?, ?, ?, ?)
                    """,
                    (
                        supplier_id,
                        supplier_idempotency_key,
                        request_hash,
                        supplier_run_id,
                        created_at,
                    ),
                )

            supplier_run = self.conn.execute(
                "SELECT * FROM supplier_text_runs WHERE run_id = ?",
                (supplier_run_id,),
            ).fetchone()
            session_replay = self.conn.execute(
                "SELECT * FROM script_generation_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if session_replay is not None:
                expected = (
                    project_id,
                    chapter_id,
                    source_revision_id,
                    supplier_run_id,
                    digest,
                )
                observed = (
                    session_replay["project_id"],
                    session_replay["chapter_id"],
                    session_replay["source_revision_id"],
                    session_replay["supplier_text_run_id"],
                    session_replay["snapshot_hash"],
                )
                if observed != expected:
                    raise ScriptGenerationConflict(
                        "SCRIPT_GENERATION_IDEMPOTENCY_CONFLICT"
                    )
                self.conn.commit()
                return dict(session_replay), dict(supplier_run), False

            self.conn.execute(
                """
                INSERT INTO script_generation_runs
                (run_id, project_id, chapter_id, source_revision_id,
                 runtime_run_id, supplier_text_run_id, snapshot_hash,
                 idempotency_key, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'prepared', ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    chapter_id,
                    source_revision_id,
                    runtime_run_id,
                    supplier_run_id,
                    digest,
                    idempotency_key,
                    created_at,
                    created_at,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return (
            self.get_script_generation_run(run_id),
            self.get_supplier_text_run(supplier_run_id),
            True,
        )

    def get_supplier_text_run(self, run_id):
        row = self.conn.execute("SELECT * FROM supplier_text_runs WHERE run_id = ?", (run_id,)).fetchone()
        return None if row is None else dict(row)

    def complete_supplier_text_run(self, run_id, *, result_object_id, evidence_object_id):
        self.conn.execute(
            "UPDATE supplier_text_runs SET status='completed', result_object_id=?, evidence_object_id=?, updated_at=? WHERE run_id=? AND status='prepared'",
            (result_object_id, evidence_object_id, now_iso(), run_id),
        )
        self.conn.commit()
        return self.get_supplier_text_run(run_id)

    def fail_supplier_text_run(self, run_id, *, error_code, evidence_object_id=""):
        self.conn.execute(
            "UPDATE supplier_text_runs SET status='failed', error_code=?, evidence_object_id=?, updated_at=? WHERE run_id=? AND status='prepared'",
            (error_code, evidence_object_id, now_iso(), run_id),
        )
        self.conn.commit()
        return self.get_supplier_text_run(run_id)

    def create_script_generation_run(
        self,
        *,
        run_id,
        project_id,
        chapter_id,
        source_revision_id,
        runtime_run_id,
        idempotency_key,
    ):
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            replay = self.conn.execute(
                "SELECT * FROM script_generation_runs WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
            if replay is not None:
                expected = (project_id, chapter_id, source_revision_id)
                observed = (
                    replay["project_id"],
                    replay["chapter_id"],
                    replay["source_revision_id"],
                )
                if observed != expected:
                    raise ScriptGenerationConflict("SCRIPT_GENERATION_IDEMPOTENCY_CONFLICT")
                self.conn.commit()
                return dict(replay)
            self.conn.execute(
                """
                INSERT INTO script_generation_runs
                (run_id, project_id, chapter_id, source_revision_id,
                 runtime_run_id, idempotency_key, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'prepared', ?, ?)
                """,
                (
                    run_id,
                    project_id,
                    chapter_id,
                    source_revision_id,
                    runtime_run_id,
                    idempotency_key,
                    created_at,
                    created_at,
                ),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_script_generation_run(run_id)

    def bind_script_generation_snapshot(
        self, run_id, *, supplier_text_run_id, snapshot_hash
    ):
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE script_generation_runs
                SET supplier_text_run_id = ?, snapshot_hash = ?, updated_at = ?
                WHERE run_id = ? AND status = 'prepared'
                  AND supplier_text_run_id = '' AND snapshot_hash = ''
                """,
                (supplier_text_run_id, snapshot_hash, now_iso(), run_id),
            )
            if cursor.rowcount != 1:
                current = self.get_script_generation_run(run_id)
                if current is None:
                    raise ScriptGenerationConflict("SCRIPT_GENERATION_NOT_FOUND")
                if (
                    current["supplier_text_run_id"] != supplier_text_run_id
                    or current["snapshot_hash"] != snapshot_hash
                ):
                    raise ScriptGenerationConflict("SCRIPT_GENERATION_BINDING_CONFLICT")
        return self.get_script_generation_run(run_id)

    def get_script_generation_run(self, run_id):
        row = self.conn.execute(
            "SELECT * FROM script_generation_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return None if row is None else dict(row)

    def get_script_generation_run_by_idempotency(self, idempotency_key):
        row = self.conn.execute(
            "SELECT * FROM script_generation_runs WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        return None if row is None else dict(row)

    def next_prepared_script_generation_run(self):
        row = self.conn.execute(
            """
            SELECT * FROM script_generation_runs
            WHERE status = 'prepared'
            ORDER BY created_at, run_id LIMIT 1
            """
        ).fetchone()
        return None if row is None else dict(row)

    def claim_script_generation_run(self, run_id):
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE script_generation_runs
                SET status = 'submitting', updated_at = ?
                WHERE run_id = ? AND status = 'prepared'
                """,
                (now_iso(), run_id),
            )
        return self.get_script_generation_run(run_id) if cursor.rowcount == 1 else None

    def append_script_generation_event(
        self, run_id, *, sequence, event_type, payload
    ):
        if event_type not in {
            "stage",
            "text_delta",
            "usage",
            "failed",
            "revision_completed",
        }:
            raise ScriptGenerationConflict("SCRIPT_EVENT_TYPE_INVALID")
        payload_raw = _normalized_json(payload)
        payload_hash = hashlib.sha256(payload_raw.encode("utf-8")).hexdigest()
        payload_object_id = self.runtime.write_text_object(payload_raw)
        byte_length = len(payload_raw.encode("utf-8"))
        created_at = now_iso()
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            existing = self.conn.execute(
                """
                SELECT * FROM script_generation_events
                WHERE run_id = ? AND sequence = ?
                """,
                (run_id, int(sequence)),
            ).fetchone()
            if existing is not None:
                if (
                    existing["event_type"] != event_type
                    or existing["payload_hash"] != payload_hash
                ):
                    raise ScriptGenerationConflict("STREAM_SEQUENCE_CONFLICT")
                self.conn.commit()
                return dict(existing)
            current = self.conn.execute(
                "SELECT * FROM script_generation_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if current is None:
                raise ScriptGenerationConflict("SCRIPT_GENERATION_NOT_FOUND")
            if int(sequence) != int(current["last_sequence"]) + 1:
                raise ScriptGenerationConflict("STREAM_SEQUENCE_CONFLICT")
            text_length = (
                len(payload.get("text", ""))
                if event_type == "text_delta"
                and isinstance(payload, dict)
                and isinstance(payload.get("text"), str)
                else 0
            )
            self.conn.execute(
                """
                INSERT INTO script_generation_events
                (run_id, sequence, event_type, payload_object_id, payload_hash,
                 byte_length, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    int(sequence),
                    event_type,
                    payload_object_id,
                    payload_hash,
                    byte_length,
                    created_at,
                ),
            )
            self.conn.execute(
                """
                UPDATE script_generation_runs
                SET last_sequence = ?, character_count = character_count + ?,
                    updated_at = ?
                WHERE run_id = ?
                """,
                (int(sequence), text_length, created_at, run_id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return dict(
            self.conn.execute(
                """
                SELECT * FROM script_generation_events
                WHERE run_id = ? AND sequence = ?
                """,
                (run_id, int(sequence)),
            ).fetchone()
        )

    def list_script_generation_events(self, run_id, *, after_sequence=0):
        rows = self.conn.execute(
            """
            SELECT * FROM script_generation_events
            WHERE run_id = ? AND sequence > ?
            ORDER BY sequence
            """,
            (run_id, int(after_sequence)),
        ).fetchall()
        return [dict(row) for row in rows]

    def transition_script_generation_run(
        self,
        run_id,
        *,
        expected_statuses,
        status,
        revision_id="",
        error_code="",
        evidence_object_id="",
    ):
        expected = tuple(expected_statuses)
        if not expected:
            raise ScriptGenerationConflict("SCRIPT_STATUS_CONFLICT")
        placeholders = ",".join("?" for _ in expected)
        with self.conn:
            cursor = self.conn.execute(
                f"""
                UPDATE script_generation_runs
                SET status = ?, revision_id = ?, error_code = ?,
                    evidence_object_id = ?, updated_at = ?
                WHERE run_id = ? AND status IN ({placeholders})
                """,
                (
                    status,
                    revision_id,
                    error_code,
                    evidence_object_id,
                    now_iso(),
                    run_id,
                    *expected,
                ),
            )
        if cursor.rowcount != 1:
            raise ScriptGenerationConflict("SCRIPT_STATUS_CONFLICT")
        return self.get_script_generation_run(run_id)

    def recover_script_generation_runs(self):
        finalizing = [
            dict(row)
            for row in self.conn.execute(
                "SELECT * FROM script_generation_runs WHERE status = 'finalizing'"
            ).fetchall()
        ]
        for session in finalizing:
            runtime_run = self.runtime.get_run(session["runtime_run_id"])
            revision = self.conn.execute(
                """
                SELECT revision_id FROM revisions
                WHERE run_id = ? ORDER BY number DESC LIMIT 1
                """,
                (session["runtime_run_id"],),
            ).fetchone()
            if runtime_run is not None and runtime_run.status == "SUCCEEDED" and revision:
                completed_event = self.conn.execute(
                    """
                    SELECT 1 FROM script_generation_events
                    WHERE run_id = ? AND event_type = 'revision_completed'
                    """,
                    (session["run_id"],),
                ).fetchone()
                if completed_event is None:
                    current = self.get_script_generation_run(session["run_id"])
                    self.append_script_generation_event(
                        session["run_id"],
                        sequence=current["last_sequence"] + 1,
                        event_type="revision_completed",
                        payload={"revision_id": revision["revision_id"]},
                    )
                self.transition_script_generation_run(
                    session["run_id"],
                    expected_statuses=("finalizing",),
                    status="completed",
                    revision_id=revision["revision_id"],
                    evidence_object_id=session["evidence_object_id"],
                )
            elif runtime_run is not None and runtime_run.status in {
                "PARSE_FAILED",
                "VALIDATION_FAILED",
                "RUNTIME_FAILED",
            }:
                self.transition_script_generation_run(
                    session["run_id"],
                    expected_statuses=("finalizing",),
                    status="failed",
                    error_code=runtime_run.error_code or runtime_run.status,
                    evidence_object_id=session["evidence_object_id"],
                )
        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE script_generation_runs
                SET status = 'unknown_outcome',
                    error_code = 'SUBMISSION_OUTCOME_UNKNOWN', updated_at = ?
                WHERE status IN ('submitting','streaming','finalizing')
                """,
                (now_iso(),),
            )
        return {"unknown_outcome": cursor.rowcount}

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

    def attach_generation_snapshot(self, job_id, *, snapshot_hash, snapshot_object_id):
        self.conn.execute(
            "UPDATE generation_jobs SET snapshot_hash = ?, snapshot_object_id = ?, resolved_snapshot_object_id = ?, updated_at = ? WHERE job_id = ?",
            (snapshot_hash, snapshot_object_id, snapshot_object_id, now_iso(), job_id),
        )
        self.conn.commit()
        return self.get_generation_job(job_id)

    def prepare_submission_attempt(self, job_id, *, attempt_number):
        existing = self.conn.execute(
            "SELECT * FROM generation_submission_attempts WHERE job_id = ?", (job_id,)
        ).fetchone()
        if existing is not None:
            return dict(existing)
        attempt_id = uuid.uuid4().hex
        now = now_iso()
        self.conn.execute(
            "INSERT INTO generation_submission_attempts (attempt_id, job_id, attempt_number, state, created_at, updated_at) VALUES (?, ?, ?, 'prepared', ?, ?)",
            (attempt_id, job_id, attempt_number, now, now),
        )
        self.conn.commit()
        return dict(self.conn.execute("SELECT * FROM generation_submission_attempts WHERE attempt_id = ?", (attempt_id,)).fetchone())

    def record_submission_attempt(self, job_id, *, state, provider_job_id="", evidence_object_id=""):
        if state not in {"submitting", "accepted", "committed", "unknown_outcome", "failed"}:
            raise ValueError("invalid submission attempt state")
        self.conn.execute(
            "UPDATE generation_submission_attempts SET state = ?, provider_job_id = ?, evidence_object_id = ?, updated_at = ? WHERE job_id = ?",
            (state, provider_job_id, evidence_object_id, now_iso(), job_id),
        )
        self.conn.commit()
        row = self.conn.execute("SELECT * FROM generation_submission_attempts WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else dict(row)

    def claim_generation_submission(self, job_id):
        """Atomically claim a prepared job before any external submission occurs."""
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            job = self.conn.execute(
                "SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            attempt = self.conn.execute(
                "SELECT * FROM generation_submission_attempts WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if (
                job is None
                or attempt is None
                or job["internal_status"] != "queued"
                or attempt["state"] != "prepared"
            ):
                self.conn.commit()
                return None
            updated_at = now_iso()
            job_update = self.conn.execute(
                """
                UPDATE generation_jobs
                SET internal_status = 'submitting', submitted_at = ?, updated_at = ?
                WHERE job_id = ? AND internal_status = 'queued'
                """,
                (updated_at, updated_at, job_id),
            )
            attempt_update = self.conn.execute(
                """
                UPDATE generation_submission_attempts
                SET state = 'submitting', updated_at = ?
                WHERE job_id = ? AND state = 'prepared'
                """,
                (updated_at, job_id),
            )
            if job_update.rowcount != 1 or attempt_update.rowcount != 1:
                self.conn.rollback()
                return None
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_generation_job(job_id)

    def commit_accepted_submission(self, job_id):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            attempt = self.conn.execute(
                "SELECT * FROM generation_submission_attempts WHERE job_id = ?", (job_id,)
            ).fetchone()
            job = self.conn.execute("SELECT * FROM generation_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if attempt is None or job is None or attempt["state"] != "accepted" or not attempt["provider_job_id"]:
                raise ValueError("accepted submission is not recoverable")
            if job["internal_status"] == "submitting":
                self.conn.execute(
                    "UPDATE generation_jobs SET internal_status='submitted', provider_job_id=?, response_object_id=?, updated_at=? WHERE job_id=?",
                    (attempt["provider_job_id"], attempt["evidence_object_id"], now_iso(), job_id),
                )
            elif job["internal_status"] != "submitted":
                raise ValueError("accepted submission job state is invalid")
            self.conn.execute(
                "UPDATE generation_submission_attempts SET state='committed', updated_at=? WHERE job_id=?",
                (now_iso(), job_id),
            )
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        return self.get_generation_job(job_id)

    def get_submission_attempt(self, job_id):
        row = self.conn.execute("SELECT * FROM generation_submission_attempts WHERE job_id = ?", (job_id,)).fetchone()
        return None if row is None else dict(row)

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

    def create_rerun_record(self, *, source_job_id, new_job_id, overrides_object_id,
                            resolution_mode="", source_snapshot_hash="", new_snapshot_hash=""):
        created_at = now_iso()
        rerun_id = uuid.uuid4().hex
        self.conn.execute(
            """
            INSERT INTO rerun_records
            (rerun_id, source_job_id, new_job_id, overrides_object_id, created_at,
             resolution_mode, source_snapshot_hash, new_snapshot_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rerun_id, source_job_id, new_job_id, overrides_object_id, created_at,
             resolution_mode, source_snapshot_hash, new_snapshot_hash),
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
