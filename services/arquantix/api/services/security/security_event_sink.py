"""
Abstraction d’export SIEM (Datadog, OpenSearch, noop).

Variable : ``SECURITY_EVENTS_SINK=datadog|opensearch|elasticsearch|elastic|none``.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

from services.security.security_env import security_events_sink_name

logger = logging.getLogger("arquantix.security.siem.sink")


class SecurityEventSink(ABC):
    """Push un payload JSON normalisé vers le backend SIEM."""

    @abstractmethod
    def push(self, payload: Dict[str, Any]) -> bool:
        raise NotImplementedError


class DatadogSink(SecurityEventSink):
    def push(self, payload: Dict[str, Any]) -> bool:
        from services.auth.datadog_sink import push_datadog_log

        return push_datadog_log(payload)


class OpenSearchSink(SecurityEventSink):
    def push(self, payload: Dict[str, Any]) -> bool:
        from services.auth.opensearch_sink import push_opensearch_document

        return push_opensearch_document(payload)


class NoopSink(SecurityEventSink):
    def push(self, payload: Dict[str, Any]) -> bool:
        logger.debug("siem.noop event_type=%s", payload.get("event_type"))
        return True


def get_security_event_sink() -> SecurityEventSink:
    name = security_events_sink_name()
    if name == "datadog":
        return DatadogSink()
    if name in ("opensearch", "elasticsearch", "elastic"):
        return OpenSearchSink()
    if name not in ("none", "", "off", "false"):
        logger.warning("unknown SECURITY_EVENTS_SINK=%r, using noop", name)
    return NoopSink()
