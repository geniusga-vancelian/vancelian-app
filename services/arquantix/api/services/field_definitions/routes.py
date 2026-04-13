"""
FastAPI routes for field definitions
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from database import get_db, FieldDefinition

router = APIRouter(prefix="/api/field-definitions", tags=["field-definitions"])


@router.get("")
def list_field_definitions(
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    List all field definitions with optional filters.
    """
    query = db.query(FieldDefinition)
    
    if category:
        query = query.filter(FieldDefinition.category == category)
    
    if is_active is not None:
        query = query.filter(FieldDefinition.is_active == is_active)
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (FieldDefinition.slug.ilike(search_term)) |
            (FieldDefinition.field_name_en.ilike(search_term))
        )
    
    fields = query.order_by(FieldDefinition.category, FieldDefinition.slug).all()
    return fields
