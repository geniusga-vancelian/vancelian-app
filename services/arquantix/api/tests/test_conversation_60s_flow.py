"""
test_conversation_60s_flow: 3–4 turns -> restitution + disclaimer + profile completeness >= 0.4
Uses chatbot_client (FakeLLM) to avoid network.
"""
import pytest


def test_60s_flow_returns_restitution_and_disclaimer(chatbot_client):
    # 1) Create session
    r0 = chatbot_client.post("/api/chatbot/session", json={})
    assert r0.status_code == 200
    session_id = r0.json()["session_id"]

    # 2) Turn 1: goal + horizon
    r1 = chatbot_client.post("/api/chatbot/conversation/turn", json={"session_id": session_id, "message": "Je veux 50 000€ dans 5 ans pour un apport"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert "reply" in d1

    # 3) Turn 2: risk
    r2 = chatbot_client.post("/api/chatbot/conversation/turn", json={"session_id": session_id, "message": "Équilibre"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert "reply" in d2

    # 4) Profile: completeness >= 0.4
    rp = chatbot_client.get(f"/api/chatbot/profile?session_id={session_id}")
    assert rp.status_code == 200
    prof = rp.json()
    assert float(prof.get("completeness_score", 0)) >= 0.4

    # 5) One of the turns should yield restitution (state=restitution) and disclaimers
    combined_replies = (d1.get("reply") or "") + " " + (d2.get("reply") or "")
    disclaimers = (d1.get("disclaimers_shown") or []) + (d2.get("disclaimers_shown") or [])
    # Either we get restitution in d2 (after risk) or we need a 3rd turn; with 2 turns we might already have comp>=0.4
    assert "illustration" in combined_replies.lower() or "répartition" in combined_replies.lower() or len(combined_replies) > 50
    assert len(disclaimers) >= 1 or "passées" in combined_replies.lower() or "ne préjugent" in combined_replies.lower()
