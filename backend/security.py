"""
Alpha-Guard — Request Protection
=================================
Per-client rate limiting for endpoints that spend external quota
(SEC bandwidth, Gemini tokens). In-memory, so limits are per process.
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from config import RATE_LIMIT_PER_MINUTE

_WINDOW_SECONDS = 60.0
_hits: dict[str, deque] = defaultdict(deque)


def _client_id(request: Request) -> str:
    # Render and most PaaS hosts put the real client first in X-Forwarded-For
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def reset_rate_limits() -> None:
    _hits.clear()


async def rate_limit(request: Request) -> None:
    """FastAPI dependency: sliding-window limit per client IP."""
    if RATE_LIMIT_PER_MINUTE <= 0:
        return

    now = time.monotonic()
    window = _hits[_client_id(request)]
    while window and now - window[0] > _WINDOW_SECONDS:
        window.popleft()

    if len(window) >= RATE_LIMIT_PER_MINUTE:
        retry_after = int(_WINDOW_SECONDS - (now - window[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_PER_MINUTE} analyses per minute. "
                   f"Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
    window.append(now)
