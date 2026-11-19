"""Small in-memory sliding-window rate limiter (per token, or per IP when anonymous).
Single-process only; use Redis if you scale to multiple workers."""
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import AppError

_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(bucket: str, per_minute: int | None = None):
    def dependency(request: Request) -> None:
        limit = per_minute or get_settings().rate_limit_per_minute
        auth = request.headers.get("authorization", "")
        key = f"{bucket}:{auth[-24:] or (request.client.host if request.client else 'anon')}"
        now = time.monotonic()
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            raise AppError("Too many requests. Please wait a moment.", 429)
        q.append(now)

    return dependency
