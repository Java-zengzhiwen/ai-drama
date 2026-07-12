#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.middleware.local_management import is_local_management_request
from ai_drama_web.store import M6B_MODEL_CATALOG_MIGRATION_ID, ProductStore
from ai_drama_web.suppliers.idempotency import (
    SupplierIdempotencyConflict,
    SupplierIdempotencyStore,
    canonical_request_hash,
)
from ai_drama_web.suppliers.model_catalog import ModelCatalogService
from ai_drama_web.suppliers.models import stable_builtin_model_id
from ai_drama_web.suppliers.resolution import ModelBindingService, ModelResolutionError, ModelResolver
from ai_drama_web.suppliers.snapshots import SnapshotBuilder, persist_snapshot
from ai_drama_web.suppliers.compiler import compile_supplier
from ai_drama_web.suppliers.worker import SupplierWorker, SupplierWorkerError


def _request(host, headers=None):
    return SimpleNamespace(
        client=SimpleNamespace(host=host),
        headers=headers or {},
    )


def verify():
    checks = {}
    with tempfile.TemporaryDirectory(prefix="ai-drama-m6b-") as directory:
        root = Path(directory)
        runtime = RuntimeStore(root / "runtime.db", root / "objects")
        store = ProductStore(runtime)
        supplier = store.list_suppliers()[0]
        legacy_source = """
export const vendor = {
  id: "verifier", version: "1", name: "Verifier", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "verifier-bucket", inputs: [], inputValues: {},
  models: [{ providerModelName: "fake-base", displayName: "Fake Base", capability: "text" }]
};
export async function textRequest() { return { text: "fake" }; }
"""
        artifact = compile_supplier(legacy_source, runtime_store=runtime)
        store.replace_supplier_version(
            supplier.supplier_id,
            source_object_id=artifact.source_object_id,
            source_hash=artifact.source_hash,
            compiled_artifact_object_id=artifact.compiled_artifact_object_id,
            compiled_artifact_hash=artifact.compiled_artifact_hash,
            manifest_hash=artifact.manifest_hash,
            adapter_contract_version=artifact.adapter_contract_version,
            worker_protocol_version="1",
            worker_runtime_version=artifact.worker_runtime_version,
            compiler_name=artifact.compiler_name,
            compiler_version=artifact.compiler_version,
            compiler_options_hash=artifact.compiler_options_hash,
            helper_api_version=artifact.helper_api_version,
            expected_revision=supplier.revision,
        )
        runtime.conn.execute("DELETE FROM supplier_model_revisions")
        runtime.conn.execute("DELETE FROM supplier_models")
        runtime.conn.execute(
            "DELETE FROM schema_migrations WHERE migration_id = ?",
            (M6B_MODEL_CATALOG_MIGRATION_ID,),
        )
        runtime.conn.commit()
        runtime.close()

        runtime = RuntimeStore(root / "runtime.db", root / "objects")
        store = ProductStore(runtime)
        supplier = store.get_supplier(supplier.supplier_id)
        base = store.list_supplier_models(supplier.supplier_id)[0]
        identity = stable_builtin_model_id(supplier.supplier_id, "text:fake-base")
        checks["stable_identities"] = "PASS" if base.supplier_model_id == identity else "FAIL"

        catalog = ModelCatalogService(store)
        default, _ = catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="fake-default",
            display_name="Fake Default",
            capability="text",
            definition={"constraints": {}},
            expected_catalog_revision=1,
            idempotency_key="default",
        )
        old_revision_id = default.current_model_revision_id
        default = catalog.revise_model(
            default.supplier_model_id,
            provider_model_name="fake-default-v2",
            display_name="Fake Default V2",
            capability="text",
            definition={"constraints": {"temperature": 1}},
            expected_catalog_revision=2,
            expected_model_revision=1,
            acknowledged_binding_count=0,
        )
        checks["immutable_revisions"] = "PASS" if (
            old_revision_id != default.current_model_revision_id
            and store.get_supplier_model_revision(old_revision_id).provider_model_name == "fake-default"
        ) else "FAIL"
        checks["overlay_base_isolation"] = "PASS" if (
            base.source == "built_in"
            and default.source == "overlay"
            and base.supplier_model_id != default.supplier_model_id
        ) else "FAIL"
        checks["catalog_etag"] = "PASS" if store.get_supplier(supplier.supplier_id).model_catalog_revision == 3 else "FAIL"

        override, _ = catalog.create_overlay(
            supplier.supplier_id,
            provider_model_name="fake-override",
            display_name="Fake Override",
            capability="text",
            definition={},
            expected_catalog_revision=3,
            idempotency_key="override",
        )
        project = store.create_project(name="M6B verifier")
        bindings = ModelBindingService(store)
        bindings.replace(
            project.project_id,
            defaults={"text": default.supplier_model_id, "image": "", "video": ""},
            overrides={"storyboard_design": override.supplier_model_id},
            expected_revision=0,
        )
        resolver = ModelResolver(store)
        inherited = resolver.resolve(project.project_id, "script_adaptation")
        specific = resolver.resolve(project.project_id, "storyboard_design")
        checks["project_defaults"] = "PASS" if inherited.model.supplier_model_id == default.supplier_model_id else "FAIL"
        checks["operation_override"] = "PASS" if specific.model.supplier_model_id == override.supplier_model_id else "FAIL"
        missing_project = store.create_project(name="Missing")
        try:
            resolver.resolve(missing_project.project_id, "shot_video_generation")
            checks["fail_closed_resolution"] = "FAIL"
        except ModelResolutionError as exc:
            checks["fail_closed_resolution"] = "PASS" if exc.code == "MODEL_BINDING_MISSING" else "FAIL"

        snapshot = SnapshotBuilder(store).build(
            inherited,
            credential_resolution_mode="current",
            resolved_credential_version_id="",
            resolved_constraints={},
            worker_limits={"timeout_seconds": 30},
            created_at="2026-07-13T00:00:00.000000Z",
        )
        snapshot_record = persist_snapshot(store, snapshot)
        checks["snapshot_hash"] = "PASS" if len(snapshot_record.snapshot_hash) == 64 else "FAIL"

        idem = SupplierIdempotencyStore(store)
        first_hash = canonical_request_hash({"prompt": "fake"}, snapshot_record.snapshot_hash)
        idem.claim(supplier.supplier_id, "text", "verifier-key", first_hash, "fake-job")
        try:
            idem.claim(
                supplier.supplier_id,
                "text",
                "verifier-key",
                canonical_request_hash({"prompt": "changed"}, snapshot_record.snapshot_hash),
                "other-job",
            )
            checks["idempotency_conflict"] = "FAIL"
        except SupplierIdempotencyConflict:
            checks["idempotency_conflict"] = "PASS"

        checks["loopback_guard"] = "PASS" if (
            is_local_management_request(_request("127.0.0.1"))
            and not is_local_management_request(
                _request("198.51.100.10", {"x-forwarded-for": "127.0.0.1"})
            )
        ) else "FAIL"
        network_source = """
export const vendor = {
  id: "network", version: "1", name: "Network", author: "Test",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "network", inputs: [], inputValues: {},
  models: [{ providerModelName: "network-text", displayName: "Network Text", capability: "text" }]
};
export async function textRequest(_request, helpers) { return helpers.http.request({ url: "https://example.invalid" }); }
"""
        network_artifact = compile_supplier(network_source, runtime_store=runtime)
        try:
            SupplierWorker().invoke(network_artifact, "textRequest", {}, mode="validation")
            checks["zero_real_network"] = "FAIL"
        except SupplierWorkerError as exc:
            checks["zero_real_network"] = "PASS" if exc.code == "NETWORK_DISABLED_DURING_VALIDATION" else "FAIL"
        legacy_sql = runtime.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'generation_jobs'"
        ).fetchone()["sql"]
        checks["m1_m5_regression"] = "PASS" if (
            "UNIQUE(provider, idempotency_key)" in legacy_sql
            and store.get_project(project.project_id) is not None
        ) else "FAIL"
        runtime.close()

        runtime = RuntimeStore(root / "runtime.db", root / "objects")
        replay = ProductStore(runtime)
        migration_count = runtime.conn.execute(
            "SELECT COUNT(*) AS n FROM schema_migrations WHERE migration_id = ?",
            (M6B_MODEL_CATALOG_MIGRATION_ID,),
        ).fetchone()["n"]
        checks["migration_replay"] = "PASS" if (
            migration_count == 1
            and replay.get_project(project.project_id)
            and replay.get_supplier_model(base.supplier_model_id)
        ) else "FAIL"
        runtime.close()

    result = "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL"
    return {
        "schema_version": "m6b-model-catalog-binding-verification-v1",
        "result": result,
        "checks": checks,
        "real_request_counts": {"text": 0, "image": 0, "video": 0},
    }


def _markdown(report):
    lines = [
        "# M6B Model Catalog And Binding Verification",
        "",
        "Result: `%s`" % report["result"],
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    lines.extend("| `%s` | %s |" % item for item in report["checks"].items())
    lines.extend(
        [
            "",
            "Real request counts: text=0, image=0, video=0.",
            "",
        ]
    )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output")
    parser.add_argument("--markdown-output")
    args = parser.parse_args()
    report = verify()
    if args.json_output:
        Path(args.json_output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if args.markdown_output:
        Path(args.markdown_output).write_text(_markdown(report))
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
