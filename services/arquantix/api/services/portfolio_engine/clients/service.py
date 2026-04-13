"""Service layer for Clients module (Portfolio Engine — ownership layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Client
from .repository import ClientRepository
from .schemas import ClientCreate, ClientUpdate


class ClientNotFoundError(Exception):
    def __init__(self, client_id: UUID):
        self.client_id = client_id
        super().__init__(f"Client {client_id} not found")


class ClientService:

    def __init__(self) -> None:
        self._repo = ClientRepository()

    def create_client(self, db: Session, payload: ClientCreate) -> Client:
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_client(self, db: Session, client_id: UUID) -> Client:
        client = self._repo.get_by_id(db, client_id)
        if client is None:
            raise ClientNotFoundError(client_id)
        return client

    def list_clients(
        self,
        db: Session,
        *,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        return self._repo.list(db, status=status, skip=skip, limit=limit)

    def update_client(self, db: Session, client_id: UUID, payload: ClientUpdate) -> Client:
        client = self.get_client(db, client_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, client, data=data)
