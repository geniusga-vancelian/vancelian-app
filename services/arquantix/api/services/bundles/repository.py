"""
Repository layer for Bundles
Handles database operations with transactions
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from decimal import Decimal
from datetime import datetime

from database import Bundle, BundleComponent, BundleAllocation, BundleDynamicRule, MarketDataInstrument


def list_bundles(
    db: Session,
    asset_class: Optional[str] = None,
    active_only: bool = True
) -> List[Bundle]:
    """List bundles with optional filtering"""
    query = db.query(Bundle)
    
    if asset_class:
        query = query.filter(Bundle.asset_class == asset_class.lower())
    
    if active_only:
        query = query.filter(Bundle.is_active == "true")
    
    return query.order_by(Bundle.name).all()


def get_bundle_with_details(
    db: Session,
    bundle_id: int
) -> Optional[tuple[Bundle, List[BundleComponent], Optional[BundleDynamicRule]]]:
    """
    Get bundle with components and active dynamic rule
    
    Returns:
        Tuple of (bundle, components, active_rule) or None if bundle not found
    """
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        return None
    
    # Load components (prefer bundle_components, fallback to bundle_allocations for legacy)
    components = db.query(BundleComponent).filter(
        BundleComponent.bundle_id == bundle_id
    ).order_by(BundleComponent.position_order, BundleComponent.id).all()
    
    # Fallback to legacy allocations if no components
    if not components:
        allocations = db.query(BundleAllocation).filter(
            BundleAllocation.bundle_id == bundle_id
        ).order_by(BundleAllocation.position_order, BundleAllocation.id).all()
        # Convert to component-like structure (for compatibility)
        components = []
        for alloc in allocations:
            comp = BundleComponent(
                id=alloc.id,
                bundle_id=alloc.bundle_id,
                component_type='instrument',
                instrument_id=alloc.instrument_id,
                child_bundle_id=None,
                weight=alloc.weight,
                position_order=alloc.position_order,
                created_at=alloc.created_at
            )
            components.append(comp)
    
    # Load active dynamic rule
    active_rule = None
    if bundle.type == 'dynamic':
        active_rule = db.query(BundleDynamicRule).filter(
            BundleDynamicRule.bundle_id == bundle_id,
            BundleDynamicRule.is_active == "true"
        ).order_by(BundleDynamicRule.version.desc()).first()
    
    return (bundle, components, active_rule)


def create_bundle(
    db: Session,
    name: str,
    asset_class: str,
    bundle_type: str,
    description: Optional[str],
    is_active: bool,
    created_by_email: Optional[str],
    components: List[Dict[str, Any]],
    dynamic_rule: Optional[Dict[str, Any]] = None
) -> Bundle:
    """
    Create a new bundle with components and optional dynamic rule
    
    Args:
        db: Database session
        name: Bundle name
        asset_class: Asset class
        bundle_type: Bundle type (fixed_instruments, composite_fixed, dynamic)
        description: Optional description
        is_active: Whether bundle is active
        created_by_email: Creator email
        components: List of component dicts with keys: component_type, instrument_id or child_bundle_id, weight, position_order
        dynamic_rule: Optional dynamic rule dict with keys: rule_json, rule_type
    
    Returns:
        Created Bundle
    """
    # Create bundle
    bundle = Bundle(
        name=name,
        asset_class=asset_class.lower(),
        type=bundle_type,
        description=description,
        is_active="true" if is_active else "false",
        created_by_email=created_by_email
    )
    db.add(bundle)
    db.flush()  # Get bundle.id
    
    # Create components
    for idx, comp_data in enumerate(components):
        component = BundleComponent(
            bundle_id=bundle.id,
            component_type=comp_data['component_type'],
            instrument_id=comp_data.get('instrument_id'),
            child_bundle_id=comp_data.get('child_bundle_id'),
            weight=Decimal(str(comp_data['weight'])),
            position_order=comp_data.get('position_order', idx)
        )
        db.add(component)
    
    # Create dynamic rule if provided
    if dynamic_rule and bundle_type == 'dynamic':
        rule = BundleDynamicRule(
            bundle_id=bundle.id,
            rule_type=dynamic_rule.get('rule_type', 'formula_dsl'),
            rule_json=dynamic_rule['rule_json'],
            version=1,
            is_active="true"
        )
        db.add(rule)
    
    db.flush()
    db.refresh(bundle)
    return bundle


def update_bundle(
    db: Session,
    bundle_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
    components: Optional[List[Dict[str, Any]]] = None,
    dynamic_rule: Optional[Dict[str, Any]] = None
) -> Bundle:
    """
    Update bundle and optionally replace components/rule
    
    Args:
        db: Database session
        bundle_id: Bundle ID
        name: Optional new name
        description: Optional new description
        is_active: Optional new active status
        components: Optional new components (replaces all existing)
        dynamic_rule: Optional new dynamic rule (upserts active rule)
    
    Returns:
        Updated Bundle
    """
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        raise ValueError(f"Bundle {bundle_id} not found")
    
    # Update bundle fields
    if name is not None:
        bundle.name = name
    if description is not None:
        bundle.description = description
    if is_active is not None:
        bundle.is_active = "true" if is_active else "false"
    bundle.updated_at = datetime.now()
    
    # Replace components if provided
    if components is not None:
        # Delete existing components
        db.query(BundleComponent).filter(
            BundleComponent.bundle_id == bundle_id
        ).delete()
        
        # Insert new components
        for idx, comp_data in enumerate(components):
            component = BundleComponent(
                bundle_id=bundle_id,
                component_type=comp_data['component_type'],
                instrument_id=comp_data.get('instrument_id'),
                child_bundle_id=comp_data.get('child_bundle_id'),
                weight=Decimal(str(comp_data['weight'])),
                position_order=comp_data.get('position_order', idx)
            )
            db.add(component)
    
    # Upsert dynamic rule if provided
    if dynamic_rule is not None:
        if bundle.type != 'dynamic':
            raise ValueError(f"Cannot set dynamic_rule on bundle type '{bundle.type}'")
        
        # Deactivate existing active rules
        db.query(BundleDynamicRule).filter(
            BundleDynamicRule.bundle_id == bundle_id,
            BundleDynamicRule.is_active == "true"
        ).update({"is_active": "false"})
        
        # Get next version
        max_version = db.query(BundleDynamicRule).filter(
            BundleDynamicRule.bundle_id == bundle_id
        ).order_by(BundleDynamicRule.version.desc()).first()
        next_version = (max_version.version + 1) if max_version else 1
        
        # Create new active rule
        rule = BundleDynamicRule(
            bundle_id=bundle_id,
            rule_type=dynamic_rule.get('rule_type', 'formula_dsl'),
            rule_json=dynamic_rule['rule_json'],
            version=next_version,
            is_active="true"
        )
        db.add(rule)
    
    db.flush()
    db.refresh(bundle)
    return bundle


def delete_bundle(db: Session, bundle_id: int) -> bool:
    """Delete a bundle (cascade deletes components and rules)"""
    bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
    if not bundle:
        return False
    
    db.delete(bundle)
    return True

