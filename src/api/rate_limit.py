"""
接口级限流工具。
"""

import time
from collections import defaultdict


class SlidingWindowRateLimiter:
    """基于滑动窗口的内存限流器。"""

    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str, limit: int) -> bool:
        """在给定窗口和阈值下，判断请求是否允许通过。"""
        if limit <= 0:
            return True

        now = time.time()
        self._hits[key] = [t for t in self._hits[key] if now - t < self.window_seconds]
        if len(self._hits[key]) >= limit:
            return False

        self._hits[key].append(now)
        self._cleanup(now)
        return True

    def _cleanup(self, now: float) -> None:
        if len(self._hits) <= 10000:
            return
        stale_keys = [
            key
            for key, timestamps in self._hits.items()
            if not timestamps or now - timestamps[-1] > self.window_seconds * 5
        ]
        for key in stale_keys:
            del self._hits[key]

