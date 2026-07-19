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


def test_compiler_accepts_media_helper_v2_without_changing_legacy_v1(tmp_path):
    upgraded = compile_supplier(
        VALID_SOURCE.replace("ai-drama-helper-v1", "ai-drama-helper-v2"),
        runtime_store=_runtime(tmp_path),
    )

    assert upgraded.helper_api_version == "ai-drama-helper-v2"


def test_compiler_accepts_manifest_select_with_unique_string_options(tmp_path):
    source = VALID_SOURCE.replace(
        "inputs: []",
        '''inputs: [{
          key: "reasoning_effort",
          label: "默认思考深度",
          type: "select",
          required: true,
          options: [
            { value: "low", label: "低" },
            { value: "medium", label: "中" },
            { value: "high", label: "高" }
          ]
        }]''',
    ).replace("inputValues: {}", 'inputValues: { reasoning_effort: "medium" }')

    artifact = compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert artifact.vendor["inputs"][0]["type"] == "select"
    assert [item["value"] for item in artifact.vendor["inputs"][0]["options"]] == [
        "low", "medium", "high"
    ]


@pytest.mark.parametrize(
    "options",
    [
        '[{ value: "medium", label: "中" }, { value: "medium", label: "重复" }]',
        '[{ value: "", label: "空值" }]',
        '[{ value: "medium", label: "" }]',
        '[]',
    ],
)
def test_compiler_rejects_malformed_manifest_select_options(tmp_path, options):
    source = VALID_SOURCE.replace(
        "inputs: []",
        f'''inputs: [{{
          key: "reasoning_effort",
          label: "默认思考深度",
          type: "select",
          options: {options}
        }}]''',
    )

    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == "INVALID_VENDOR_MANIFEST"


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


def test_compile_validation_blocks_constructor_chain_host_escape(tmp_path):
    source = (
        "const host = module.constructor.constructor('return pro' + 'cess')();\n"
        + VALID_SOURCE
    )

    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == "SUPPLIER_VALIDATION_FAILED"
    assert "process" not in exc_info.value.message.lower()


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


def test_compile_supplier_requires_exports_for_declared_model_capabilities(tmp_path):
    source = VALID_SOURCE.replace(
        "models: []",
        'models: [{ supplierModelId: "model-1", providerModelName: "model-1", '
        'displayName: "Model 1", capability: "text" }]',
    ).replace(
        "export async function textRequest(request: { prompt: string }) {\n"
        "  return { text: request.prompt };\n"
        "}",
        "",
    )

    with pytest.raises(SupplierCompileError) as exc_info:
        compile_supplier(source, runtime_store=_runtime(tmp_path))

    assert exc_info.value.code == "MISSING_RUNTIME_EXPORT"
