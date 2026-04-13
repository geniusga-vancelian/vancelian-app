"""Deterministic request hashing for idempotency checks.

Produces a stable SHA-256 hex digest from arbitrary JSON-serializable data.
Same semantic payload always produces the same hash.
"""
import hashlib
import json
from typing import Any


def compute_request_hash(data: Any) -> str:
    canonical = json.dumps(data, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
