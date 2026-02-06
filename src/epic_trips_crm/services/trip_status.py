from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select

from epic_trips_crm.db.enums import SaleStatus, TripStatus
from epic_trips_crm.db.models import Sale
from epic_trips_crm.db.repositories.trips import TripRepository


@dataclass(frozen=True)
class TripStatusComputation:
    earliest_start: date | None
    latest_end: date | None
    computed_status: TripStatus | None


def compute_trip_status_from_sales(
    sales: Iterable[Sale],
    *,
    today: date,
) -> TripStatusComputation:
    """
    What it does:
    - Computes a TripStatus based on the earliest travel_start_date and latest travel_end_date
      across eligible sales.

    Why it matters:
    - Keeps status logic deterministic and unit-testable (pure function).
    - Lets the DB update function stay small.

    Behavior:
    - Filters out sales with status Cancelada / No aplica.
    - If no eligible sales or no start dates -> computed_status=None (caller decides whether to change trip).
    - Otherwise returns Próximo/Viajando/Finalizado based on date comparisons.
    """
    excluded = {SaleStatus.CANCELADA.value, SaleStatus.NO_APLICA.value}

    eligible = [s for s in sales if (s.status not in excluded)]
    starts = [s.travel_start_date for s in eligible if s.travel_start_date is not None]
    ends = [s.travel_end_date for s in eligible if s.travel_end_date is not None]

    earliest_start = min(starts) if starts else None
    latest_end = max(ends) if ends else None

    if earliest_start is None:
        return TripStatusComputation(
            earliest_start=None,
            latest_end=latest_end,
            computed_status=None,
        )

    if today < earliest_start:
        status = TripStatus.PROXIMO
    else:
        if latest_end is None:
            status = TripStatus.VIAJANDO
        else:
            status = TripStatus.VIAJANDO if today <= latest_end else TripStatus.FINALIZADO

    return TripStatusComputation(
        earliest_start=earliest_start,
        latest_end=latest_end,
        computed_status=status,
    )


def sync_trip_status_from_sales(
    *,
    session,
    trip_id: int,
    today: date | None = None,
) -> TripStatus | None:
    """
    What it does:
    - Loads trip + its sales, computes desired trip status, and updates the trip if needed.

    Why it matters:
    - This is the callable your UI and future automation will use after creating/updating sales.

    Behavior:
    - If trip is Cancelado -> returns Cancelado and does not change it.
    - If computation yields None -> returns None (no change).
    - If computed status differs -> updates trip.status and flushes.
    - Commit/rollback handled by outer get_session() boundary.
    """
    today = today or date.today()

    trips = TripRepository(session)
    trip = trips.get(trip_id)

    # Respect manual final state
    if trip.status == TripStatus.CANCELADO.value:
        return TripStatus.CANCELADO

    sales = list(session.scalars(select(Sale).where(Sale.trip_id == trip_id)).all())
    result = compute_trip_status_from_sales(sales, today=today)

    if result.computed_status is None:
        return None

    desired = result.computed_status.value
    if trip.status != desired:
        trips.update(trip_id, status=desired)

    return result.computed_status
