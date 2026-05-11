"""Deep-links CAL invest — montant / devise optionnels sur crypto_buy."""

from __future__ import annotations

from services.assistance.agents.tools.product import show_invest_source_accounts as m


def test_crypto_buy_amount_query_on_deep_link():
    url = m._build_deep_link(
        target_kind="crypto_buy",
        target_id="BTC",
        account_key="fiat",
        amount_from=1000.0,
        currency_from="EUR",
    )
    assert url.startswith("vancelian://app/invest/crypto_buy_amount?symbol=BTC")
    assert "account_key=fiat" in url
    assert "amount=1000" in url.lower()
    assert "ccy=eur" in url.lower()


def test_crypto_buy_deep_link_without_amount_unchanged_shape():
    url = m._build_deep_link(
        target_kind="crypto_buy",
        target_id="ETH",
        account_key="crypto:USDC",
    )
    q = url.split("?", 1)[-1]
    assert "amount=" not in q
    assert "ccy=" not in q


def test_normalize_quote_currency():
    assert m._normalize_quote_currency("euro") == "EUR"
    assert m._normalize_quote_currency("USD") == "USD"
