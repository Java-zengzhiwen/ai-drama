import asyncio
from dataclasses import dataclass

from ai_drama_runtime.store import RuntimeStore, now_iso
from ai_drama_web.providers.base import GenerationBackend
from ai_drama_web.services.generation_execution import GenerationExecutionService
from ai_drama_web.store import ProductStore
from ai_drama_web.suppliers.snapshots import load_snapshot, SupplierRuntimeUnavailable


@dataclass(frozen=True)
class PollerCycleResult:
    submitted: int = 0
    polled: int = 0
    skipped: int = 0
    submission_outcome_unknown: int = 0


class GenerationPoller:
    def __init__(
        self,
        product_store: ProductStore,
        runtime_store: RuntimeStore,
        backend: GenerationBackend,
        *,
        rpm: int,
        poll_interval_seconds: float,
        execution_service: GenerationExecutionService | None = None,
    ) -> None:
        if rpm <= 0:
            raise ValueError("rpm must be positive")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        self.product_store = product_store
        self.runtime_store = runtime_store
        self.backend = backend
        self.rpm = rpm
        self.poll_interval_seconds = poll_interval_seconds
        self.execution_service = execution_service or GenerationExecutionService(
            product_store,
            runtime_store,
            backend,
        )
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            await self.run_cycle()
            await asyncio.sleep(self.poll_interval_seconds)

    async def run_cycle(self) -> PollerCycleResult:
        self.execution_service.recover_submission_attempts()
        unknown = self._mark_orphaned_submitting()
        pollable_jobs, skipped = self._due_jobs_by_status("submitted", "polling")
        limited_pollable = self._rate_limited_jobs(pollable_jobs, mutate_unavailable=False)
        skipped += len(pollable_jobs) - len(limited_pollable)
        submitted = 0
        for job in self._rate_limited_jobs(self._jobs_by_status("queued")):
            self.execution_service.submit_queued_job(job.job_id)
            submitted += 1
        polled = 0
        for job in limited_pollable:
            self.execution_service.refresh_job(job.job_id)
            refreshed = self.product_store.get_generation_job(job.job_id)
            if refreshed is not None and refreshed.internal_status in {"submitted", "polling"}:
                self.product_store.transition_generation_job(
                    refreshed.job_id,
                    "polling",
                    next_poll_at=now_iso(),
                )
            polled += 1
        return PollerCycleResult(
            submitted=submitted,
            polled=polled,
            skipped=skipped,
            submission_outcome_unknown=unknown,
        )

    def _rate_limited_jobs(self, jobs, *, mutate_unavailable=True):
        counts = {}
        selected = []
        for job in jobs:
            bucket = "legacy:%s" % job.provider
            if job.snapshot_hash:
                try:
                    bucket = load_snapshot(self.product_store, job.snapshot_hash).rate_limit_bucket_key
                except SupplierRuntimeUnavailable:
                    if mutate_unavailable:
                        self.product_store.transition_generation_job(
                            job.job_id, "cancelled", error_code="SUPPLIER_RUNTIME_UNAVAILABLE",
                            error_message="supplier runtime is unavailable",
                        )
                        continue
                    bucket = "unavailable:%s" % job.snapshot_hash
            if counts.get(bucket, 0) >= self.rpm:
                continue
            counts[bucket] = counts.get(bucket, 0) + 1
            selected.append(job)
        return selected

    def _mark_orphaned_submitting(self) -> int:
        count = 0
        for job in self._jobs_by_status("submitting"):
            if not job.provider_job_id:
                attempt = self.product_store.get_submission_attempt(job.job_id)
                if attempt is not None and attempt["state"] == "accepted":
                    self.product_store.commit_accepted_submission(job.job_id)
                    continue
                self.product_store.transition_generation_job(
                    job.job_id,
                    "failed",
                    error_code="SUBMISSION_OUTCOME_UNKNOWN" if job.snapshot_hash else "submission_outcome_unknown",
                    error_message="video submission outcome is unknown",
                )
                count += 1
        return count

    def _jobs_by_status(self, *statuses: str):
        placeholders = ",".join("?" for _ in statuses)
        rows = self.product_store.conn.execute(
            f"""
            SELECT *
            FROM generation_jobs
            WHERE internal_status IN ({placeholders})
            ORDER BY created_at ASC, job_id ASC
            """,
            statuses,
        ).fetchall()
        from ai_drama_web.models import GenerationJobRecord

        return [GenerationJobRecord(**dict(row)) for row in rows]

    def _due_jobs_by_status(self, *statuses: str):
        jobs = self._jobs_by_status(*statuses)
        now = now_iso()
        due = [job for job in jobs if not job.next_poll_at or job.next_poll_at <= now]
        return due, len(jobs) - len(due)
