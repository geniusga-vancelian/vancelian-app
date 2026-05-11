"""Tests — motifs transactionnels déterministes (garde pré-LLM)."""

from __future__ import annotations

from services.assistance.agents.transactional_crypto_intent_patterns import (
    matches_spot_acquisition_verb,
    matches_spot_swap_verb,
)


def test_investis_usdc_en_eth_counts_as_acquisition_not_swap():
    t = "Investis tout mon USDC en ETH"
    assert matches_spot_acquisition_verb(t)
    assert not matches_spot_swap_verb(t)


def test_convertir_is_swap_lane():
    assert matches_spot_swap_verb("je veux convertir mes USDC en ETH")


def test_mettre_tout_is_acquisition_verb_lane():
    assert matches_spot_acquisition_verb("je veux mettre tout mon USDC en ethereum")
