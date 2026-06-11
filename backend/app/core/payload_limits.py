"""Server-side caps for worker-supplied log/result/game-state payloads (M-3).

Worker callbacks (`PATCH /jobs/build`, `PATCH /matches/{id}`) accept logs and
arbitrary JSON dicts. These helpers bound the stored size so a worker (the only
caller able to reach those endpoints) cannot bloat the database or starve
SSE/API responses. Logs are truncated; oversized JSON payloads are rejected.
"""

import json
from typing import Any


_TRUNCATION_MARKER = "\n...[truncated]...\n"


class PayloadTooLargeError(ValueError):
    """Raised when a worker-supplied JSON payload exceeds its configured cap."""


def cap_log_append(existing: str, addition: str, *, append_cap: int, total_cap: int) -> str:
    """Append `addition` to `existing` log text, truncating per-append and total size.

    A single append larger than `append_cap` is clipped; if the combined log then
    exceeds `total_cap`, the oldest content is dropped so the most recent logs are
    kept. A cap of 0 disables that check.
    """
    if append_cap and len(addition) > append_cap:
        addition = addition[:append_cap] + _TRUNCATION_MARKER
    combined = existing + addition + "\n"
    if total_cap and len(combined) > total_cap:
        combined = _TRUNCATION_MARKER + combined[-total_cap:]
    return combined


def ensure_json_within(payload: Any, *, max_bytes: int, field_name: str) -> None:
    """Reject a JSON-serializable payload whose encoded size exceeds `max_bytes`.

    A cap of 0 disables the check.
    """
    if not max_bytes:
        return
    size = len(json.dumps(payload, default=str).encode("utf-8"))
    if size > max_bytes:
        raise PayloadTooLargeError(
            f"{field_name} payload is {size} bytes, exceeding the maximum of {max_bytes} bytes"
        )
