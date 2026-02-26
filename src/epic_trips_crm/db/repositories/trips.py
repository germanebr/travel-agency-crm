from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from epic_trips_crm.db.enums import TripStatus
from epic_trips_crm.db.models import Trip
from epic_trips_crm.db.repositories.base import BaseRepository
from epic_trips_crm.utils.errors import NotFoundError


def _normalize_trip_status(status: TripStatus | str) -> str:
    """
    What it does:
    - Converts status input into the exact string stored in Postgres.
    Why it matters:
    - Ensures accents/casing match the DB enum values (prevents DB errors).
    Behavior:
    - Accepts TripStatus enum or exact string values.
    - Raises ValueError for any invalid string.
    """
    if isinstance(status, TripStatus):
        return status.value

    # Allow raw strings from UI, but validate strictly
    allowed = {s.value for s in TripStatus}
    if status not in allowed:
        raise ValueError(f"Invalid trip status '{status}'. Allowed: {sorted(allowed)}")
    return status


class TripRepository(BaseRepository):
    def create(
        self,
        *,
        trip_name: str,
        status: TripStatus | str,
        client_id: int,
        start_month: str | None = None,
        start_year: int | None = None,
        end_month: str | None = None,
        end_year: int | None = None,
        companions: str | None = None,
        flights: str | None = None,
        reservation_id: int | None = None,
        notes: str | None = None,
        checklist_id: int | None = None,
        portal_form_ref: str | None = None,
    ) -> Trip:
        """
        What it does:
        - Inserts a new Trip row.
        Why it matters:
        - Trip is a core entity that anchors sales/checklist.
        Behavior:
        - Validates status against allowed enum values before DB write.
        - Flushes to obtain generated identity id immediately.
        """
        trip = Trip(
            trip_name=trip_name,
            status=_normalize_trip_status(status),
            client_id=client_id,
            start_month=start_month,
            start_year=start_year,
            end_month=end_month,
            end_year=end_year,
            companions=companions,
            flights=flights,
            reservation_id=reservation_id,
            notes=notes,
            checklist_id=checklist_id,
            portal_form_ref=portal_form_ref,
        )
        self.session.add(trip)
        self.session.flush()
        return trip

    def get(
        self, trip_id: int, *, include_client: bool = False, include_sales: bool = False
    ) -> Trip:
        """
        What it does:
        - Fetches one Trip by id.
        Why it matters:
        - Trip detail screens depend on this.
        Behavior:
        - Optional eager loads to avoid lazy-load queries after session closure.
        """
        if not include_client and not include_sales:
            trip = self.session.get(Trip, trip_id)
            if not trip:
                raise NotFoundError(f"Trip {trip_id} not found")
            return trip

        opts = []
        if include_client:
            opts.append(selectinload(Trip.client))
        if include_sales:
            opts.append(selectinload(Trip.sales))

        stmt = select(Trip).where(Trip.id == trip_id).options(*opts)
        trip = self.session.scalars(stmt).first()
        if not trip:
            raise NotFoundError(f"Trip {trip_id} not found")
        return trip

    def list(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        include_client: bool = False,
    ) -> list[Trip]:
        """
        What it does:
        - Lists recent trips.
        Why it matters:
        - Powers Trips main screen.
        Behavior:
        - Optional eager load of client to avoid N+1 queries.
        """
        stmt = select(Trip).order_by(Trip.id.desc()).limit(limit).offset(offset)
        if include_client:
            stmt = stmt.options(selectinload(Trip.client))
        return list(self.session.scalars(stmt).all())

    def list_by_client(
        self,
        client_id: int,
        *,
        include_client: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trip]:
        """
        What it does:
        - Lists trips for a given client.
        Why it matters:
        - Client profile view.
        Behavior:
        - Filters by Trip.client_id.
        """
        stmt = (
            select(Trip)
            .where(Trip.client_id == client_id)
            .order_by(Trip.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_client:
            stmt = stmt.options(selectinload(Trip.client))
        return list(self.session.scalars(stmt).all())

    def list_by_status(
        self,
        status: TripStatus | str,
        *,
        include_client: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Trip]:
        """
        What it does:
        - Lists trips filtered by status.
        Why it matters:
        - Workflow screens ("Próximo", "Viajando", "Cancelado").
        Behavior:
        - Normalizes/validates status before building the query.
        """
        status_value = _normalize_trip_status(status)
        stmt = (
            select(Trip)
            .where(Trip.status == status_value)
            .order_by(Trip.id.desc())
            .limit(limit)
            .offset(offset)
        )
        if include_client:
            stmt = stmt.options(selectinload(Trip.client))
        return list(self.session.scalars(stmt).all())

    def get_by_reservation_id(
        self, reservation_id: int, *, include_client: bool = False
    ) -> Trip | None:
        """
        What it does:
        - Fetches trip by unique reservation_id.
        Why it matters:
        - Fast lookup when you have a provider reservation number.
        Behavior:
        - Returns None if not found.
        """
        stmt = select(Trip).where(Trip.reservation_id == reservation_id)
        if include_client:
            stmt = stmt.options(selectinload(Trip.client))
        return self.session.scalars(stmt).first()

    def get_by_portal_form_ref(
        self, portal_form_ref: str, *, include_client: bool = False
    ) -> Trip | None:
        """
        What it does:
        - Fetches trip by portal form reference (EVO...).
        Why it matters:
        - Lets you jump from portal form ID to the owning trip quickly.
        Behavior:
        - Returns None if not found.
        """
        stmt = select(Trip).where(Trip.portal_form_ref == portal_form_ref)
        if include_client:
            stmt = stmt.options(selectinload(Trip.client))
        return self.session.scalars(stmt).first()

    def update(self, trip_id: int, **fields) -> Trip:
        """
        What it does:
        - Updates fields on a trip.
        Why it matters:
        - Form edits.
        Behavior:
        - If 'status' is provided, validates and normalizes it.
        - Ignores unknown field names safely (hasattr guard).
        """
        trip = self.get(trip_id)

        if "status" in fields and fields["status"] is not None:
            fields["status"] = _normalize_trip_status(fields["status"])

        for k, v in fields.items():
            if hasattr(trip, k):
                setattr(trip, k, v)

        self.session.flush()
        return trip

    def delete(self, trip_id: int) -> None:
        """
        What it does:
        - Deletes the trip.
        Why it matters:
        - Cleanup workflows.
        Behavior:
        - DB may block deletion if FK constraints restrict it (e.g., sales exist).
        """
        trip = self.get(trip_id)
        self.session.delete(trip)
        self.session.flush()