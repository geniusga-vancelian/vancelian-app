"""Admin read-only — options / parcours de l’agent ``action``.

Expose la documentation consolidée (tools + whitelist CTA) pour
l’espace Next ``/admin/assistance/agent-action-options``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from services.assistance.agent_action_options_catalog import (
    build_agent_action_options_payload,
)
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import (
    require_admin_or_ops,
)

admin_router = APIRouter(
    prefix="/api/admin/assistance/agent-action-options",
    tags=["assistance-agent-action-options"],
)
_guard = require_admin_or_ops()


class CtaKindRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str
    default_label: str
    deep_link_template: str
    available_phase_2b: bool
    requires_param: Optional[str] = None


class ActionToolAdminRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    title: str
    tool_description_llm: str
    autonomy_level: str
    client_flow_steps: list[str]
    related_cta_kinds: list[str] = Field(default_factory=list)


class AgentActionOptionsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_revision: str
    source_files_note: list[str]
    action_agent_tools: list[ActionToolAdminRow]
    cta_whitelist: list[CtaKindRow]


@admin_router.get("", response_model=AgentActionOptionsResponse)
def list_agent_action_options(
    _actor: ActorContext = Depends(_guard),
) -> AgentActionOptionsResponse:
    """Vue consolidée pour l’admin web."""

    payload = build_agent_action_options_payload()
    return AgentActionOptionsResponse(**payload)
