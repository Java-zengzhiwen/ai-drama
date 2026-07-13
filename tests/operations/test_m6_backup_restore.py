import json
from pathlib import Path
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.operations.backup_restore import (
    BackupIntegrityError,
    M6BackupService,
    M6RestoreService,
    semantic_store_summary,
)
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import SupplierCredentialStore


def _seed(data_root):
    data_root.mkdir(parents=True)
    (data_root / ".m6e-temporary-root").write_text("test-only\n", encoding="utf-8")
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Backup project", description="semantic")
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)
    store.create_source_revision(chapter.chapter_id, "backup source")
    supplier = store.create_supplier(slug="backup-supplier", display_name="Backup Supplier")
    credentials = SupplierCredentialStore(store, data_root)
    credential = credentials.replace(
        supplier.supplier_id,
        "backup-secret-never-in-manifest",
        expected_revision=0,
    )
    return runtime, store, supplier, credential


def test_backup_restore_relocates_credentials_and_preserves_semantics(tmp_path):
    source = tmp_path / "source"
    runtime, store, supplier, credential = _seed(source)
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


def test_restored_app_starts_and_secret_api_stays_write_only(tmp_path):
    source = tmp_path / "source"
    runtime, store, supplier, _credential = _seed(source)
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
    _runtime, store, _supplier, _credential = _seed(source)
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


def test_backup_manifest_is_deterministic_and_contains_no_file_content(tmp_path):
    source = tmp_path / "source"
    _runtime, store, _supplier, _credential = _seed(source)
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
    runtime, _store, _supplier, _credential = _seed(source)
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
