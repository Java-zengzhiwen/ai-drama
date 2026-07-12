import pytest

from ai_drama_runtime.store import RuntimeStore
from ai_drama_web.suppliers.compiler import SupplierCompileError, compile_supplier


VALID_SOURCE = """
export const vendor = {
  id: "custom-test",
  version: "1.0.0",
  name: "Custom Test",
  author: "Local",
  adapterContractVersion: "ai-drama-supplier-v1",
  helperApiVersion: "ai-drama-helper-v1",
  rateLimitBucketKey: "custom-test",
  inputs: [],
  inputValues: {},
  models: []
};

export async function textRequest(request: { prompt: string }) {
  return { text: request.prompt };
}
""".strip()


def _runtime(tmp_path):
    return RuntimeStore(tmp_path / "runtime.db", tmp_path / "objects")


def test_compile_supplier_is_deterministic_and_persists_immutable_artifacts(tmp_path):
    runtime = _runtime(tmp_path)

    first = compile_supplier(VALID_SOURCE, runtime_store=runtime)
    second = compile_supplier(VALID_SOURCE, runtime_store=runtime)

    assert first.source_hash == second.source_hash
    assert first.compiled_artifact_hash == second.compiled_artifact_hash
    assert first.manifest_hash == second.manifest_hash
    assert first.compiler_name == "esbuild"
    assert first.adapter_contract_version == "ai-drama-supplier-v1"
    assert first.helper_api_version == "ai-drama-helper-v1"
    assert first.vendor["name"] == "Custom Test"
    assert runtime.read_text(first.source_object_id) == VALID_SOURCE
    assert runtime.read_text(first.compiled_artifact_object_id) == first.compiled_code
    assert "credential" not in first.compiled_code.lower()


@pytest.mark.parametrize(
    "source,code",
    [
        ('import fs from "node:fs";\n' + VALID_SOURCE, "FORBIDDEN_IMPORT"),
        ('const value = require("node:fs");\n' + VALID_SOURCE, "FORBIDDEN_GLOBAL"),
        ("const value = process.env.HOME;\n" + VALID_SOURCE, "FORBIDDEN_GLOBAL"),
        ("const value = fetch('https://example.invalid');\n" + VALID_SOURCE, "FORBIDDEN_GLOBAL"),
    ],
)
def test_compile_supplier_rejects_imports_and_host_globals(tmp_path, source, code):
    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == code
    assert exc_info.value.line == 1
    assert exc_info.value.column >= 1
    assert "HOME" not in exc_info.value.message


def test_compile_supplier_returns_safe_line_column_diagnostic(tmp_path):
    source = VALID_SOURCE.replace("models: []", "models: [")

    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == "TYPESCRIPT_COMPILE_FAILED"
    assert exc_info.value.line > 0
    assert exc_info.value.column > 0
    assert len(exc_info.value.message) < 300


@pytest.mark.parametrize(
    "source,code",
    [
        (VALID_SOURCE.replace('id: "custom-test",', ""), "INVALID_VENDOR_MANIFEST"),
        (
            VALID_SOURCE.replace('rateLimitBucketKey: "custom-test"', 'rateLimitBucketKey: "bad bucket"'),
            "INVALID_VENDOR_MANIFEST",
        ),
        (VALID_SOURCE.replace("export const vendor", "const vendor"), "MISSING_VENDOR_EXPORT"),
    ],
)
def test_compile_supplier_validates_required_contract(tmp_path, source, code):
    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == code

