"""Repository layer for pe_clients (Portfolio Engine — Clients module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import Client


class DuplicateEmailError(Exception):
    """Raised when attempting to create a client with an email that already exists."""

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Client with email '{email}' already exists")


class ClientRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Client:
        client = Client(**data)
        db.add(client)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise DuplicateEmailError(data.get("email", ""))
        return client

    @staticmethod
    def get_by_id(db: Session, client_id: UUID) -> Optional[Client]:
        return db.query(Client).filter(Client.id == client_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        query = db.query(Client)
        if status:
            query = query.filter(Client.status == status)
        total = query.count()
        items = query.order_by(Client.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, client: Client, *, data: dict) -> Client:
        for key, value in data.items():
            setattr(client, key, value)
        db.flush()
        return client
