"""Repository layer for pe_product_definitions (Portfolio Engine — Products module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import ProductDefinition


class DuplicateProductCodeError(Exception):
    """Raised when attempting to create a product with a code that already exists."""

    def __init__(self, product_code: str):
        self.product_code = product_code
        super().__init__(f"Product with code '{product_code}' already exists")


class ProductRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ProductDefinition:
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        product = ProductDefinition(**data)
        db.add(product)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateProductCodeError(data.get("product_code", ""))
        return product

    @staticmethod
    def get_by_id(db: Session, product_id: UUID) -> Optional[ProductDefinition]:
        return db.query(ProductDefinition).filter(ProductDefinition.id == product_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        product_type: Optional[str] = None,
        status: Optional[str] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductDefinition], int]:
        query = db.query(ProductDefinition)
        if product_type:
            query = query.filter(ProductDefinition.product_type == product_type)
        if status:
            query = query.filter(ProductDefinition.status == status)
        if is_public is not None:
            query = query.filter(ProductDefinition.is_public == is_public)
        total = query.count()
        items = query.order_by(ProductDefinition.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, product: ProductDefinition, *, data: dict) -> ProductDefinition:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(product, col_name, value)
        db.flush()
        return product
