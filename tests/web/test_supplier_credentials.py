import os

import pytest
from fastapi.testclient import TestClient

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.app import create_app
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.credentials import SupplierCredentialStore


class SimulatedCrash(RuntimeError):
    pass


def _stores(tmp_path, crash_after=None):
    runtime = RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")
    product = ProductStore(runtime)
    supplier = product.create_supplier(slug="credential-test", display_name="Credential Test")

    def checkpoint(name):
        if name == crash_after:
            raise SimulatedCrash(name)

    credentials = SupplierCredentialStore(
        product,
        tmp_path / "runtime-data",
        checkpoint=checkpoint,
    )
    return runtime, product, supplier, credentials


@pytest.mark.parametrize(
    "crash_after,expected_ready",
    [
        ("journal_created", False),
        ("temp_written", False),
        ("pending_committed", True),
        ("renamed", True),
        ("ready_committed", True),
    ],
)
def test_replace_recovers_after_each_crash_boundary(tmp_path, crash_after, expected_ready):
    runtime, product, supplier, credentials = _stores(tmp_path, crash_after)

    with pytest.raises(SimulatedCrash):
        credentials.replace(supplier.supplier_id, "credential-value", expected_revision=0)

    recovered = SupplierCredentialStore(product, tmp_path / "runtime-data").recover()
    replayed = SupplierCredentialStore(product, tmp_path / "runtime-data").recover()
    current = product.get_supplier(supplier.supplier_id)

    if expected_ready:
        assert current.current_credential_version_id
        record = credentials.get(current.current_credential_version_id)
        assert record.state == "ready"
        assert credentials.read(record.credential_version_id) == "credential-value"
        assert os.stat(record.secret_path).st_mode & 0o777 == 0o600
        assert recovered.ready == 1
    else:
        assert current.current_credential_version_id == ""
        assert recovered.ready == 0
    assert replayed.ready == 0
    assert replayed.corrupt == 0
    assert "credential-value" not in repr(recovered)


def test_recovery_marks_missing_pending_file_corrupt_and_fails_closed(tmp_path):
    _, product, supplier, credentials = _stores(tmp_path, "pending_committed")
    with pytest.raises(SimulatedCrash):
        credentials.replace(supplier.supplier_id, "credential-value", expected_revision=0)
    current = product.get_supplier(supplier.supplier_id)
    record = credentials.get(current.current_credential_version_id)
    for path in (record.secret_path, credentials.temp_path(record.credential_version_id)):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    report = SupplierCredentialStore(product, tmp_path / "runtime-data").recover()

    assert report.corrupt == 1
    assert credentials.get(record.credential_version_id).state == "credential_storage_corrupt"
    with pytest.raises(RuntimeError, match="CREDENTIAL_STORAGE_CORRUPT"):
        credentials.read(record.credential_version_id)


def test_delete_is_recovered_idempotently(tmp_path):
    _, product, supplier, credentials = _stores(tmp_path)
    created = credentials.replace(supplier.supplier_id, "credential-value", expected_revision=0)
    credentials._checkpoint = lambda name: (_ for _ in ()).throw(SimulatedCrash(name)) \
        if name == "delete_file_removed" else None

    with pytest.raises(SimulatedCrash):
        credentials.delete(supplier.supplier_id, expected_revision=1)

    recovery_store = SupplierCredentialStore(product, tmp_path / "runtime-data")
    first = recovery_store.recover()
    second = recovery_store.recover()

    assert first.deleted == 1
    assert second.deleted == 0
    assert product.get_supplier(supplier.supplier_id).current_credential_version_id == ""
    assert recovery_store.get(created.credential_version_id) is None


def test_recovery_removes_unreferenced_temp_orphans(tmp_path):
    _, product, _, credentials = _stores(tmp_path)
    orphan = credentials.secrets_root / ".orphan.tmp"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_text("not-a-real-secret", encoding="utf-8")

    report = credentials.recover(orphan_grace_seconds=0)

    assert report.orphans_removed == 1
    assert not orphan.exists()


def test_app_recovers_supplier_credentials_before_runtime_start(tmp_path):
    data_root = tmp_path / "runtime-data"
    runtime = RuntimeStore(data_root / "runtime.db", data_root / "objects")
    product = ProductStore(runtime)
    supplier = product.create_supplier(slug="startup", display_name="Startup")
    credentials = SupplierCredentialStore(
        product,
        data_root,
        checkpoint=lambda name: (_ for _ in ()).throw(SimulatedCrash(name))
        if name == "pending_committed"
        else None,
    )
    with pytest.raises(SimulatedCrash):
        credentials.replace(supplier.supplier_id, "credential-value", expected_revision=0)
    runtime.close()

    app = create_app(data_root=data_root, skills_root="skills")
    with TestClient(app) as client:
        state = client.portal.call(
            lambda: (
                app.state.supplier_credential_store.get(
                    app.state.product_store.get_supplier(
                        supplier.supplier_id
                    ).current_credential_version_id
                ).state,
                app.state.supplier_credential_recovery.ready,
            )
        )
        assert state == ("ready", 1)
