"""Tests module ``deterministic_intake`` — signaux ACHAT crypto depuis le brut."""

from __future__ import annotations

from services.assistance.agents.tools.shared import deterministic_intake as di


def test_extract_trade_1000_eur_bitcoin():
    extract = di.extract_intake_signals(
        "crypto_buy",
        "fais moi un trade de 1000€ en bitcoin",
    )
    assert extract["symbol"] == "BTC"
    assert extract["amount_from"] == 1000.0


def test_compound_symbol_prefers_crypto_mentioned_in_user_tail():
    compound = (
        "[RÉPONSE ASSISTANT PRÉCÉDENTE – référencée pour résoudre le tour courant]\n"
        "Ethereum est très volatil en ce moment.\n"
        "[DEMANDE / RÉPONSE UTILISATEUR SUR CE TOUR]\n"
        "Je veux plutôt investir 500 € dans du Bitcoin."
    )
    extract = di.extract_intake_signals("crypto_buy", compound)
    assert extract["symbol"] == "BTC"
    assert extract["amount_from"] == 500.0
    assert extract["currency_from"] == "EUR"
    assert "amount:500.0" in extract["_signals"]


def test_merge_text_amount_overrides_tool_when_both_present():
    merged = di.merge_crypto_buy_intake(
        tool_symbol="ETH",
        tool_amount_from=5.0,
        tool_currency_from="USD",
        signals={
            "symbol": "BTC",
            "amount_from": 1000.0,
            "currency_from": "EUR",
            "_signals": [],
        },
        pending_action=None,
        current_topic=None,
    )
    assert merged["symbol"] == "BTC"
    assert merged["amount_from"] == 1000.0
    assert merged["currency_from"] == "EUR"


def test_merge_pending_fills_when_text_empty_but_tool_weak():
    merged = di.merge_crypto_buy_intake(
        tool_symbol=None,
        tool_amount_from=None,
        tool_currency_from=None,
        signals={},
        pending_action={
            "target_kind": "crypto_buy",
            "target_id": "BTC",
            "amount_from": 750,
            "currency_from": "EUR",
        },
        current_topic=None,
    )
    assert merged["symbol"] == "BTC"
    assert merged["amount_from"] == 750


def test_topic_instrument_fallback():
    merged = di.merge_crypto_buy_intake(
        tool_symbol=None,
        tool_amount_from=None,
        tool_currency_from=None,
        signals={"amount_from": 200.0, "currency_from": "EUR", "_signals": []},
        pending_action=None,
        current_topic={"kind": "instrument", "instrument_symbol": "SOL"},
    )
    assert merged["symbol"] == "SOL"
    assert merged["amount_from"] == 200.0


def test_resolve_intake_user_text_prefers_compound_turn():
    t = di.resolve_intake_user_text(
        user_message="je le suis",
        memory_state={"compound_user_turn": "Réponse précédente. Message court : oui BTC"},
        recent_turns=[],
    )
    assert "BTC" in t or "oui" in t


def test_merge_assistant_history_fills_symbol_on_amount_only_user():
    merged = di.merge_crypto_buy_intake(
        tool_symbol=None,
        tool_amount_from=None,
        tool_currency_from=None,
        signals={
            "amount_from": 1000.0,
            "currency_from": "EUR",
            "_signals": [],
        },
        pending_action=None,
        current_topic=None,
        recent_turns=[
            {
                "role": "assistant",
                "content": "Pour acheter du Bitcoin confirmez le montant.",
            },
            {"role": "user", "content": "1000€"},
        ],
    )
    assert merged["symbol"] == "BTC"
    assert merged["merge_sources"]["symbol"] == "assistant_history"


def test_compound_user_turn_prioritizes_tail_amount_over_assistant_euro_noise():
    compound = (
        "[RÉPONSE ASSISTANT PRÉCÉDENTE – référencée pour résoudre le tour courant]\n"
        "Les frais peuvent atteindre 10 € selon l'opération.\n"
        "[DEMANDE / RÉPONSE UTILISATEUR SUR CE TOUR]\n"
        "Je veux acheter pour 1000 € de Bitcoin"
    )
    extract = di.extract_intake_signals("crypto_buy", compound)
    assert extract["symbol"] == "BTC"
    assert extract["amount_from"] == 1000.0