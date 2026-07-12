from dataclasses import dataclass
from pathlib import Path
import json
import os
import signal
import subprocess


@dataclass(frozen=True)
class WorkerLimits:
    timeout_seconds: float = 30.0
    max_request_bytes: int = 4 * 1024 * 1024
    max_output_bytes: int = 4 * 1024 * 1024


@dataclass(frozen=True)
class SupplierInvocationResult:
    value: object
    worker_protocol_version: str
    helper_api_version: str


class SupplierWorkerError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class SupplierWorker:
    def __init__(self, *, worker_entrypoint=None):
        self.worker_entrypoint = Path(worker_entrypoint) if worker_entrypoint else (
            Path(__file__).resolve().parents[2] / "worker" / "src" / "worker.ts"
        )

    def invoke(self, artifact, operation, payload, *, mode="execution", limits=None):
        limits = limits or WorkerLimits()
        request = json.dumps(
            {
                "workerProtocolVersion": "1",
                "helperApiVersion": artifact.helper_api_version,
                "compiledCode": artifact.compiled_code,
                "operation": operation,
                "payload": payload,
                "mode": mode,
                "timeoutMs": max(1, int(limits.timeout_seconds * 1000)),
                "maxOutputBytes": limits.max_output_bytes,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(request) > limits.max_request_bytes:
            raise SupplierWorkerError("SUPPLIER_WORKER_REQUEST_TOO_LARGE", "supplier worker request too large")

        process = subprocess.Popen(
            ["node", str(self.worker_entrypoint)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                "PATH": os.environ.get("PATH", ""),
                "LANG": "C.UTF-8",
                "TZ": "UTC",
            },
            start_new_session=True,
        )
        try:
            stdout, _stderr = process.communicate(request, timeout=limits.timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise SupplierWorkerError("SUPPLIER_WORKER_TIMEOUT", "supplier worker timed out")
        if len(stdout) > limits.max_output_bytes:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_OUTPUT_TOO_LARGE", "supplier worker output too large"
            )
        try:
            response = json.loads(stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_PROTOCOL_ERROR", "supplier worker returned malformed protocol"
            ) from exc
        if process.returncode != 0:
            raise SupplierWorkerError("SUPPLIER_WORKER_EXITED", "supplier worker exited unexpectedly")
        if not response.get("ok"):
            error = response.get("error") or {}
            raise SupplierWorkerError(
                error.get("code", "SUPPLIER_EXECUTION_FAILED"),
                str(error.get("message", "supplier operation failed"))[:299],
            )
        return SupplierInvocationResult(
            value=response.get("value"),
            worker_protocol_version=response["workerProtocolVersion"],
            helper_api_version=response["helperApiVersion"],
        )

