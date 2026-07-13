import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.providers.fake import FakeGenerationBackend
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.operations.backup_restore import (
    BackupIntegrityError,
    M6BackupService,
    M6RestoreService,
    semantic_store_summary,
)
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import SupplierCredentialStore
from ai_drama_web.suppliers.resolution import ModelBindingService, ModelResolver
from ai_drama_web.suppliers.snapshots import SnapshotBuilder
from tests.web.model_test_support import create_model, install_test_supplier_runtime


def _seed(data_root):
    data_root.mkdir(parents=True)
    (data_root / ".m6e-temporary-root").write_text("test-only\n", encoding="utf-8")
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Backup project", description="semantic")
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)
    store.create_source_revision(chapter.chapter_id, "backup source")
    supplier = store.create_supplier(slug="backup-supplier", display_name="Backup Supplier")
    install_test_supplier_runtime(store, supplier, rate_bucket="backup-local")
    supplier = store.get_supplier(supplier.supplier_id)
    credentials = SupplierCredentialStore(store, data_root)
    credential = credentials.replace(
        supplier.supplier_id,
        "backup-secret-never-in-manifest",
        expected_revision=0,
    )
    model = create_model(
        store, supplier, capability="video", name="backup-video",
        catalog_revision=0, key="backup-video-model",
    )
    ModelBindingService(store).replace(
        project.project_id,
        defaults={"text": "", "image": "", "video": model.supplier_model_id},
        overrides={},
        expected_revision=0,
    )
    resolved = ModelResolver(store).resolve(project.project_id, "shot_video_generation")
    snapshot = SnapshotBuilder(store).build(
        resolved,
        credential_resolution_mode="current",
        resolved_credential_version_id=credential.credential_version_id,
        resolved_constraints={"offline": True},
        worker_limits={"timeout_seconds": 30, "max_output_bytes": 4 * 1024 * 1024},
    )
    active, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=supplier.supplier_id, capability="video", provider="m6:backup:video",
        job_type="video", project_id=project.project_id, chapter_id=chapter.chapter_id,
        shot_id="active-shot", prompt_revision_id="active-prompt",
        idempotency_key="backup-active", request={"prompt": "active"}, snapshot=snapshot,
    )
    store.transition_generation_job(active.job_id, "submitting")
    store.record_submission_attempt(active.job_id, state="accepted", provider_job_id="backup-active-video")
    store.commit_accepted_submission(active.job_id)
    store.transition_generation_job(active.job_id, "polling", next_poll_at="9999-01-01T00:00:00Z")
    completed, _ = store.enqueue_generation_job_with_snapshot(
        supplier_id=supplier.supplier_id, capability="video", provider="m6:backup:video",
        job_type="video", project_id=project.project_id, chapter_id=chapter.chapter_id,
        shot_id="completed-shot", prompt_revision_id="completed-prompt",
        idempotency_key="backup-completed", request={"prompt": "completed"}, snapshot=snapshot,
    )
    store.transition_generation_job(completed.job_id, "submitting")
    store.record_submission_attempt(completed.job_id, state="accepted", provider_job_id="backup-completed-video")
    store.commit_accepted_submission(completed.job_id)
    store.transition_generation_job(completed.job_id, "polling")
    media = b"backup-completed-mp4"
    media_object_id = runtime.write_bytes_object(media)
    metadata_object_id = runtime.write_text_object('{"provider":"local-fake"}')
    completed = store.complete_generation_job_with_result(
        job_id=completed.job_id, object_id=media_object_id, media_type="video/mp4",
        source_url="", source_url_state="source_url_expired",
        metadata_object_id=metadata_object_id,
    )
    asset = store.create_generated_asset(
        project_id=project.project_id, chapter_id=chapter.chapter_id,
        asset_type="shot_keyframe", name="Backup media", data=b"backup-image",
        media_type="image/png", source_job_id=completed.job_id,
        metadata={"offline": True},
    )
    orphan_object_id = runtime.write_text_object('{"orphan":"retained"}')
    return runtime, store, supplier, credential, {
        "active_job_id": active.job_id,
        "completed_job_id": completed.job_id,
        "result_id": completed.provider_result_id,
        "asset_id": asset.asset_id,
        "model_id": model.supplier_model_id,
        "orphan_object_id": orphan_object_id,
    }


def test_backup_restore_relocates_credentials_and_preserves_semantics(tmp_path):
    source = tmp_path / "source"
    runtime, store, supplier, credential, evidence = _seed(source)
    expected = semantic_store_summary(store)
    backup_root = tmp_path / "backup"

    manifest = M6BackupService(store, source).create(backup_root)
    manifest_text = manifest.path.read_text(encoding="utf-8")

    assert manifest.status == "verified"
    assert "backup-secret-never-in-manifest" not in manifest_text
    assert manifest.inventory_hash
    assert all(item.path.startswith("payload/") for item in manifest.files)

    restored_root = tmp_path / "restored"
    report = M6RestoreService().restore(manifest.path, restored_root)
    restored_runtime = RuntimeStore(restored_root / "runtime.db", restored_root / "objects")
    restored = ProductStore(restored_runtime)
    restored_supplier = restored.get_supplier(supplier.supplier_id)
    restored_credential = restored.get_credential_version(
        restored_supplier.current_credential_version_id
    )

    assert report.status == "verified"
    assert semantic_store_summary(restored) == expected
    assert Path(restored_credential.secret_path).is_relative_to(restored_root)
    assert Path(restored_credential.secret_path).is_file()
    assert oct(Path(restored_credential.secret_path).stat().st_mode & 0o777) == "0o600"
    assert SupplierCredentialStore(restored, restored_root).read(
        restored_credential.credential_version_id
    ) == "backup-secret-never-in-manifest"
    assert Path(credential.secret_path).is_file()
    assert restored.get_supplier_model(evidence["model_id"]) is not None
    assert restored.get_asset(evidence["asset_id"]) is not None
    assert restored.get_generation_result(evidence["result_id"]) is not None
    assert restored.runtime.object_path(evidence["orphan_object_id"]).is_file()

    class RestoreGateway:
        calls = []

        def invoke(self, _snapshot_hash, operation, payload):
            self.calls.append((operation, payload))
            if operation == "videoPoll":
                return {"status": "completed", "video_id": payload["video_id"]}
            if operation == "videoFetch":
                return {"media_type": "video/mp4", "bytes": b"restored-active-video"}
            raise AssertionError(operation)

    gateway = RestoreGateway()
    resumed = GenerationExecutionService(
        restored, restored_runtime, FakeGenerationBackend(), supplier_gateway=gateway,
        supplier_execution_enabled=True,
    ).refresh_job(evidence["active_job_id"])
    assert resumed.internal_status == "completed"
    assert resumed.provider_job_id == "backup-active-video"
    assert [operation for operation, _payload in gateway.calls] == ["videoPoll", "videoFetch"]


def test_restored_app_starts_and_secret_api_stays_write_only(tmp_path):
    source = tmp_path / "source"
    runtime, store, supplier, _credential, _evidence = _seed(source)
    manifest = M6BackupService(store, source).create(tmp_path / "backup")
    restored_root = tmp_path / "restored"
    M6RestoreService().restore(manifest.path, restored_root)
    runtime.close()

    with TestClient(
        create_app(data_root=restored_root, skills_root="skills"),
        client=("127.0.0.1", 50000),
    ) as client:
        detail = client.get(f"/api/suppliers/{supplier.supplier_id}")

    assert detail.status_code == 200
    assert detail.json()["credential"]["configured"] is True
    assert "backup-secret-never-in-manifest" not in detail.text


def test_restore_rejects_corrupt_backup_and_nonempty_destination(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, _credential, _evidence = _seed(source)
    manifest = M6BackupService(store, source).create(tmp_path / "backup")
    database = manifest.path.parent / "payload/runtime.db"
    database.write_bytes(database.read_bytes() + b"corrupt")

    with pytest.raises(BackupIntegrityError, match="BACKUP_HASH_MISMATCH"):
        M6RestoreService().restore(manifest.path, tmp_path / "restored")

    other_manifest = M6BackupService(store, source).create(tmp_path / "backup-two")
    destination = tmp_path / "occupied"
    destination.mkdir()
    (destination / "user-file").write_text("keep", encoding="utf-8")
    with pytest.raises(BackupIntegrityError, match="RESTORE_DESTINATION_NOT_EMPTY"):
        M6RestoreService().restore(other_manifest.path, destination)
    assert (destination / "user-file").read_text(encoding="utf-8") == "keep"


def test_restore_rejects_backup_member_mode_mismatch(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, credential, _evidence = _seed(source)
    manifest = M6BackupService(store, source).create(tmp_path / "backup")
    secret_member = manifest.path.parent / "payload" / Path(credential.secret_path).relative_to(source)
    secret_member.chmod(0o644)

    with pytest.raises(BackupIntegrityError, match="BACKUP_MODE_MISMATCH"):
        M6RestoreService().restore(manifest.path, tmp_path / "restored")


def test_backup_rejects_unsafe_source_credential_mode(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, credential, _evidence = _seed(source)
    Path(credential.secret_path).chmod(0o644)

    with pytest.raises(BackupIntegrityError, match="CREDENTIAL_BACKUP_UNSAFE"):
        M6BackupService(store, source).create(tmp_path / "backup")


def test_backup_and_restore_reject_recursive_path_overlap(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, _credential, _evidence = _seed(source)

    with pytest.raises(BackupIntegrityError, match="BACKUP_PATH_OVERLAP"):
        M6BackupService(store, source).create(source / "objects" / "nested-backup")

    manifest = M6BackupService(store, source).create(tmp_path / "backup")
    with pytest.raises(BackupIntegrityError, match="RESTORE_PATH_OVERLAP"):
        M6RestoreService().restore(
            manifest.path,
            manifest.path.parent / "payload" / "nested-restore",
        )


def test_backup_manifest_is_deterministic_and_contains_no_file_content(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, _credential, _evidence = _seed(source)
    first = M6BackupService(store, source).create(tmp_path / "backup-one")
    second = M6BackupService(store, source).create(tmp_path / "backup-two")

    first_payload = json.loads(first.path.read_text(encoding="utf-8"))
    second_payload = json.loads(second.path.read_text(encoding="utf-8"))
    for payload in (first_payload, second_payload):
        payload.pop("created_at")
        payload.pop("backup_root")

    assert first_payload == second_payload
    assert "content" not in first.path.read_text(encoding="utf-8").lower()


def test_backup_and_restore_cli_emit_sanitized_json(tmp_path):
    source = tmp_path / "source"
    runtime, _store, _supplier, _credential, _evidence = _seed(source)
    runtime.close()
    root = Path(__file__).resolve().parents[2]
    backup = subprocess.run(
        [
            sys.executable,
            "tools/backup_m6_store.py",
            "--data-root",
            str(source),
            "--destination",
            str(tmp_path / "backup"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert backup.returncode == 0, backup.stderr
    backup_payload = json.loads(backup.stdout)
    assert backup_payload["status"] == "verified"
    assert "backup-secret-never-in-manifest" not in backup.stdout

    restore = subprocess.run(
        [
            sys.executable,
            "tools/restore_m6_store.py",
            "--manifest",
            backup_payload["manifest"],
            "--destination",
            str(tmp_path / "restored"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert restore.returncode == 0, restore.stderr
    assert json.loads(restore.stdout)["status"] == "verified"
    assert "backup-secret-never-in-manifest" not in restore.stdout
