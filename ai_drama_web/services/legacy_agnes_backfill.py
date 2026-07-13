import hashlib
import json
import uuid
from pathlib import Path

from ai_drama_runtime.store import now_iso
from ai_drama_web.config import Settings
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.resolution import ResolvedModel
from ai_drama_web.suppliers.snapshots import SnapshotBuilder, persist_snapshot


LEGACY_VERSION = "legacy_agnes_v1"
LEGACY_MODEL_ID = uuid.uuid5(uuid.NAMESPACE_URL, "ai-drama:legacy-agnes-v1:model:video").hex


class LegacyAgnesBackfill:
    def __init__(self, store, runtime_store, data_root, legacy_secret_store, settings=None):
        self.store = store
        self.runtime = runtime_store
        self.data_root = Path(data_root)
        self.legacy_secrets = legacy_secret_store
        self.settings = settings or Settings(data_root=self.data_root)

    def run(self):
        rows = self.store.conn.execute(
            """
            SELECT job_id FROM generation_jobs
            WHERE provider='agnes' AND job_type='video'
              AND internal_status IN ('queued','submitting','submitted','polling')
              AND snapshot_hash='' AND legacy_backfill_state!='completed'
            ORDER BY created_at, job_id
            """
        ).fetchall()
        if not rows:
            return 0
        supplier, model, revision = self._ensure_runtime()
        count = 0
        for row in rows:
            job = self.store.get_generation_job(row["job_id"])
            if not job.provider_job_id:
                self.store.conn.execute(
                    "UPDATE generation_jobs SET legacy_backfill_state='failed', error_code='LEGACY_PROVIDER_ID_MISSING', updated_at=? WHERE job_id=?",
                    (now_iso(), job.job_id),
                )
                self.store.conn.commit()
                continue
            resolved = ResolvedModel(
                job.project_id, "shot_video_generation", "video", "legacy_backfill",
                supplier, model, revision,
            )
            snapshot = SnapshotBuilder(self.store).build(
                resolved,
                credential_resolution_mode="historical",
                resolved_credential_version_id=supplier.current_credential_version_id,
                resolved_constraints={"legacy": True, "submit_allowed": False},
                worker_limits={"timeout_seconds": 30, "max_output_bytes": 4 * 1024 * 1024},
            )
            record = persist_snapshot(self.store, snapshot)
            with self.store.conn:
                self.store.conn.execute(
                    """
                    UPDATE generation_jobs
                    SET snapshot_hash=?, snapshot_object_id=?, resolved_snapshot_object_id=?,
                        legacy_backfill_state='completed', legacy_backfill_version=?, updated_at=?
                    WHERE job_id=? AND snapshot_hash=''
                    """,
                    (record.snapshot_hash, record.snapshot_object_id, record.snapshot_object_id,
                     LEGACY_VERSION, now_iso(), job.job_id),
                )
            count += 1
        return count

    def _ensure_runtime(self):
        supplier = next((item for item in self.store.list_suppliers() if item.slug == LEGACY_VERSION), None)
        if supplier is None:
            supplier = self.store.create_supplier(slug=LEGACY_VERSION, display_name="Legacy Agnes v1")
        if not supplier.current_supplier_version_id or self.store.get_supplier_version(supplier.current_supplier_version_id).worker_runtime_version.startswith("unavailable"):
            artifact = compile_supplier(_legacy_source(), runtime_store=self.runtime)
            supplier = self.store.get_supplier(supplier.supplier_id)
            self.store.replace_supplier_version(
                supplier.supplier_id,
                source_object_id=artifact.source_object_id, source_hash=artifact.source_hash,
                compiled_artifact_object_id=artifact.compiled_artifact_object_id,
                compiled_artifact_hash=artifact.compiled_artifact_hash,
                manifest_hash=artifact.manifest_hash, manifest=artifact.vendor,
                adapter_contract_version=artifact.adapter_contract_version,
                worker_protocol_version="1", worker_runtime_version=artifact.worker_runtime_version,
                compiler_name=artifact.compiler_name, compiler_version=artifact.compiler_version,
                compiler_options_hash=artifact.compiler_options_hash,
                helper_api_version=artifact.helper_api_version,
                rate_limit_bucket_key="legacy-agnes-v1", expected_revision=supplier.revision,
                built_in=True,
            )
        supplier = self.store.get_supplier(supplier.supplier_id)
        config = {
            "video_status_endpoint": self.settings.agnes_video_status_endpoint,
            "video_endpoint": self.settings.agnes_video_endpoint,
            "result_origins": ["https://platform-outputs.agnes-ai.space"],
        }
        current_config = self.store.get_config_revision(supplier.current_config_revision_id)
        if not current_config.config_object_id:
            raw = json.dumps(config, sort_keys=True, separators=(",", ":"))
            object_id = self.runtime.write_text_object(raw)
            self.store.replace_supplier_config(
                supplier.supplier_id, config_object_id=object_id,
                config_hash=hashlib.sha256(raw.encode()).hexdigest(),
                expected_revision=supplier.config_revision,
            )
        supplier = self.store.get_supplier(supplier.supplier_id)
        if not supplier.current_credential_version_id:
            secret_path = self.data_root / "secrets" / "agnes-api-key"
            secret = self.legacy_secrets.get_agnes_api_key()
            if not secret or not secret_path.exists():
                raise RuntimeError("CREDENTIAL_MISSING")
            credential_id = uuid.uuid5(uuid.NAMESPACE_URL, "ai-drama:legacy-agnes-v1:credential").hex
            digest = hashlib.sha256(secret.encode()).hexdigest()
            created = now_iso()
            with self.store.conn:
                self.store.conn.execute(
                    "INSERT OR IGNORE INTO credential_versions (credential_version_id, supplier_id, revision, state, secret_path, content_hash, created_at, updated_at) VALUES (?, ?, 1, 'ready', ?, ?, ?, ?)",
                    (credential_id, supplier.supplier_id, str(secret_path), digest, created, created),
                )
                self.store.conn.execute(
                    "UPDATE suppliers SET current_credential_version_id=?, credential_revision=1, updated_at=? WHERE supplier_id=?",
                    (credential_id, created, supplier.supplier_id),
                )
        supplier = self.store.get_supplier(supplier.supplier_id)
        model = self.store.get_supplier_model(LEGACY_MODEL_ID)
        if model is None:
            raise RuntimeError("SUPPLIER_RUNTIME_UNAVAILABLE")
        revision = self.store.get_supplier_model_revision(model.current_model_revision_id)
        return supplier, model, revision


def _legacy_source():
    return f'''
export const vendor = {{
  id: "{LEGACY_VERSION}", version: "1", name: "Legacy Agnes v1", author: "AI Drama",
  adapterContractVersion: "ai-drama-supplier-v1", helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "legacy-agnes-v1", inputs: [], inputValues: {{}},
  models: [{{ supplierModelId: "{LEGACY_MODEL_ID}", providerModelName: "agnes-video-v2.0", displayName: "Legacy Agnes Video", capability: "video" }}]
}};
export async function videoSubmit() {{ throw Object.assign(new Error("LEGACY_RESUBMIT_FORBIDDEN"), {{code:"LEGACY_RESUBMIT_FORBIDDEN"}}); }}
export async function videoPoll(payload, helpers) {{
  const raw=await helpers.http.request({{method:"GET", url:payload.config.video_status_endpoint, query:{{video_id:payload.request.video_id}}, headers:{{Authorization:`Bearer ${{payload.credential}}`}}}});
  const value=String(raw.status||raw.data?.status||"pending").toLowerCase();
  const status=({{pending:"queued",queued:"queued",processing:"polling",running:"polling",succeeded:"completed",completed:"completed",failed:"failed",error:"failed"}})[value];
  if (!status) throw Object.assign(new Error("PROVIDER_STATUS_INVALID"),{{code:"PROVIDER_STATUS_INVALID"}});
  return {{video_id:payload.request.video_id,status}};
}}
export async function videoFetch(payload, helpers) {{
  const raw=await helpers.http.request({{method:"GET", url:payload.config.video_status_endpoint, query:{{video_id:payload.request.video_id}}, headers:{{Authorization:`Bearer ${{payload.credential}}`}}}});
  const url=raw.url||raw.video_url||raw.data?.url||raw.data?.video_url;
  if (!url) throw Object.assign(new Error("RESULT_MISSING"),{{code:"RESULT_MISSING"}});
  const bytes=await helpers.http.request({{method:"GET",url,responseType:"bytes"}});
  return {{video_id:payload.request.video_id,url,...bytes}};
}}
'''
