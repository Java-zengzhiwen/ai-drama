from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

from .contracts import CompiledSupplierArtifact


COMPILER_OPTIONS = {
    "bundle": True,
    "format": "cjs",
    "platform": "neutral",
    "target": "es2022",
    "legalComments": "none",
    "sourcemap": False,
}


class SupplierCompileError(ValueError):
    def __init__(self, code, message, *, line=0, column=0):
        super().__init__(message)
        self.code = code
        self.message = message
        self.line = line
        self.column = column


def compile_supplier(source, *, runtime_store, worker_root=None):
    _reject_forbidden_source(source)
    root = Path(worker_root) if worker_root else Path(__file__).resolve().parents[2] / "worker"
    command = ["node", str(root / "src" / "compiler.mjs")]
    try:
        completed = subprocess.run(
            command,
            input=json.dumps({"source": source}, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
            env={
                "PATH": os.environ.get("PATH", ""),
                "LANG": "C.UTF-8",
                "TZ": "UTC",
            },
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SupplierCompileError("SUPPLIER_COMPILER_UNAVAILABLE", "supplier compiler unavailable") from exc
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SupplierCompileError("SUPPLIER_COMPILER_PROTOCOL_ERROR", "supplier compiler protocol error") from exc
    if not payload.get("ok"):
        error = payload.get("error") or {}
        raise SupplierCompileError(
            error.get("code", "TYPESCRIPT_COMPILE_FAILED"),
            str(error.get("message", "supplier compilation failed"))[:299],
            line=int(error.get("line") or 0),
            column=int(error.get("column") or 0),
        )

    compiled_code = payload["compiledCode"]
    vendor = payload["vendor"]
    source_object_id = runtime_store.write_text_object(source)
    compiled_artifact_object_id = runtime_store.write_text_object(compiled_code)
    manifest_json = _canonical_json(vendor)
    options_json = _canonical_json(COMPILER_OPTIONS)
    return CompiledSupplierArtifact(
        source_object_id=source_object_id,
        source_hash=_sha256(source),
        compiled_artifact_object_id=compiled_artifact_object_id,
        compiled_artifact_hash=_sha256(compiled_code),
        manifest_hash=_sha256(manifest_json),
        compiled_code=compiled_code,
        vendor=vendor,
        compiler_name="esbuild",
        compiler_version=payload["compilerVersion"],
        compiler_options_hash=_sha256(options_json),
        adapter_contract_version=vendor["adapterContractVersion"],
        helper_api_version=vendor["helperApiVersion"],
        worker_runtime_version=payload["workerRuntimeVersion"],
    )


def _reject_forbidden_source(source):
    executable_source = _without_comments(source)
    checks = (
        ("FORBIDDEN_IMPORT", re.compile(r"\bimport\s*(?:\(|[\s\w{*])"), "import"),
        ("FORBIDDEN_GLOBAL", re.compile(r"\brequire\s*\("), "require"),
        ("FORBIDDEN_GLOBAL", re.compile(r"\bprocess\b"), "process"),
        ("FORBIDDEN_GLOBAL", re.compile(r"\bfetch\s*\("), "fetch"),
        ("FORBIDDEN_GLOBAL", re.compile(r"\bWebSocket\b"), "WebSocket"),
    )
    for code, pattern, label in checks:
        match = pattern.search(executable_source)
        if match:
            line, column = _line_column(executable_source, match.start())
            raise SupplierCompileError(
                code,
                "supplier source uses forbidden construct: %s" % label,
                line=line,
                column=column,
            )


def _without_comments(source):
    """Blank JavaScript comments while preserving offsets and quoted URL text."""
    output = list(source)
    state = "code"
    quote = ""
    index = 0
    while index < len(source):
        char = source[index]
        following = source[index + 1] if index + 1 < len(source) else ""
        if state == "line_comment":
            if char == "\n":
                state = "code"
            else:
                output[index] = " "
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and following == "/":
                output[index] = " "
                output[index + 1] = " "
                state = "code"
                index += 2
                continue
            if char != "\n":
                output[index] = " "
            index += 1
            continue
        if state == "quoted":
            if char == "\\":
                index += 2
                continue
            if char == quote:
                state = "code"
            index += 1
            continue
        if char in {"'", '"', "`"}:
            state = "quoted"
            quote = char
            index += 1
            continue
        if char == "/" and following == "/":
            output[index] = " "
            output[index + 1] = " "
            state = "line_comment"
            index += 2
            continue
        if char == "/" and following == "*":
            output[index] = " "
            output[index + 1] = " "
            state = "block_comment"
            index += 2
            continue
        index += 1
    return "".join(output)


def _line_column(source, offset):
    line = source.count("\n", 0, offset) + 1
    last_newline = source.rfind("\n", 0, offset)
    return line, offset - last_newline


def _canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
