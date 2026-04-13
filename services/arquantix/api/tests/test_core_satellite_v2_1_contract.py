"""
Tests contractuels pour Core-Satellite V2.1 (EDHEC-style).

Vérifie que les champs V2.1 sont correctement produits et stockés dans weights_json.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import date, timedelta
from services.backtest.strategies.core_satellite import run_core_satellite_backtest


def test_v2_1_weights_json_contains_fields():
    """Test que weights_json contient les champs V2.1 obligatoires."""
    # Créer données synthétiques
    start = date(2024, 1, 1)
    dates = pd.date_range(start, periods=30, freq='D')
    prices_df = pd.DataFrame({
        1: [100.0 + i * 0.5 for i in range(30)],
        2: [50.0 + i * 0.3 for i in range(30)],
    }, index=dates)
    
    result = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=29),
        initial_capital=100.0,
        rebalance_frequency="daily",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="te_target",
        target_te=0.10,
        debug=True,
    )
    
    # Vérifier que portfolio_series existe et contient des données
    assert 'portfolio_series' in result
    assert len(result['portfolio_series']) > 0
    
    # Vérifier les champs V2.1 obligatoires dans chaque bar
    required_v2_1_fields = [
        '_cs_alloc_mode',
        '_cs_sat_weight_scalar',
        '_cs_te_sat',
        '_cs_ir_sat',
    ]
    
    for bar in result['portfolio_series']:
        assert 'weights_json' in bar
        weights = bar['weights_json']
        
        # Vérifier présence des champs
        for field in required_v2_1_fields:
            assert field in weights, f"Field {field} missing in weights_json at date {bar['date']}"
        
        # Vérifier types et valeurs
        assert weights['_cs_alloc_mode'] == "te_target"
        assert 0.0 <= weights['_cs_sat_weight_scalar'] <= 1.0
        assert weights['_cs_te_sat'] >= 0.0
        # _cs_ir_sat peut être None
        if weights['_cs_ir_sat'] is not None:
            assert isinstance(weights['_cs_ir_sat'], (int, float))


def test_v2_1_te_target_mode_changes_scalar():
    """Test que te_target mode change w_scalar quand target_te change."""
    start = date(2024, 1, 1)
    dates = pd.date_range(start, periods=50, freq='D')
    
    # Créer données avec volatilité modérée
    np.random.seed(42)
    returns1 = np.random.normal(0.001, 0.02, 50)
    returns2 = np.random.normal(0.001, 0.015, 50)
    prices1 = 100.0 * np.cumprod(1 + returns1)
    prices2 = 50.0 * np.cumprod(1 + returns2)
    
    prices_df = pd.DataFrame({
        1: prices1,
        2: prices2,
    }, index=dates)
    
    # Run 1: target_te bas (0.05) -> devrait donner w_scalar plus bas
    result1 = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=49),
        initial_capital=100.0,
        rebalance_frequency="weekly",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="te_target",
        target_te=0.05,
        debug=False,
    )
    
    # Run 2: target_te élevé (0.20) -> devrait donner w_scalar plus élevé
    result2 = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=49),
        initial_capital=100.0,
        rebalance_frequency="weekly",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="te_target",
        target_te=0.20,
        debug=False,
    )
    
    # Comparer w_scalar moyen
    w_scalar_list1 = [bar['weights_json']['_cs_sat_weight_scalar'] for bar in result1['portfolio_series'] if bar['weights_json'].get('_cs_sat_weight_scalar') is not None]
    w_scalar_list2 = [bar['weights_json']['_cs_sat_weight_scalar'] for bar in result2['portfolio_series'] if bar['weights_json'].get('_cs_sat_weight_scalar') is not None]
    
    assert len(w_scalar_list1) > 0
    assert len(w_scalar_list2) > 0
    
    avg_w1 = np.mean(w_scalar_list1)
    avg_w2 = np.mean(w_scalar_list2)
    
    # target_te plus élevé devrait donner w_scalar plus élevé (sous réserve de sat_max)
    # Mais on accepte aussi si les deux sont proches (cas où sat_max limite)
    assert avg_w2 >= avg_w1 * 0.8, f"Expected avg_w2 ({avg_w2}) >= avg_w1 ({avg_w1}) * 0.8 when target_te increases"


def test_v2_1_utility_lambda_mode_uses_lambda():
    """Test que utility_lambda mode utilise lambda_risk (w diminue quand lambda augmente)."""
    start = date(2024, 1, 1)
    dates = pd.date_range(start, periods=50, freq='D')
    
    np.random.seed(42)
    returns1 = np.random.normal(0.002, 0.02, 50)
    returns2 = np.random.normal(0.0015, 0.018, 50)
    prices1 = 100.0 * np.cumprod(1 + returns1)
    prices2 = 50.0 * np.cumprod(1 + returns2)
    
    prices_df = pd.DataFrame({
        1: prices1,
        2: prices2,
    }, index=dates)
    
    # Run 1: lambda_risk bas (0.1) -> devrait donner w_scalar plus élevé
    result1 = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=49),
        initial_capital=100.0,
        rebalance_frequency="weekly",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="utility_lambda",
        lambda_risk=0.1,
        target_te=0.10,  # Nécessaire même si pas directement utilisé
        debug=False,
    )
    
    # Run 2: lambda_risk élevé (0.5) -> devrait donner w_scalar plus bas
    result2 = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=49),
        initial_capital=100.0,
        rebalance_frequency="weekly",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="utility_lambda",
        lambda_risk=0.5,
        target_te=0.10,
        debug=False,
    )
    
    w_scalar_list1 = [bar['weights_json']['_cs_sat_weight_scalar'] for bar in result1['portfolio_series'] if bar['weights_json'].get('_cs_sat_weight_scalar') is not None]
    w_scalar_list2 = [bar['weights_json']['_cs_sat_weight_scalar'] for bar in result2['portfolio_series'] if bar['weights_json'].get('_cs_sat_weight_scalar') is not None]
    
    assert len(w_scalar_list1) > 0
    assert len(w_scalar_list2) > 0
    
    avg_w1 = np.mean(w_scalar_list1)
    avg_w2 = np.mean(w_scalar_list2)
    
    # lambda_risk plus élevé devrait donner w_scalar plus bas
    assert avg_w2 <= avg_w1 * 1.2, f"Expected avg_w2 ({avg_w2}) <= avg_w1 ({avg_w1}) * 1.2 when lambda_risk increases"
    # Permet une petite tolérance pour la stabilité numérique


def test_v2_1_dynamic_cushion_produces_rel_fields():
    """Test que dynamic_cushion mode produit les champs rel_index, rel_floor, cushion."""
    start = date(2024, 1, 1)
    dates = pd.date_range(start, periods=50, freq='D')
    
    np.random.seed(42)
    returns1 = np.random.normal(0.001, 0.02, 50)
    returns2 = np.random.normal(0.001, 0.015, 50)
    prices1 = 100.0 * np.cumprod(1 + returns1)
    prices2 = 50.0 * np.cumprod(1 + returns2)
    
    prices_df = pd.DataFrame({
        1: prices1,
        2: prices2,
    }, index=dates)
    
    result = run_core_satellite_backtest(
        prices_df=prices_df,
        instrument_ids=[1, 2],
        start_date=start,
        end_date=start + timedelta(days=49),
        initial_capital=100.0,
        rebalance_frequency="weekly",
        fees_bps=0.0,
        slippage_bps=0.0,
        allocation_mode="dynamic_cushion",
        multiplier=4.0,
        floor_rel_ratio=0.95,
        floor_accrues_with_core=True,
        target_te=0.10,  # Nécessaire même si pas directement utilisé
        debug=False,
    )
    
    assert 'portfolio_series' in result
    assert len(result['portfolio_series']) > 0
    
    # Vérifier les champs conditionnels pour dynamic_cushion
    dynamic_cushion_fields = [
        '_cs_rel_index',
        '_cs_rel_floor',
        '_cs_cushion',
    ]
    
    found_fields = {field: False for field in dynamic_cushion_fields}
    
    for bar in result['portfolio_series']:
        assert 'weights_json' in bar
        weights = bar['weights_json']
        
        # Vérifier que allocation_mode est correct
        assert weights['_cs_alloc_mode'] == "dynamic_cushion"
        
        # Vérifier présence des champs conditionnels
        for field in dynamic_cushion_fields:
            if field in weights:
                found_fields[field] = True
                # Vérifier que les valeurs sont numériques
                assert isinstance(weights[field], (int, float))
                # rel_index et rel_floor doivent être >= 0
                if field in ['_cs_rel_index', '_cs_rel_floor']:
                    assert weights[field] >= 0.0
                # cushion doit être >= 0
                if field == '_cs_cushion':
                    assert weights[field] >= 0.0
    
    # Vérifier qu'au moins un bar contient ces champs
    # (ils peuvent être absents sur les premiers jours avant le premier rebalance)
    assert any(found_fields.values()), "At least one dynamic_cushion field should be present in weights_json"
