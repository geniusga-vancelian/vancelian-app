"""
Preview service for bundles
Builds price matrices and resolves bundle weights for preview
Uses centralized bars_d1_repo for price data
"""
from typing import Dict, List, Tuple
from datetime import date, timedelta
from sqlalchemy.orm import Session
import pandas as pd

from database import MarketDataInstrument, Bundle
from services.market_data.bars_d1_repo import (
    get_price_dataframe,
    check_data_coverage,
    get_available_date_range,
)
from .resolver import (
    resolve_bundle_effective_weights,
    resolve_bundle_to_instrument_weights,
    BundleCycleError as ResolverCycleError,
    BundleWeightValidationError as ResolverWeightError,
)
from .exceptions import (
    BundleCycleError,
    InsufficientMarketData,
    DynamicRuleInvalid,
)
from .dsl_analyzer import infer_dynamic_requirements


def get_all_instrument_ids_for_bundle(
    db: Session,
    bundle_id: int,
    visited: set = None
) -> List[int]:
    """
    Recursively get all instrument IDs that a bundle (or its children) references
    
    Args:
        db: Database session
        bundle_id: Bundle ID
        visited: Set of visited bundle IDs (for cycle detection)
    
    Returns:
        List of instrument IDs
    """
    if visited is None:
        visited = set()
    
    if bundle_id in visited:
        raise BundleCycleError(f"Bundle {bundle_id} is referenced recursively")
    
    visited.add(bundle_id)
    
    # Load bundle
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        raise ValueError(f"Bundle {bundle_id} not found")
    
    instrument_ids = set()
    
    # Load components
    from database import BundleComponent, BundleAllocation
    components = db.query(BundleComponent).filter(
        BundleComponent.bundle_id == bundle_id
    ).all()
    
    # Fallback to legacy allocations
    if not components:
        allocations = db.query(BundleAllocation).filter(
            BundleAllocation.bundle_id == bundle_id
        ).all()
        for alloc in allocations:
            instrument_ids.add(alloc.instrument_id)
    else:
        for comp in components:
            if comp.component_type == 'instrument' and comp.instrument_id:
                instrument_ids.add(comp.instrument_id)
            elif comp.component_type == 'bundle' and comp.child_bundle_id:
                # Recursively get instruments from child bundle
                child_instruments = get_all_instrument_ids_for_bundle(
                    db, comp.child_bundle_id, visited.copy()
                )
                instrument_ids.update(child_instruments)
    
    return list(instrument_ids)


def preview_bundle_effective_weights(
    db: Session,
    bundle_id: int,
    preview_date: date
) -> Tuple[Dict[int, float], List[str]]:
    """
    Preview effective instrument weights for a bundle at a given date
    
    Uses centralized bars_d1_repo for price data loading.
    
    Args:
        db: Database session
        bundle_id: Bundle ID
        preview_date: Date to preview as of
    
    Returns:
        Tuple of (weights_dict, warnings_list)
        weights_dict: instrument_id -> weight (0.0 to 1.0)
        warnings: List of warning messages
    
    Raises:
        BundleCycleError: If cycle detected
        InsufficientMarketData: If insufficient price data
        DynamicRuleInvalid: If dynamic rule is invalid
    """
    warnings = []
    
    # Load bundle
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        raise ValueError(f"Bundle {bundle_id} not found")
    
    # For fixed/composite bundles, no price data needed
    if bundle.type in ('fixed_instruments', 'composite_fixed'):
        try:
            weights = resolve_bundle_to_instrument_weights(db, bundle_id)
            return weights, warnings
        except ResolverCycleError as e:
            raise BundleCycleError(str(e))
        except ResolverWeightError as e:
            raise DynamicRuleInvalid(str(e))
        except Exception as e:
            warnings.append(f"Warning: {str(e)}")
            raise ValueError(f"Failed to resolve bundle: {str(e)}")
    
    # For dynamic bundles, need price data
    elif bundle.type == 'dynamic':
        # Load active dynamic rule
        from database import BundleDynamicRule
        rule = db.query(BundleDynamicRule).filter(
            BundleDynamicRule.bundle_id == bundle_id,
            BundleDynamicRule.is_active == "true"
        ).order_by(BundleDynamicRule.version.desc()).first()
        
        if not rule:
            raise DynamicRuleInvalid("Bundle has no active dynamic rule")
        
        rule_json = rule.rule_json
        
        # Infer requirements from rule
        lookback_days, uses_prices = infer_dynamic_requirements(rule_json)
        
        if not uses_prices:
            # Rule doesn't use prices, can resolve without data
            try:
                # Create empty price matrix (won't be used)
                price_matrix = pd.DataFrame(columns=['date', 'instrument_id', 'open', 'high', 'low', 'close', 'volume'])
                weights = resolve_bundle_effective_weights(
                    db, bundle_id, preview_date, price_matrix
                )
                return weights, warnings
            except Exception as e:
                raise DynamicRuleInvalid(f"Failed to resolve rule without prices: {str(e)}")
        
        # Rule uses prices: need to load data
        # Get all instrument IDs that might be referenced
        try:
            all_instrument_ids = get_all_instrument_ids_for_bundle(db, bundle_id)
        except BundleCycleError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to get instrument IDs: {str(e)}")
        
        if not all_instrument_ids:
            raise DynamicRuleInvalid("Bundle has no instruments")
        
        # Calculate date range needed
        start_date = preview_date - timedelta(days=lookback_days)
        
        # Check data coverage
        is_sufficient, coverage_warnings = check_data_coverage(
            db, all_instrument_ids, start_date, preview_date, min_coverage_pct=0.80
        )
        warnings.extend(coverage_warnings)
        
        # Load price data using centralized repo
        try:
            price_matrix = get_price_dataframe(
                db, all_instrument_ids, start_date, preview_date
            )
        except Exception as e:
            raise InsufficientMarketData(f"Failed to load price data: {str(e)}")
        
        if len(price_matrix) == 0:
            raise InsufficientMarketData(
                f"No price data found for instruments {all_instrument_ids} "
                f"in range {start_date} to {preview_date}"
            )
        
        # Check if we have enough data for the preview date
        date_data = price_matrix[price_matrix['date'] <= preview_date]
        if len(date_data) == 0:
            raise InsufficientMarketData(
                f"No price data available up to {preview_date}"
            )
        
        # Check if we have enough data for required windows
        for inst_id in all_instrument_ids:
            inst_data = date_data[date_data['instrument_id'] == inst_id]
            if len(inst_data) < lookback_days * 0.8:  # 80% coverage minimum
                raise InsufficientMarketData(
                    f"Instrument {inst_id} has insufficient data: "
                    f"need {lookback_days} days, got {len(inst_data)}"
                )
        
        # Resolve dynamic weights
        try:
            weights = resolve_bundle_effective_weights(
                db, bundle_id, preview_date, price_matrix
            )
            return weights, warnings
        except ResolverCycleError as e:
            raise BundleCycleError(str(e))
        except ResolverWeightError as e:
            raise DynamicRuleInvalid(str(e))
        except Exception as e:
            if "Insufficient" in str(e) or "not enough data" in str(e).lower():
                raise InsufficientMarketData(str(e))
            raise DynamicRuleInvalid(f"Failed to resolve dynamic bundle: {str(e)}")
    
    else:
        raise ValueError(f"Unknown bundle type: {bundle.type}")
