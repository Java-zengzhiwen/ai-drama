import hashlib

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.services.m6_generation import M6GenerationCoordinator
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.resolution import ModelBindingService
from ai_drama_web.suppliers.snapshots import load_snapshot


PNG = b"\x89PNG\r\n\x1a\n" + b"m6e-deterministic-png"
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"m6e-deterministic-mp4"


def _source(version):
    return f"""
export const vendor = {{
  id: "m6e-fake", version: "{version}", name: "M6E Fake", author: "Acceptance",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "m6e-fake-local", inputs: [], inputValues: {{}}, models: []
}};
export async function textRequest() {{ return {{ output: "fake-{version}", usage: {{}} }}; }}
export async function imageRequest() {{ return {{ media_type: "image/png", content: "fake" }}; }}
export async function videoSubmit() {{ return {{ video_id: "fake-video-{version}" }}; }}
export async function videoPoll(payload) {{ return {{ video_id: payload.request.video_id, status: "completed" }}; }}
export async function videoFetch() {{ return {{ media_type: "video/mp4", content: "fake" }}; }}
""".strip()


def _install_version(store, supplier_id, version, expected_revision):
    artifact = compile_supplier(_source(version), runtime_store=store.runtime)
    return store.replace_supplier_version(
        supplier_id,
        source_object_id=artifact.source_object_id,
        source_hash=artifact.source_hash,
        compiled_artifact_object_id=artifact.compiled_artifact_object_id,
        compiled_artifact_hash=artifact.compiled_artifact_hash,
        manifest_hash=artifact.manifest_hash,
        manifest=artifact.vendor,
        adapter_contract_version=artifact.adapter_contract_version,
        worker_protocol_version="1",
        worker_runtime_version=artifact.worker_runtime_version,
        compiler_name=artifact.compiler_name,
        compiler_version=artifact.compiler_version,
        compiler_options_hash=artifact.compiler_options_hash,
        helper_api_version=artifact.helper_api_version,
        rate_limit_bucket_key=artifact.vendor["rateLimitBucketKey"],
        expected_revision=expected_revision,
    )


def _create_model(store, supplier_id, capability, revision):
    model, created = ModelCatalogService(store).create_overlay(
        supplier_id,
        provider_model_name=f"fake-{capability}-v1",
        display_name=f"Fake {capability.title()}",
        capability=capability,
        definition={"constraints": {"offline": True}},
        expected_catalog_revision=revision,
        idempotency_key=f"m6e-{capability}",
    )
    assert created is True
    return model


class DeterministicFakeGateway:
    def __init__(self, store):
        self.store = store
        self.calls = []
        self.submit_count = 0
        self.poll_count = {}

    def invoke(self, snapshot_hash, operation, payload):
        snapshot = load_snapshot(self.store, snapshot_hash)
        supplier_version = self.store.get_supplier_version(snapshot.supplier_version_id)
        revision = supplier_version.revision
        self.calls.append((snapshot_hash, revision, operation, dict(payload)))
        if operation == "textRequest":
            return {
                "output": f"M6E_FAKE_VERSION_{revision}",
                "usage": {"input_tokens": 2, "output_tokens": 3},
                "authorization": "must-not-persist",
            }
        if operation == "imageRequest":
            return {
                "media_type": "image/png",
                "bytes": PNG,
                "url": "https://fake.invalid/image.png?token=must-not-persist",
            }
        if operation == "videoSubmit":
            self.submit_count += 1
            return {"video_id": f"fake-video-{revision}-{self.submit_count}", "status": "queued"}
        if operation == "videoPoll":
            video_id = payload["video_id"]
            count = self.poll_count.get(video_id, 0) + 1
            self.poll_count[video_id] = count
            return {"video_id": video_id, "status": "polling" if count == 1 else "completed"}
        if operation == "videoFetch":
            return {"media_type": "video/mp4", "bytes": MP4}
        raise AssertionError(operation)


def _complete_video(store, runtime, gateway, job_id):
    service = GenerationExecutionService(
        store,
        runtime,
        FakeGenerationBackend(),
        supplier_gateway=gateway,
        supplier_execution_enabled=True,
    )
    submitted = service.submit_queued_job(job_id)
    assert submitted.internal_status == "submitted"
    provider_id = submitted.provider_job_id
    assert service.refresh_job(job_id).internal_status == "polling"

    restarted = GenerationExecutionService(
        store,
        runtime,
        FakeGenerationBackend(),
        supplier_gateway=gateway,
        supplier_execution_enabled=True,
    )
    completed = restarted.refresh_job(job_id)
    assert completed.internal_status == "completed"
    assert completed.provider_job_id == provider_id
    return completed


def test_full_fake_supplier_workflow_is_durable_restart_safe_and_snapshot_isolated(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    supplier = store.create_supplier(slug="m6e-fake", display_name="M6E Fake")
    version_v1 = _install_version(store, supplier.supplier_id, "1.0.0", supplier.revision)
    credentials = SupplierCredentialStore(store, tmp_path)
    credential = credentials.replace(supplier.supplier_id, "m6e-local-only", expected_revision=0)

    text_model = _create_model(store, supplier.supplier_id, "text", 0)
    image_model = _create_model(store, supplier.supplier_id, "image", 1)
    video_model = _create_model(store, supplier.supplier_id, "video", 2)
    project = store.create_project(name="M6E fake acceptance")
    chapter = store.create_chapter(project.project_id, title="Offline workflow", position=1)
    ModelBindingService(store).replace(
        project.project_id,
        defaults={
            "text": text_model.supplier_model_id,
            "image": image_model.supplier_model_id,
            "video": video_model.supplier_model_id,
        },
        overrides={"script_adaptation": text_model.supplier_model_id},
        expected_revision=0,
    )

    gateway = DeterministicFakeGateway(store)
    coordinator = M6GenerationCoordinator(store, runtime, credentials, gateway)
    text_v1 = coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key="m6e-text-v1",
        request={"prompt": "offline text"},
    )
    image = coordinator.generate_image(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        idempotency_key="m6e-image-v1",
        request={
            "prompt": "offline frame",
            "size": "1024x768",
            "asset_type": "shot_keyframe",
            "name": "M6E Frame",
        },
    )
    source, created = coordinator.enqueue_video(
        project_id=project.project_id,
        chapter_id=chapter.chapter_id,
        shot_id="shot-1",
        prompt_revision_id="prompt-1",
        idempotency_key="m6e-video-v1",
        request={"prompt": "offline video", "asset_ids": [], "parameters": {}},
    )
    source_snapshot = load_snapshot(store, source.snapshot_hash)
    assert created is True
    completed = _complete_video(store, runtime, gateway, source.job_id)

    assert text_v1["output"] == "M6E_FAKE_VERSION_2"
    assert runtime.read_bytes_object(store.get_asset(image["asset_id"]).object_id) == PNG
    assert runtime.read_bytes_object(store.get_generation_result(completed.provider_result_id).object_id) == MP4
    assert gateway.submit_count == 1
    assert source_snapshot.supplier_version_id == version_v1.supplier_version_id
    assert source_snapshot.resolved_credential_version_id == credential.credential_version_id
    assert "must-not-persist" not in runtime.read_text(store.get_supplier_text_run(text_v1["run_id"])["evidence_object_id"])
    image_attempt = store.get_submission_attempt(image["job_id"])
    assert "token=" not in runtime.read_text(image_attempt["evidence_object_id"])

    version_v2 = _install_version(
        store,
        supplier.supplier_id,
        "2.0.0",
        store.get_supplier(supplier.supplier_id).revision,
    )
    old_queued, _ = coordinator.rerun_video(
        source_job=completed,
        idempotency_key="m6e-rerun-inherit",
        request={"prompt": "inherit source", "asset_ids": [], "parameters": {}},
        use_current_project_model=False,
    )
    revised_video = ModelCatalogService(store).revise_model(
        video_model.supplier_model_id,
        provider_model_name="fake-video-v2",
        display_name="Fake Video V2",
        capability="video",
        definition={"constraints": {"offline": True, "revision": 2}},
        expected_catalog_revision=3,
        expected_model_revision=1,
        acknowledged_binding_count=1,
    )
    current_queued, _ = coordinator.rerun_video(
        source_job=completed,
        idempotency_key="m6e-rerun-current",
        request={"prompt": "current model", "asset_ids": [], "parameters": {}},
        use_current_project_model=True,
    )
    text_v2 = coordinator.execute_text(
        project_id=project.project_id,
        operation_key="script_adaptation",
        idempotency_key="m6e-text-v2",
        request={"prompt": "offline text after save"},
    )

    inherited = load_snapshot(store, old_queued.snapshot_hash)
    current = load_snapshot(store, current_queued.snapshot_hash)
    assert inherited.supplier_version_id == version_v1.supplier_version_id
    assert inherited.model_revision_id == source_snapshot.model_revision_id
    assert inherited.source_snapshot_hash == source.snapshot_hash
    assert inherited.credential_resolution_mode == "current"
    assert current.supplier_version_id == version_v2.supplier_version_id
    assert current.model_revision_id == revised_video.current_model_revision_id
    assert current.source_snapshot_hash == ""
    assert old_queued.rerun_resolution_mode == "inherit_source_snapshot"
    assert current_queued.rerun_resolution_mode == "current_project_model"
    assert text_v2["output"] == "M6E_FAKE_VERSION_3"

    _complete_video(store, runtime, gateway, old_queued.job_id)
    _complete_video(store, runtime, gateway, current_queued.job_id)
    assert gateway.submit_count == 3
    submit_revisions = [revision for _digest, revision, operation, _payload in gateway.calls if operation == "videoSubmit"]
    assert submit_revisions == [2, 2, 3]
    assert hashlib.sha256(PNG).hexdigest() == image["object_id"]
