from collections import defaultdict, deque
import threading
import time


class SupplierRateLimiter:
    """Thread-safe rolling-minute limiter shared by snapshot bucket identity."""

    def __init__(self, rpm, *, clock=None):
        if int(rpm) <= 0:
            raise ValueError("rpm must be positive")
        self.default_rpm = int(rpm)
        self.clock = clock or time.monotonic
        self._events = defaultdict(deque)
        self._limits = {}
        self._lock = threading.Lock()

    def acquire(self, bucket, *, rpm=None):
        if not isinstance(bucket, str) or not bucket:
            raise ValueError("rate-limit bucket must be non-empty")
        requested_limit = self.default_rpm if rpm is None else int(rpm)
        if requested_limit <= 0:
            raise ValueError("rpm must be positive")
        now = float(self.clock())
        threshold = now - 60.0
        with self._lock:
            limit = min(self._limits.get(bucket, requested_limit), requested_limit)
            self._limits[bucket] = limit
            events = self._events[bucket]
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= limit:
                return False
            events.append(now)
            return True

    def release(self, bucket):
        """Return the latest reservation when enqueue resolves to an idempotent replay."""
        with self._lock:
            events = self._events.get(bucket)
            if not events:
                return False
            events.pop()
            if not events:
                self._events.pop(bucket, None)
            return True
