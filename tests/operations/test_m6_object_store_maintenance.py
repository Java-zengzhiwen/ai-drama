import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.operations.backup_restore import M6BackupService, M6RestoreService
from ai_drama_web.operations.object_store_maintenance import (
    GCGuardError,
    ObjectGarbageCollector,
    ObjectInventory,
)
from ai_drama_web.store import ProductStore


def _fixture(tmp_path):
    data_root = tmp_path / "m6e-temp-store"
    data_root.mkdir()
    (data_root / ".m6e-temporary-root").write_text("test-only\n", encoding="utf-8")
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    store = ProductStore(runtime)
    project = store.create_project(name="Inventory")
    chapter = store.create_chapter(project.project_id, title="Chapter", position=1)
    source = store.create_source_revision(chapter.chapter_id, "protected source")
    orphan_json = runtime.write_text_object('{"orphan":true}')
    unknown = runtime.write_bytes_object(b"\x00\x01\x02unclassified")
    corrupt = runtime.write_text_object("will be corrupt")
    runtime.object_path(corrupt).write_text("changed", encoding="utf-8")
    old = time.time() - 3600
    for object_id in (orphan_json, unknown, corrupt):
        os.utime(runtime.object_path(object_id), (old, old))
    return data_root, runtime, store, source.object_id, orphan_json, unknown, corrupt


def _backup_manifest(store, data_root, name="backup"):
    return M6BackupService(store, data_root).create(data_root.parent / name).path


def test_inventory_protects_db_references_and_classifies_safe_candidates(tmp_path):
    data_root, runtime, store, protected, orphan_json, unknown, corrupt = _fixture(tmp_path)

    report = ObjectInventory(store, data_root).build(grace_seconds=300)
    entries = {item.object_id: item for item in report.entries}

    assert entries[protected].referenced is True
    assert entries[protected].candidate is False
    assert entries[orphan_json].kind == "json"
    assert entries[orphan_json].candidate is True
    assert entries[unknown].kind == "unknown"
    assert entries[unknown].candidate is False
    assert entries[corrupt].corrupt is True
    assert entries[corrupt].candidate is False
    assert report.candidate_count == 1
    assert report.candidate_bytes == runtime.object_path(orphan_json).stat().st_size
    assert report.inventory_hash


def test_inventory_identity_is_independent_of_gc_grace_policy(tmp_path):
    data_root, _runtime, store, _protected, _orphan_json, _unknown, _corrupt = _fixture(tmp_path)

    immediate = ObjectInventory(store, data_root).build(grace_seconds=0)
    deferred = ObjectInventory(store, data_root).build(grace_seconds=24 * 60 * 60)

    assert immediate.candidate_count != deferred.candidate_count
    assert immediate.inventory_hash == deferred.inventory_hash


def test_gc_is_dry_run_by_default_and_apply_requires_all_guards(tmp_path):
    data_root, runtime, store, _protected, orphan_json, _unknown, _corrupt = _fixture(tmp_path)
    collector = ObjectGarbageCollector(store, data_root)
    plan = collector.plan(grace_seconds=300)

    dry_run = collector.run(grace_seconds=300)
    assert dry_run.applied is False
    assert runtime.object_path(orphan_json).exists()

    with pytest.raises(GCGuardError, match="BACKUP_REQUIRED"):
        collector.apply(plan.inventory_hash, backup_manifest=None, grace_seconds=300)

    manifest = _backup_manifest(store, data_root)
    runtime.write_text_object('{"new":"object"}')
    with pytest.raises(GCGuardError, match="INVENTORY_CHANGED"):
        collector.apply(plan.inventory_hash, backup_manifest=manifest, grace_seconds=300)


def test_gc_apply_deletes_only_planned_objects_in_marked_temp_root(tmp_path):
    data_root, runtime, store, protected, orphan_json, unknown, corrupt = _fixture(tmp_path)
    collector = ObjectGarbageCollector(store, data_root)
    plan = collector.plan(grace_seconds=300)
    manifest = _backup_manifest(store, data_root)

    result = collector.apply(
        plan.inventory_hash,
        backup_manifest=manifest,
        grace_seconds=300,
    )

    assert result.applied is True
    assert result.deleted_count == 1
    assert not runtime.object_path(orphan_json).exists()
    for object_id in (protected, unknown, corrupt):
        assert runtime.object_path(object_id).exists()
    restored = data_root.parent / "restored-after-gc"
    assert M6RestoreService().restore(manifest, restored).status == "verified"


def test_gc_apply_rejects_unmarked_root(tmp_path):
    data_root, runtime, store, _protected, _orphan_json, _unknown, _corrupt = _fixture(tmp_path)
    (data_root / ".m6e-temporary-root").unlink()
    collector = ObjectGarbageCollector(store, data_root)
    plan = collector.plan(grace_seconds=300)
    manifest = _backup_manifest(store, data_root)

    with pytest.raises(GCGuardError, match="TEMPORARY_ROOT_REQUIRED"):
        collector.apply(plan.inventory_hash, backup_manifest=manifest, grace_seconds=300)


def test_gc_rejects_self_declared_manifest_without_verified_payload(tmp_path):
    data_root, runtime, store, _protected, orphan_json, _unknown, _corrupt = _fixture(tmp_path)
    collector = ObjectGarbageCollector(store, data_root)
    plan = collector.plan(grace_seconds=300)
    forged = data_root / "forged-manifest.json"
    forged.write_text(
        json.dumps(
            {
                "schema_version": "m6-backup-v1",
                "status": "verified",
                "source_data_root": str(data_root.resolve()),
                "inventory_hash": plan.inventory_hash,
                "files": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(GCGuardError, match="BACKUP_INVALID"):
        collector.apply(plan.inventory_hash, backup_manifest=forged, grace_seconds=300)
    assert runtime.object_path(orphan_json).is_file()


def test_inventory_and_gc_cli_default_to_read_only_json(tmp_path):
    data_root, runtime, _store, _protected, orphan_json, _unknown, _corrupt = _fixture(tmp_path)
    root = Path(__file__).resolve().parents[2]
    inventory = subprocess.run(
        [
            sys.executable,
            "tools/inventory_object_store.py",
            "--data-root",
            str(data_root),
            "--grace-seconds",
            "300",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    gc = subprocess.run(
        [
            sys.executable,
            "tools/gc_object_store.py",
            "--data-root",
            str(data_root),
            "--grace-seconds",
            "300",
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )

    assert inventory.returncode == 0, inventory.stderr
    assert json.loads(inventory.stdout)["candidate_count"] == 1
    assert gc.returncode == 0, gc.stderr
    assert json.loads(gc.stdout)["applied"] is False
    assert runtime.object_path(orphan_json).exists()
