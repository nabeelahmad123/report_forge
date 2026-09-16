"""Minimal in-memory sliding-window rate limiter (spec §10: "simple in-memory
limiter is fine"). Per-process only — fine for a single-instance demo, not
meant to survive multiple workers/replicas."""

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True
