from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from epic_trips_crm.db.enums import ProviderName, SaleStatus
from epic_trips_crm.db.models import Sale
from epic_trips_crm.db.repositories.base import BaseRepository
from epic_trips_crm.utils.errors import NotFoundError


def _normalize_sale_status(status: SaleStatus | str) -> str:
    """
    What it does:
    - Converts status input into the exact DB enum string.

    Why it matters:
    - Prevents DB enum violations caused by typos/accents.
    - Keeps UI inputs flexible: accept enum or raw string.

    Behavior:
    - If passed a SaleStatus enum -> returns its value.
    - If passed a string -> validates it matches one of the allowed values.
    - Otherwise -> raises ValueError before any DB operation.
    """
    if isinstance(status, SaleStatus):
        return status.value

    allowed = {s.value for s in SaleStatus}
    if status not in allowed:
        raise ValueError(f"Invalid sale status '{status}'. Allowed: {sorted(allowed)}")
    return status


def _normalize_provider(provider: ProviderName | str) -> str:
    if isinstance(provider, ProviderName):
        return provider.value

    allowed = {p.value for p in ProviderName}
    if provider not in allowed:
        raise ValueError(f"Invalid provider '{provider}'. Allowed: {sorted(allowed)}")
    return provider


class SaleRepository(BaseRepository):
    def create(
        self,
        *,
        status: SaleStatus | str,
        client_id: int,
        trip_id: int,
        provider: ProviderName | str,
        booking_date: date | None = None,
        travel_start_date: date | None = None,
        travel_end_date: date | None = None,
        destination: str | None = None,
        concept: str | None = None,
        hotel: str | None = None,
        room_type: str | None = None,
        adults: int | None = None,
        children: str | None = None,
        confirmation_number: str | None = None,
        total_amount: Decimal | None = None,
        client_payments: Decimal | None = None,
        balance_amount: Decimal | None = None,
        payment_deadline: date | None = None,
        park_days: int | None = None,
        ticket_type: str | None = None,
        photos: str | None = None,
        express_passes: str | None = None,
        meal_plan: str | None = None,
        promotion: str | None = None,
        extras: str | None = None,
        app_account: str | None = None,
    ) -> Sale:
        """
        What it does:
        - Inserts a Sale row connected to an existing Client and Trip.

        Why it matters:
        - This is the core record that will later be submitted to the portal and generate commissions.

        Behavior:
        - Validates status before writing.
        - Adds to session and flushes so sale.id is available immediately.
        - Commit is handled by your transaction boundary (get_session()).
        """
        sale = Sale(
            status=_normalize_sale_status(status),
            client_id=client_id,
            trip_id=trip_id,
            provider=_normalize_provider(provider),
            booking_date=booking_date,
            travel_start_date=travel_start_date,
            travel_end_date=travel_end_date,
            destination=destination,
            concept=concept,
            hotel=hotel,
            room_type=room_type,
            adults=adults,
            children=children,
            confirmation_number=confirmation_number,
            total_amount=total_amount,
            client_payments=client_payments,
            balance_amount=balance_amount,
            payment_deadline=payment_deadline,
            park_days=park_days,
            ticket_type=ticket_type,
            photos=photos,
            express_passes=express_passes,
            meal_plan=meal_plan,
            promotion=promotion,
            extras=extras,
            app_account=app_account,
        )
        self.session.add(sale)
        self.session.flush()
        return sale

    def get(
        self,
        sale_id: int,
        *,
        include_client: bool = False,
        include_trip: bool = False,
        include_commission: bool = False,
    ) -> Sale:
        """
        What it does:
        - Fetches a Sale by primary key.

        Why it matters:
        - Sale detail screens and workflows need a stable read method.

        Behavior:
        - Optionally eager-loads related objects to avoid lazy queries after session closes.
        """
        if not include_client and not include_trip and not include_commission:
            sale = self.session.get(Sale, sale_id)
            if not sale:
                raise NotFoundError(f"Sale {sale_id} not found")
            return sale

        opts = []
        if include_client:
            opts.append(selectinload(Sale.client))
        if include_trip:
            opts.append(selectinload(Sale.trip))
        if include_commission:
            opts.append(selectinload(Sale.commission))

        stmt = select(Sale).where(Sale.id == sale_id).options(*opts)
        sale = self.session.scalars(stmt).first()
        if not sale:
            raise NotFoundError(f"Sale {sale_id} not found")
        return sale

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        include_client: bool = False,
        include_trip: bool = False,
    ) -> list[Sale]:
        """
        What it does:
        - Lists recent sales.

        Why it matters:
        - Powers your Sales main screen.

        Behavior:
        - Optional eager-load for client/trip to prevent N+1 queries in UI lists.
        """
        stmt = select(Sale).order_by(Sale.id.desc()).limit(limit).offset(offset)
        if include_client:
            stmt = stmt.options(selectinload(Sale.client))
        if include_trip:
            stmt = stmt.options(selectinload(Sale.trip))
        return list(self.session.scalars(stmt).all())

    def list_by_trip(
        self,
        trip_id: int,
        *,
        limit: int = 200,
        offset: int = 0,
        include_client: bool = False,
    ) -> list[Sale]:
        """
        What it does:
        - Lists all sales for a given trip.

        Why it matters:
        - Trip detail screens need to show all booked items/sales.

        Behavior:
        - Filters by Sale.trip_id and orders by id desc.
        """
        stmt = (
            select(Sale)
            .where(Sale.trip_id == trip_id)
            .order_by(Sale.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_client:
            stmt = stmt.options(selectinload(Sale.client))
        return list(self.session.scalars(stmt).all())

    def list_by_client(
        self,
        client_id: int,
        *,
        limit: int = 200,
        offset: int = 0,
        include_trip: bool = False,
    ) -> list[Sale]:
        """
        What it does:
        - Lists all sales for a given client.

        Why it matters:
        - Client profile screens and reporting.

        Behavior:
        - Filters by Sale.client_id.
        """
        stmt = (
            select(Sale)
            .where(Sale.client_id == client_id)
            .order_by(Sale.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_trip:
            stmt = stmt.options(selectinload(Sale.trip))
        return list(self.session.scalars(stmt).all())

    def list_by_status(
        self,
        status: SaleStatus | str,
        *,
        limit: int = 200,
        offset: int = 0,
        include_client: bool = False,
        include_trip: bool = False,
    ) -> list[Sale]:
        """
        What it does:
        - Lists sales filtered by status.

        Why it matters:
        - Workflow filtering (e.g., see only 'Reservada' or 'Liquidada').

        Behavior:
        - Normalizes status; invalid values raise ValueError.
        """
        status_value = _normalize_sale_status(status)
        stmt = (
            select(Sale)
            .where(Sale.status == status_value)
            .order_by(Sale.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_client:
            stmt = stmt.options(selectinload(Sale.client))
        if include_trip:
            stmt = stmt.options(selectinload(Sale.trip))
        return list(self.session.scalars(stmt).all())

    def list_by_provider(
        self,
        provider: ProviderName | str,
        *,
        limit: int = 200,
        offset: int = 0,
        include_client: bool = False,
        include_trip: bool = False,
    ) -> list[Sale]:
        """
        What it does:
        - Lists sales filtered by provider.

        Why it matters:
        - Commission submission is often provider-specific; this helps batching.

        Behavior:
        - Filters by Sale.provider (DB enum).
        """
        provider_value = _normalize_provider(provider)
        stmt = (
            select(Sale)
            .where(Sale.provider == provider_value)
            .order_by(Sale.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_client:
            stmt = stmt.options(selectinload(Sale.client))
        if include_trip:
            stmt = stmt.options(selectinload(Sale.trip))
        return list(self.session.scalars(stmt).all())

    def find_by_confirmation_number(self, confirmation_number: str) -> Sale | None:
        """
        What it does:
        - Finds a sale by provider confirmation number.

        Why it matters:
        - Useful lookup when the portal gives you a confirmation and you need the sale record.

        Behavior:
        - Returns None if not found.
        """
        stmt = select(Sale).where(Sale.confirmation_number == confirmation_number)
        return self.session.scalars(stmt).first()

    def list_missing_confirmation_number(self, *, limit: int = 200) -> list[Sale]:
        """
        What it does:
        - Lists sales where confirmation_number is null/empty.

        Why it matters:
        - Data hygiene; these will usually block commission submission.

        Behavior:
        - Returns a list (possibly empty).
        """
        stmt = (
            select(Sale)
            .where((Sale.confirmation_number.is_(None)) | (Sale.confirmation_number == ""))
            .order_by(Sale.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def list_with_payment_deadline_on_or_before(
        self, deadline: date, *, limit: int = 200
    ) -> list[Sale]:
        """
        What it does:
        - Lists sales with payment_deadline <= deadline.

        Why it matters:
        - Helps you prioritize follow-ups and avoid missed deadlines.

        Behavior:
        - Filters by Sale.payment_deadline (date), ignoring NULL values.
        """
        stmt = (
            select(Sale)
            .where(Sale.payment_deadline.is_not(None))
            .where(Sale.payment_deadline <= deadline)
            .order_by(Sale.payment_deadline.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def update(self, sale_id: int, **fields) -> Sale:
        """
        What it does:
        - Updates fields on a Sale.

        Why it matters:
        - Your UI will update sales incrementally (payments, deadline, status, etc).

        Behavior:
        - If 'status' is provided, it is validated/normalized.
        - Flushes changes so they’re persisted on commit.
        """
        sale = self.get(sale_id)

        if "status" in fields and fields["status"] is not None:
            fields["status"] = _normalize_sale_status(fields["status"])

        if "provider" in fields and fields["provider"] is not None:
            fields["provider"] = _normalize_provider(fields["provider"])

        for k, v in fields.items():
            if hasattr(sale, k):
                setattr(sale, k, v)

        self.session.flush()
        return sale

    def delete(self, sale_id: int) -> None:
        """
        What it does:
        - Deletes a Sale.

        Why it matters:
        - Cleanup/testing. In production you may prefer soft deletes later.

        Behavior:
        - If a Commission exists and FK is CASCADE from commissions.sale_id,
          deletion will also delete the commission row (DB handles it).
        """
        sale = self.get(sale_id)
        self.session.delete(sale)
        self.session.flush()
