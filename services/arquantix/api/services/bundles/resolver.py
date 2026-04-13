"""
Bundle resolver - Compute effective weights for bundles at a given date
Supports fixed, composite, and dynamic bundles

Note: BundleComponent.weight is stored as Decimal percentage (0-100) in the database.
This resolver converts to fraction (0-1) for consistency with backtest strategies.
"""
from typing import Dict, Optional
from datetime import date
from sqlalchemy.orm import Session
from decimal import Decimal

from database import MarketDataBundle, BundleComponent
from services.bundles.errors import BundleValidationError


def resolve_bundle_effective_weights(
    db: Session,
    bundle_id: int,
    target_date: date,
) -> Dict[int, float]:
    """
    Resolve effective weights for a bundle at a given date.
    
    Returns Dict[instrument_id, weight] where weights are in [0..1] and sum to 1.0.
    
    For fixed bundles: returns fixed weights from BundleComponent.weight
    For composite bundles: recursively resolves child bundles
    For dynamic bundles: computes weights based on rules (future)
    
    Raises ValueError if weights are invalid (sum != 1.0, missing weights, etc.)
    """
    bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == bundle_id).first()
    if not bundle:
        raise BundleValidationError(
            f"Bundle {bundle_id} not found",
            bundle_id=bundle_id
        )
    
    # Get components for this bundle
    components = db.query(BundleComponent).filter(
        BundleComponent.bundle_id == bundle.id,
        BundleComponent.component_type == "instrument",
        BundleComponent.instrument_id.isnot(None)
    ).all()
    
    if not components:
        raise BundleValidationError(
            f"Bundle {bundle_id} has no instruments",
            bundle_id=bundle_id
        )
    
    # Support fixed, composite, and dynamic bundles
    if bundle.type == "fixed_instruments":
        # Fixed bundle: use weights from BundleComponent
        # Note: BundleComponent.weight is stored as Decimal percentage (0-100) in DB
        weights = {}
        for comp in components:
            if comp.instrument_id is None:
                continue
            if comp.weight is None:
                raise BundleValidationError(
                    f"Bundle {bundle_id} component for instrument {comp.instrument_id} has no weight",
                    bundle_id=bundle_id
                )
            # Convert from percentage (0-100) to fraction (0-1)
            weight_fraction = float(comp.weight) / 100.0
            if weight_fraction <= 0:
                raise BundleValidationError(
                    f"Bundle {bundle_id} component for instrument {comp.instrument_id} has non-positive weight: {comp.weight}%",
                    bundle_id=bundle_id
                )
            weights[comp.instrument_id] = weight_fraction
        
        # Validate: all weights > 0
        if not all(w > 0 for w in weights.values()):
            raise BundleValidationError(
                f"Bundle {bundle_id} has non-positive weights after conversion",
                bundle_id=bundle_id
            )
        
        # Validate: sum == 1.0 (strict tolerance 1e-6)
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            # Calculate original percentage sum for clearer error message
            original_total_pct = sum(float(comp.weight) for comp in components if comp.instrument_id and comp.weight)
            raise BundleValidationError(
                f"Bundle {bundle_id} weights sum to {total:.6f} (fraction) / {original_total_pct:.2f}% (percentage), expected 1.0 / 100.0",
                bundle_id=bundle_id
            )
        
        return weights
    
    elif bundle.type == "composite_fixed":
        # Composite bundle: recursively resolve child bundles
        child_components = db.query(BundleComponent).filter(
            BundleComponent.bundle_id == bundle.id,
            BundleComponent.component_type == "bundle",
            BundleComponent.child_bundle_id.isnot(None)
        ).all()
        
        if not child_components:
            raise BundleValidationError(
                f"Composite bundle {bundle_id} has no child bundles",
                bundle_id=bundle_id
            )
        
        # Aggregate weights from child bundles
        aggregated_weights = {}
        for comp in child_components:
            if comp.child_bundle_id is None or comp.weight is None:
                continue
            # Convert from percentage (0-100) to fraction (0-1)
            child_weight_fraction = float(comp.weight) / 100.0
            
            # Resolve child bundle weights (returns fractions)
            child_weights = resolve_bundle_effective_weights(db, comp.child_bundle_id, target_date)
            
            # Multiply child weights by parent allocation
            for inst_id, child_weight in child_weights.items():
                aggregated_weights[inst_id] = aggregated_weights.get(inst_id, 0.0) + child_weight * child_weight_fraction
        
        # Validate aggregated weights
        if not aggregated_weights:
            raise BundleValidationError(
                f"Composite bundle {bundle_id} resolved to no instruments",
                bundle_id=bundle_id
            )
        
        if not all(w > 0 for w in aggregated_weights.values()):
            raise BundleValidationError(
                f"Composite bundle {bundle_id} has non-positive aggregated weights",
                bundle_id=bundle_id
            )
        
        total = sum(aggregated_weights.values())
        if abs(total - 1.0) > 1e-6:
            raise BundleValidationError(
                f"Composite bundle {bundle_id} aggregated weights sum to {total:.6f}, expected 1.0",
                bundle_id=bundle_id
            )
        
        return aggregated_weights
    
    elif bundle.type == "dynamic":
        # Dynamic bundle: not yet implemented
        raise BundleValidationError(
            f"Dynamic bundles not yet implemented for bundle {bundle_id}",
            bundle_id=bundle_id
        )
    
    else:
        raise BundleValidationError(
            f"Unknown bundle type '{bundle.type}' for bundle {bundle_id}",
            bundle_id=bundle_id
        )

