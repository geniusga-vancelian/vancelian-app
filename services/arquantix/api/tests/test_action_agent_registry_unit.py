"""Smoke — registre runtime agent ``action``."""


def test_action_agent_has_tools_registered():
    from services.assistance.agents.tools import registry as reg

    assert "action" in reg.TOOLS_BY_AGENT
    names = reg.all_tool_names("action")
    assert "deposit_present_channels" in names
    assert "crypto_buy_start" in names
    assert "crypto_sell_start" in names
    assert "crypto_swap_start" in names
    assert "bundle_invest_start" in names
    assert "ask_user_question" in names


def test_get_agent_returns_action_agent():
    from services.assistance.agents.registry import get_agent
    from services.assistance.agents.action import ActionAgent

    agent = get_agent("action")
    assert isinstance(agent, ActionAgent)


def test_known_agent_ids_includes_action():
    from services.assistance.agents.base import AGENT_ACTION_ID, KNOWN_AGENT_IDS

    assert AGENT_ACTION_ID == "action"
    assert "action" in KNOWN_AGENT_IDS
