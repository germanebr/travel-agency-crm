from __future__ import annotations

from sqlalchemy import select

from epic_trips_crm.db.models import Client
from epic_trips_crm.db.repositories.base import BaseRepository
from epic_trips_crm.utils.errors import NotFoundError


class ClientRepository(BaseRepository):
    def create(
        self,
        *,
        first_name: str,
        last_name: str,
        country: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
    ) -> Client:
        client = Client(
            first_name=first_name,
            last_name=last_name,
            country=country,
            phone=phone,
            email=email,
            address=address,
        )
        self.session.add(client)
        self.session.flush()  # assigns identity id without committing
        return client

    def get(self, client_id: int) -> Client:
        client = self.session.get(Client, client_id)
        if not client:
            raise NotFoundError(f"Client {client_id} not found")
        return client

    def list(self, limit: int = 100, offset: int = 0) -> list[Client]:
        stmt = select(Client).order_by(Client.id.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt).all())

    def find_by_email(self, email: str) -> Client | None:
        stmt = select(Client).where(Client.email == email)
        return self.session.scalars(stmt).first()

    def search(self, query: str, limit: int = 50) -> list[Client]:
        q = f"%{query.strip()}%"
        stmt = (
            select(Client)
            .where(
                (Client.first_name.ilike(q)) | (Client.last_name.ilike(q)) | (Client.email.ilike(q))
            )
            .order_by(Client.last_name.asc(), Client.first_name.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def update(self, client_id: int, **fields) -> Client:
        client = self.get(client_id)
        for k, v in fields.items():
            if hasattr(client, k):
                setattr(client, k, v)
        self.session.flush()
        return client

    def delete(self, client_id: int) -> None:
        client = self.get(client_id)
        self.session.delete(client)
        self.session.flush()
