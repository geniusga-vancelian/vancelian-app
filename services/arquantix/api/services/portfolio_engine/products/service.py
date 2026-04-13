"""Service layer for Products module (Portfolio Engine — catalog layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import ProductDefinition
from .repository import ProductRepository
from .schemas import ProductCreate, ProductUpdate


class ProductNotFoundError(Exception):
    def __init__(self, product_id: UUID):
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")


class ProductService:

    def __init__(self) -> None:
        self._repo = ProductRepository()

    def create_product(self, db: Session, payload: ProductCreate) -> ProductDefinition:
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_product(self, db: Session, product_id: UUID) -> ProductDefinition:
        product = self._repo.get_by_id(db, product_id)
        if product is None:
            raise ProductNotFoundError(product_id)
        return product

    def list_products(
        self,
        db: Session,
        *,
        product_type: Optional[str] = None,
        status: Optional[str] = None,
        is_public: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        return self._repo.list(
            db,
            product_type=product_type,
            status=status,
            is_public=is_public,
            skip=skip,
            limit=limit,
        )

    def update_product(self, db: Session, product_id: UUID, payload: ProductUpdate) -> ProductDefinition:
        product = self.get_product(db, product_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, product, data=data)
