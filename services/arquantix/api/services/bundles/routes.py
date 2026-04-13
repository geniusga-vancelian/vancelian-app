"""
Bundles routes - CRUD operations for market data bundles
"""
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal
import uuid

from database import get_db, MarketDataBundle, MarketDataInstrument, BundleComponent
from auth import get_current_user, AdminUser

router = APIRouter(prefix="/api/bundles", tags=["bundles"])


# ============================================================================
# Schemas
# ============================================================================

class BundleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    instrument_ids: List[int]
    allocations: Optional[dict] = None  # Map of instrument_id: allocation_percentage


class BundleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instrument_ids: Optional[List[int]] = None


class BundleResponse(BaseModel):
    id: str
    name: str
    asset_class: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str]
    instrument_ids: List[int]
    instruments: Optional[List[dict]] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


# ============================================================================
# Routes
# ============================================================================

@router.get("", response_model=List[BundleResponse])
def list_bundles(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all bundles"""
    bundles = db.query(MarketDataBundle).filter(
        MarketDataBundle.is_active == "true"
    ).order_by(
        MarketDataBundle.asset_class.asc(),
        MarketDataBundle.type.asc(),
        MarketDataBundle.name.asc()
    ).all()
    
    result = []
    for bundle in bundles:
        # Load components (instruments) for each bundle
        components = db.query(BundleComponent).filter(
            BundleComponent.bundle_id == bundle.id,
            BundleComponent.component_type == "instrument",
            BundleComponent.instrument_id.isnot(None)
        ).all()
        
        instrument_ids = [comp.instrument_id for comp in components if comp.instrument_id]
        
        # Create a map of instrument_id -> weight for quick lookup
        instrument_weights = {comp.instrument_id: float(comp.weight) if comp.weight else None 
                             for comp in components if comp.instrument_id}
        
        # Load instrument details with weights
        instruments = []
        if instrument_ids:
            instrument_list = db.query(MarketDataInstrument).filter(
                MarketDataInstrument.id.in_(instrument_ids)
            ).all()
            instruments = [
                {
                    "id": inst.id,
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "asset_class": inst.asset_class,
                    "weight": instrument_weights.get(inst.id),
                    "weight_pct": round(float(instrument_weights.get(inst.id, 0)), 2) if instrument_weights.get(inst.id) else None,
                }
                for inst in instrument_list
            ]
        
        result.append({
            "id": str(bundle.id),  # Convert to string for frontend
            "name": bundle.name,
            "asset_class": bundle.asset_class,
            "type": bundle.type,
            "description": bundle.description,
            "instrument_ids": instrument_ids,
            "instruments": instruments,
            "created_at": bundle.created_at.isoformat() if bundle.created_at else "",
            "updated_at": bundle.updated_at.isoformat() if bundle.updated_at else "",
        })
    
    return result


@router.get("/{bundle_id}", response_model=BundleResponse)
def get_bundle(
    bundle_id: str,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a bundle by ID"""
    try:
        bundle_id_int = int(bundle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bundle ID format")
    
    bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == bundle_id_int).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Load components (instruments) for this bundle
    components = db.query(BundleComponent).filter(
        BundleComponent.bundle_id == bundle.id,
        BundleComponent.component_type == "instrument",
        BundleComponent.instrument_id.isnot(None)
    ).all()
    
    instrument_ids = [comp.instrument_id for comp in components if comp.instrument_id]
    
    # Load instrument details
    instruments = []
    if instrument_ids:
        instrument_list = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(instrument_ids)
        ).all()
        instruments = [
            {
                "id": inst.id,
                "symbol": inst.symbol,
                "name": inst.name,
                "asset_class": inst.asset_class,
            }
            for inst in instrument_list
        ]
    
    return {
        "id": str(bundle.id),  # Convert to string for frontend
        "name": bundle.name,
        "asset_class": bundle.asset_class,
        "type": bundle.type,
        "description": bundle.description,
        "instrument_ids": instrument_ids,
        "instruments": instruments,
        "created_at": bundle.created_at.isoformat() if bundle.created_at else "",
        "updated_at": bundle.updated_at.isoformat() if bundle.updated_at else "",
    }


@router.post("", response_model=BundleResponse, status_code=status.HTTP_201_CREATED)
def create_bundle(
    bundle_data: BundleCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bundle"""
    # Validate instrument IDs exist and load instruments
    instruments = []
    if bundle_data.instrument_ids:
        instruments = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(bundle_data.instrument_ids)
        ).all()
        if len(instruments) != len(bundle_data.instrument_ids):
            found_ids = {inst.id for inst in instruments}
            missing_ids = set(bundle_data.instrument_ids) - found_ids
            raise HTTPException(
                status_code=400,
                detail=f"Some instrument IDs not found: {list(missing_ids)}"
            )
    
    # Determine asset_class from instruments (use most common, or first if all same)
    # asset_class is NOT NULL in database, so we must provide a value
    asset_class = "mixed"  # Default fallback
    if instruments:
        instrument_asset_classes = [inst.asset_class for inst in instruments if inst.asset_class]
        if instrument_asset_classes:
            # Use most common asset class
            from collections import Counter
            asset_class_counts = Counter(instrument_asset_classes)
            asset_class = asset_class_counts.most_common(1)[0][0]
    
    # Create bundle
    # Note: type column has CHECK constraint: 'fixed_instruments', 'composite_fixed', or 'dynamic'
    # For bundles with fixed instrument allocations, use 'fixed_instruments'
    bundle = MarketDataBundle(
        name=bundle_data.name,
        description=bundle_data.description,
        asset_class=asset_class,  # Required field (NOT NULL in DB)
        type="fixed_instruments",  # Valid CHECK constraint value for fixed instrument bundles
        is_active="true",
        created_by_email=current_user.email,
    )
    
    db.add(bundle)
    db.flush()  # Flush to get the ID
    
    # Create bundle components for each instrument with allocations
    allocations = bundle_data.allocations or {}
    
    # Convert string keys to int if needed (JSON keys might be strings)
    allocations_normalized = {}
    if allocations:
        for key, value in allocations.items():
            try:
                instrument_id_int = int(key) if isinstance(key, str) else key
                allocations_normalized[instrument_id_int] = value
            except (ValueError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid instrument ID in allocations: {key}"
                )
    
    # Validate allocations sum to 100 if provided
    if allocations_normalized:
        total_allocation = sum(float(v) for v in allocations_normalized.values() if v is not None)
        if abs(total_allocation - 100.0) > 0.01:  # Allow small floating point errors
            raise HTTPException(
                status_code=400,
                detail=f"Total allocation must be 100%. Current total: {total_allocation:.2f}%"
            )
        
        # Verify all instrument IDs have allocations
        for instrument_id in bundle_data.instrument_ids:
            if instrument_id not in allocations_normalized or allocations_normalized[instrument_id] is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Allocation required for instrument ID {instrument_id}"
                )
    
    # If no allocations provided, use equal weight
    equal_weight = 100.0 / len(bundle_data.instrument_ids) if bundle_data.instrument_ids else 0.0
    
    for idx, instrument_id in enumerate(bundle_data.instrument_ids):
        # Get allocation from provided dict or use equal weight
        allocation_percentage = None
        if allocations_normalized and instrument_id in allocations_normalized:
            # Use provided allocation
            allocation_value = allocations_normalized[instrument_id]
            allocation_percentage = Decimal(str(allocation_value)) if allocation_value is not None else None
        else:
            # Use equal weight if no allocations provided (should not happen if validation passed)
            allocation_percentage = Decimal(str(equal_weight))
        
        # Ensure allocation_percentage is set
        if allocation_percentage is None:
            allocation_percentage = Decimal(str(equal_weight))
        
        component = BundleComponent(
            bundle_id=bundle.id,
            component_type="instrument",
            instrument_id=instrument_id,
            position_order=idx,
            weight=allocation_percentage,  # Store allocation as weight (Decimal)
        )
        db.add(component)
    
    db.commit()
    db.refresh(bundle)
    
    # Load instruments for response
    instruments = []
    if bundle_data.instrument_ids:
        instrument_list = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(bundle_data.instrument_ids)
        ).all()
        instruments = [
            {
                "id": inst.id,
                "symbol": inst.symbol,
                "name": inst.name,
                "asset_class": inst.asset_class,
            }
            for inst in instrument_list
        ]
    
    return {
        "id": str(bundle.id),  # Convert to string for frontend
        "name": bundle.name,
        "asset_class": bundle.asset_class,
        "type": bundle.type,
        "description": bundle.description,
        "instrument_ids": bundle_data.instrument_ids,
        "instruments": instruments,
        "created_at": bundle.created_at.isoformat() if bundle.created_at else "",
        "updated_at": bundle.updated_at.isoformat() if bundle.updated_at else "",
    }


@router.put("/{bundle_id}", response_model=BundleResponse)
def update_bundle(
    bundle_id: str,
    bundle_data: BundleUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bundle"""
    try:
        bundle_id_int = int(bundle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bundle ID format")
    
    bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == bundle_id_int).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Update fields
    if bundle_data.name is not None:
        bundle.name = bundle_data.name
    if bundle_data.description is not None:
        bundle.description = bundle_data.description
    
    # Update instrument IDs if provided
    if bundle_data.instrument_ids is not None:
        # Validate instrument IDs exist
        instruments = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(bundle_data.instrument_ids)
        ).all()
        if len(instruments) != len(bundle_data.instrument_ids):
            found_ids = {inst.id for inst in instruments}
            missing_ids = set(bundle_data.instrument_ids) - found_ids
            raise HTTPException(
                status_code=400,
                detail=f"Some instrument IDs not found: {list(missing_ids)}"
            )
        
        # Delete old components
        db.query(BundleComponent).filter(
            BundleComponent.bundle_id == bundle.id,
            BundleComponent.component_type == "instrument"
        ).delete()
        
        # Create new components
        for idx, instrument_id in enumerate(bundle_data.instrument_ids):
            component = BundleComponent(
                bundle_id=bundle.id,
                component_type="instrument",
                instrument_id=instrument_id,
                position_order=idx,
                weight=None,
            )
            db.add(component)
    
    db.commit()
    db.refresh(bundle)
    
    # Load components to get final instrument_ids
    components = db.query(BundleComponent).filter(
        BundleComponent.bundle_id == bundle.id,
        BundleComponent.component_type == "instrument",
        BundleComponent.instrument_id.isnot(None)
    ).all()
    
    instrument_ids = [comp.instrument_id for comp in components if comp.instrument_id]
    
    # Load instruments for response
    instruments = []
    if instrument_ids:
        instrument_list = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id.in_(instrument_ids)
        ).all()
        instruments = [
            {
                "id": inst.id,
                "symbol": inst.symbol,
                "name": inst.name,
                "asset_class": inst.asset_class,
            }
            for inst in instrument_list
        ]
    
    return {
        "id": str(bundle.id),  # Convert to string for frontend
        "name": bundle.name,
        "asset_class": bundle.asset_class,
        "type": bundle.type,
        "description": bundle.description,
        "instrument_ids": instrument_ids,
        "instruments": instruments,
        "created_at": bundle.created_at.isoformat() if bundle.created_at else "",
        "updated_at": bundle.updated_at.isoformat() if bundle.updated_at else "",
    }


@router.delete("/{bundle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bundle(
    bundle_id: str,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bundle"""
    try:
        bundle_id_int = int(bundle_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid bundle ID format")
    
    bundle = db.query(MarketDataBundle).filter(MarketDataBundle.id == bundle_id_int).first()
    if not bundle:
        raise HTTPException(status_code=404, detail="Bundle not found")
    
    # Delete components first (foreign key constraint)
    db.query(BundleComponent).filter(BundleComponent.bundle_id == bundle.id).delete()
    
    # Delete bundle
    db.delete(bundle)
    db.commit()
    return None

