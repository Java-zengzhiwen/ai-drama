from pathlib import Path

from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_web.store import (
    M6A_SUPPLIER_FINGERPRINT_MIGRATION_ID,
    M6A_SUPPLIER_MIGRATION_ID,
    M6B_MODEL_CATALOG_MIGRATION_ID,
    M6C_ADAPTER_CUTOVER_MIGRATION_ID,
    M6C_SUBMISSION_STATE_MIGRATION_ID,
    ProductStore,
)


ALL_M6_MIGRATIONS = (
    M6A_SUPPLIER_MIGRATION_ID,
    M6A_SUPPLIER_FINGERPRINT_MIGRATION_ID,
    M6B_MODEL_CATALOG_MIGRATION_ID,
    M6C_ADAPTER_CUTOVER_MIGRATION_ID,
    M6C_SUBMISSION_STATE_MIGRATION_ID,
)


class M6EStoreFactory:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def m5(self):
        runtime = RuntimeStore(self.root / "runtime.db", self.root / "objects")
        runtime.conn.executescript(M5_PRODUCT_SCHEMA)
        now = now_iso()
        source_object_id = runtime.write_text_object("m5 source history")
        request_object_id = runtime.write_text_object('{"prompt":"m5 completed"}')
        result_object_id = runtime.write_bytes_object(b"m5-result-media")
        metadata_object_id = runtime.write_text_object('{"legacy":true}')
        runtime.conn.execute(
            "INSERT INTO projects VALUES (?,?,?,?,?,?,?,?)",
            ("m5-project", "M5 Project", "history", "canon", "characters", "brief", now, now),
        )
        runtime.conn.execute(
            "INSERT INTO chapters VALUES (?,?,?,?,?,?,?)",
            ("m5-chapter", "m5-project", "M5 Chapter", 1, "m5-source", now, now),
        )
        runtime.conn.execute(
            "INSERT INTO chapter_source_revisions VALUES (?,?,?,?,?,?)",
            ("m5-source", "m5-chapter", 1, source_object_id, source_object_id, now),
        )
        runtime.conn.execute(
            """
            INSERT INTO generation_jobs
            (job_id,provider,job_type,project_id,chapter_id,shot_id,prompt_revision_id,
             provider_job_id,provider_result_id,internal_status,idempotency_key,request_hash,
             request_object_id,response_object_id,attempt_number,error_code,error_message,
             submitted_at,next_poll_at,completed_at,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                "m5-job", "agnes", "video", "m5-project", "m5-chapter", "m5-shot",
                "m5-prompt", "m5-video-id", "m5-result", "completed", "m5-idempotency",
                "m5-request-hash", request_object_id, "", 1, "", "", now, "", now, now, now,
            ),
        )
        runtime.conn.execute(
            "INSERT INTO generation_results VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "m5-result", "m5-job", "m5-chapter", "m5-shot", result_object_id,
                "video/mp4", "", metadata_object_id, now,
            ),
        )
        runtime.conn.commit()
        return runtime, {
            "project_id": "m5-project",
            "chapter_id": "m5-chapter",
            "job_id": "m5-job",
            "result_id": "m5-result",
            "source_object_id": source_object_id,
            "request_object_id": request_object_id,
            "result_object_id": result_object_id,
        }

    def intermediate(self, stage):
        runtime = RuntimeStore(self.root / "runtime.db", self.root / "objects")
        store = ProductStore(runtime)
        project = store.create_project(name=f"{stage} history")
        chapter = store.create_chapter(project.project_id, title="History", position=1)
        source = store.create_source_revision(chapter.chapter_id, f"{stage} immutable source")
        expected = {
            "project_id": project.project_id,
            "source_object_id": source.object_id,
            "suppliers": {
                item.slug: (
                    item.supplier_id,
                    item.current_supplier_version_id,
                    item.current_config_revision_id,
                    item.revision,
                    item.config_revision,
                )
                for item in store.list_suppliers()
            },
        }
        if stage == "m6a":
            runtime.conn.execute("DELETE FROM supplier_model_revisions")
            runtime.conn.execute("DELETE FROM supplier_models")
            runtime.conn.execute("DELETE FROM model_creation_requests")
            runtime.conn.execute("UPDATE suppliers SET model_catalog_revision=0")
            runtime.conn.execute(
                "UPDATE supplier_versions SET manifest_object_id='', rate_limit_bucket_key=''"
            )
            self._remove_migrations(runtime, M6B_MODEL_CATALOG_MIGRATION_ID,
                                    M6C_ADAPTER_CUTOVER_MIGRATION_ID,
                                    M6C_SUBMISSION_STATE_MIGRATION_ID)
        elif stage == "m6b":
            self._remove_migrations(runtime, M6C_ADAPTER_CUTOVER_MIGRATION_ID,
                                    M6C_SUBMISSION_STATE_MIGRATION_ID)
        elif stage == "m6c":
            self._remove_migrations(runtime, M6C_SUBMISSION_STATE_MIGRATION_ID)
            runtime.conn.executescript(
                """
                ALTER TABLE generation_submission_attempts RENAME TO generation_submission_attempts_current;
                CREATE TABLE generation_submission_attempts (
                  attempt_id TEXT PRIMARY KEY,
                  job_id TEXT NOT NULL UNIQUE REFERENCES generation_jobs(job_id) ON DELETE RESTRICT,
                  attempt_number INTEGER NOT NULL,
                  state TEXT NOT NULL CHECK (state IN ('prepared','submitting','submitted','committed','unknown','failed')),
                  provider_job_id TEXT NOT NULL DEFAULT '',
                  evidence_object_id TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                DROP TABLE generation_submission_attempts_current;
                """
            )
        elif stage != "m6d":
            raise ValueError(stage)
        runtime.conn.commit()
        runtime.close()
        return expected

    @staticmethod
    def _remove_migrations(runtime, *migration_ids):
        runtime.conn.executemany(
            "DELETE FROM schema_migrations WHERE migration_id=?",
            [(migration_id,) for migration_id in migration_ids],
        )


M5_PRODUCT_SCHEMA = """
CREATE TABLE projects (
  project_id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
  series_canon TEXT NOT NULL, characters_context TEXT NOT NULL,
  production_brief TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE chapters (
  chapter_id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL,
  position INTEGER NOT NULL, current_source_revision_id TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE chapter_source_revisions (
  source_revision_id TEXT PRIMARY KEY, chapter_id TEXT NOT NULL, number INTEGER NOT NULL,
  object_id TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE generation_jobs (
  job_id TEXT PRIMARY KEY, provider TEXT NOT NULL, job_type TEXT NOT NULL,
  project_id TEXT NOT NULL, chapter_id TEXT NOT NULL, shot_id TEXT NOT NULL DEFAULT '',
  prompt_revision_id TEXT NOT NULL DEFAULT '', provider_job_id TEXT NOT NULL DEFAULT '',
  provider_result_id TEXT NOT NULL DEFAULT '', internal_status TEXT NOT NULL,
  idempotency_key TEXT NOT NULL, request_hash TEXT NOT NULL, request_object_id TEXT NOT NULL,
  response_object_id TEXT NOT NULL DEFAULT '', attempt_number INTEGER NOT NULL,
  error_code TEXT NOT NULL DEFAULT '', error_message TEXT NOT NULL DEFAULT '',
  submitted_at TEXT NOT NULL DEFAULT '', next_poll_at TEXT NOT NULL DEFAULT '',
  completed_at TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(provider, idempotency_key)
);
CREATE TABLE generation_results (
  result_id TEXT PRIMARY KEY, job_id TEXT NOT NULL, chapter_id TEXT NOT NULL,
  shot_id TEXT NOT NULL, object_id TEXT NOT NULL, media_type TEXT NOT NULL,
  source_url TEXT NOT NULL, metadata_object_id TEXT NOT NULL, created_at TEXT NOT NULL
);
"""
