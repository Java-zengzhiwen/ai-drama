from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import selectors
import signal
import subprocess
import tempfile
import time


WORKER_PROTOCOL_VERSION = "2"
SUPPORTED_WORKER_PROTOCOL_VERSIONS = frozenset({"1", "2"})
SUPPORTED_HELPER_API_VERSIONS = frozenset(
    {"ai-drama-helper-v1", "ai-drama-helper-v2", "ai-drama-helper-v3"}
)
SUPPORTED_RUNTIME_PAIRS = frozenset(
    {
        ("1", "ai-drama-helper-v1"),
        ("1", "ai-drama-helper-v2"),
        ("2", "ai-drama-helper-v3"),
    }
)


def current_worker_runtime_version():
    result = subprocess.run(
        ["node", "--version"],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8", "TZ": "UTC"},
        timeout=5,
    )
    return result.stdout.strip()


@dataclass(frozen=True)
class WorkerLimits:
    timeout_seconds: float = 30.0
    max_request_bytes: int = 4 * 1024 * 1024
    max_output_bytes: int = 4 * 1024 * 1024
    max_media_bytes: int = 512 * 1024 * 1024


@dataclass(frozen=True)
class SupplierInvocationResult:
    value: object
    worker_protocol_version: str
    helper_api_version: str
    worker_runtime_version: str


class SupplierWorkerError(RuntimeError):
    def __init__(self, code, message, *, evidence=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.evidence = evidence if isinstance(evidence, dict) else {}


class SupplierWorker:
    def __init__(self, *, worker_entrypoint=None):
        self.worker_entrypoint = Path(worker_entrypoint) if worker_entrypoint else (
            Path(__file__).resolve().parents[2] / "worker" / "src" / "worker.ts"
        )

    def command(self):
        """Return a least-privilege Node command for trusted local adapters.

        The VM is an API-isolation layer, not a hostile-code sandbox. Node's
        permission model adds defense in depth by denying arbitrary host-file,
        child-process, and worker-thread access if adapter code escapes the VM.
        Network remains enabled only because the host-owned HTTP broker needs it.
        """
        temp_root = Path(tempfile.gettempdir()).resolve()
        source_root = self.worker_entrypoint.resolve().parent
        return [
            "node",
            "--permission",
            f"--allow-fs-read={source_root}",
            f"--allow-fs-write={temp_root}",
            "--allow-net",
            str(self.worker_entrypoint),
        ]

    def _protocol_version(self, artifact, worker_protocol_version=None):
        selected = worker_protocol_version or (
            "2" if artifact.helper_api_version == "ai-drama-helper-v3" else "1"
        )
        if (selected, artifact.helper_api_version) not in SUPPORTED_RUNTIME_PAIRS:
            raise SupplierWorkerError(
                "SUPPLIER_RUNTIME_UNAVAILABLE",
                "supplier runtime fingerprint is unavailable",
            )
        return selected

    def _request_bytes(
        self,
        artifact,
        operation,
        payload,
        *,
        mode,
        limits,
        worker_protocol_version,
    ):
        limits = limits or WorkerLimits()
        request = json.dumps(
            {
                "workerProtocolVersion": worker_protocol_version,
                "helperApiVersion": artifact.helper_api_version,
                "workerRuntimeVersion": artifact.worker_runtime_version,
                "compiledCode": artifact.compiled_code,
                "operation": operation,
                "payload": payload,
                "mode": mode,
                "timeoutMs": max(1, int(limits.timeout_seconds * 1000)),
                "maxOutputBytes": limits.max_output_bytes,
                "maxMediaBytes": limits.max_media_bytes,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(request) > limits.max_request_bytes:
            raise SupplierWorkerError("SUPPLIER_WORKER_REQUEST_TOO_LARGE", "supplier worker request too large")
        return request

    def _start_process(self):
        return subprocess.Popen(
            self.command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={
                "PATH": os.environ.get("PATH", ""),
                "LANG": "C.UTF-8",
                "TZ": "UTC",
                # Keep downloaded media inside the exact root validated by the
                # Python gateway without forwarding any supplier secrets.
                "TMPDIR": str(Path(tempfile.gettempdir()).resolve()),
            },
            start_new_session=True,
        )

    @staticmethod
    def _terminate_process_group(process):
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=0.2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()

    def invoke(
        self,
        artifact,
        operation,
        payload,
        *,
        mode="execution",
        limits=None,
        worker_protocol_version=None,
    ):
        limits = limits or WorkerLimits()
        protocol_version = self._protocol_version(artifact, worker_protocol_version)
        request = self._request_bytes(
            artifact,
            operation,
            payload,
            mode=mode,
            limits=limits,
            worker_protocol_version=protocol_version,
        )
        process = self._start_process()
        try:
            stdout, _stderr = process.communicate(request, timeout=limits.timeout_seconds)
        except subprocess.TimeoutExpired:
            self._terminate_process_group(process)
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
                evidence=error.get("evidence"),
            )
        if (
            response.get("workerProtocolVersion") != protocol_version
            or response.get("helperApiVersion") != artifact.helper_api_version
            or response.get("workerRuntimeVersion") != artifact.worker_runtime_version
        ):
            raise SupplierWorkerError(
                "SUPPLIER_RUNTIME_UNAVAILABLE", "supplier runtime fingerprint is unavailable"
            )
        return SupplierInvocationResult(
            value=response.get("value"),
            worker_protocol_version=response["workerProtocolVersion"],
            helper_api_version=response["helperApiVersion"],
            worker_runtime_version=response["workerRuntimeVersion"],
        )

    def invoke_stream(
        self,
        artifact,
        operation,
        payload,
        *,
        mode="execution",
        limits=None,
        worker_protocol_version=None,
    ):
        limits = limits or WorkerLimits()
        protocol_version = self._protocol_version(artifact, worker_protocol_version)
        if protocol_version != "2" or operation != "textStream":
            raise SupplierWorkerError(
                "SUPPLIER_RUNTIME_UNAVAILABLE",
                "supplier runtime fingerprint is unavailable",
            )
        request = self._request_bytes(
            artifact,
            operation,
            payload,
            mode=mode,
            limits=limits,
            worker_protocol_version=protocol_version,
        )
        process = self._start_process()
        deadline = time.monotonic() + limits.timeout_seconds
        expected_sequence = 0
        output_bytes = 0
        pending = bytearray()
        terminal_seen = False
        selector = selectors.DefaultSelector()
        try:
            try:
                process.stdin.write(request)
                process.stdin.close()
            except (BrokenPipeError, OSError) as exc:
                raise SupplierWorkerError(
                    "SUPPLIER_WORKER_EXITED", "supplier worker exited unexpectedly"
                ) from exc
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise SupplierWorkerError(
                        "SUPPLIER_WORKER_TIMEOUT", "supplier worker timed out"
                    )
                ready = selector.select(remaining)
                if not ready:
                    raise SupplierWorkerError(
                        "SUPPLIER_WORKER_TIMEOUT", "supplier worker timed out"
                    )
                chunk = os.read(process.stdout.fileno(), 64 * 1024)
                if not chunk:
                    if pending:
                        raise SupplierWorkerError(
                            "SUPPLIER_WORKER_PROTOCOL_ERROR",
                            "supplier worker returned malformed protocol",
                        )
                    if not terminal_seen:
                        raise SupplierWorkerError(
                            "SUPPLIER_WORKER_PROTOCOL_ERROR",
                            "supplier worker stream ended without a terminal frame",
                        )
                    break
                output_bytes += len(chunk)
                if output_bytes > limits.max_output_bytes:
                    raise SupplierWorkerError(
                        "SUPPLIER_WORKER_OUTPUT_TOO_LARGE",
                        "supplier worker output too large",
                    )
                pending.extend(chunk)
                while b"\n" in pending:
                    raw_line, _, remainder = pending.partition(b"\n")
                    pending = bytearray(remainder)
                    frame = self._decode_stream_frame(raw_line, expected_sequence)
                    expected_sequence += 1
                    terminal_seen = frame["type"] in {"completed", "failed"}
                    yield frame
                    if terminal_seen:
                        if pending.strip():
                            raise SupplierWorkerError(
                                "SUPPLIER_WORKER_PROTOCOL_ERROR",
                                "supplier worker emitted data after the terminal frame",
                            )
                        return
        finally:
            selector.close()
            self._terminate_process_group(process)

    @staticmethod
    def _decode_stream_frame(raw_line, expected_sequence):
        if not raw_line:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_PROTOCOL_ERROR", "supplier worker emitted an empty frame"
            )
        try:
            frame = json.loads(raw_line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_PROTOCOL_ERROR",
                "supplier worker returned malformed protocol",
            ) from exc
        if not isinstance(frame, dict) or frame.get("sequence") != expected_sequence:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_PROTOCOL_ERROR", "supplier worker stream sequence mismatch"
            )
        frame_type = frame.get("type")
        valid = False
        if frame_type == "started":
            valid = set(frame) == {"type", "sequence"}
        elif frame_type == "text_delta":
            valid = set(frame) == {"type", "sequence", "text"} and isinstance(
                frame.get("text"), str
            ) and bool(frame["text"])
        elif frame_type == "usage":
            usage = frame.get("usage")
            valid = (
                set(frame) == {"type", "sequence", "usage"}
                and isinstance(usage, dict)
                and all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                    for value in usage.values()
                )
            )
        elif frame_type == "completed":
            valid = set(frame) == {"type", "sequence", "evidence"} and isinstance(
                frame.get("evidence"), dict
            )
        elif frame_type == "failed":
            valid = (
                set(frame) == {"type", "sequence", "errorCode", "evidence"}
                and isinstance(frame.get("errorCode"), str)
                and bool(frame["errorCode"])
                and isinstance(frame.get("evidence"), dict)
            )
        if not valid:
            raise SupplierWorkerError(
                "SUPPLIER_WORKER_PROTOCOL_ERROR", "supplier worker emitted an invalid frame"
            )
        return frame
