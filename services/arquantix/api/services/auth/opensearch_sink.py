"""Export d’événements sécurité vers OpenSearch / Elasticsearch (index par jour)."""
from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("arquantix.auth.siem")


def push_opensearch_document(payload: Dict[str, Any]) -> bool:
    """
    Indexe un document via ``POST {OPENSEARCH_URL}/{index}/_doc``.
    """
    base = (os.getenv("OPENSEARCH_URL") or os.getenv("ELASTICSEARCH_URL") or "").rstrip("/")
    if not base:
        logger.debug("opensearch_sink skipped: no OPENSEARCH_URL")
        return False

    prefix = (os.getenv("OPENSEARCH_INDEX_PREFIX") or "auth-security-events").strip().strip("/")
    day = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    index = f"{prefix}-{day}"
    url = f"{base}/{index}/_doc"

    user = (os.getenv("OPENSEARCH_USER") or "").strip()
    pwd = (os.getenv("OPENSEARCH_PASSWORD") or "").strip()
    headers = {"Content-Type": "application/json"}
    if user and pwd:
        token = base64.b64encode(f"{user}:{pwd}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    data = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
            return 200 <= resp.getcode() < 300
    except urllib.error.HTTPError as e:
        logger.warning("opensearch_sink http_error %s %s", e.code, e.reason)
    except Exception as exc:  # noqa: BLE001
        logger.warning("opensearch_sink failed: %s", exc)
    return False
