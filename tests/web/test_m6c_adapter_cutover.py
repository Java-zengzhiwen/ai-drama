import json

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.config import Settings
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.adapters import FakeSupplierAdapter, SupplierAdapterGateway, sanitize_evidence


def test_feature_flag_defaults_off():
    assert Settings().m6_supplier_execution_enabled is False


def test_fake_video_polls_video_id_and_submits_once():
    fake = FakeSupplierAdapter()
    gateway = SupplierAdapterGateway(fake, supplier_slug="fake")
    submitted = gateway.video_submit({"prompt": "p"})
    gateway.video_poll(submitted.value["video_id"])
    gateway.video_fetch(submitted.value["video_id"])
    assert submitted.value == {"video_id": "fake-video-1"}
    assert (fake.submit_count, fake.poll_count, fake.fetch_count) == (1, 1, 1)


def test_evidence_removes_secret_keys_and_signed_query():
    value = sanitize_evidence({"Authorization": "Bearer x", "url": "https://example.invalid/a?token=x"})
    assert value == {"url": "https://example.invalid/a"}


def test_m6c_migration_is_additive_and_replayable(tmp_path):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    store = ProductStore(runtime)
    ProductStore(runtime)
    columns = {row["name"] for row in store.conn.execute("PRAGMA table_info(generation_jobs)")}
    assert {"snapshot_hash", "snapshot_object_id", "source_job_id", "rerun_resolution_mode"} <= columns
    assert store.conn.execute("SELECT 1 FROM schema_migrations WHERE migration_id = 'm6c_adapter_cutover_v1'").fetchone()
    assert store.conn.execute("SELECT COUNT(*) FROM generation_submission_attempts").fetchone()[0] == 0
