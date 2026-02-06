import uuid
from datetime import date, timedelta

import pytest

from epic_trips_crm.config.settings import settings
from epic_trips_crm.db.engine import get_session
from epic_trips_crm.db.enums import ProviderName, SaleStatus, TripStatus
from epic_trips_crm.db.repositories.clients import ClientRepository
from epic_trips_crm.db.repositories.commissions import CommissionRepository
from epic_trips_crm.db.repositories.sales import SaleRepository
from epic_trips_crm.db.repositories.trips import TripRepository
from epic_trips_crm.services.trip_status import sync_trip_status_from_sales

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not settings.database_url, reason="DATABASE_URL not configured")
def test_trip_status_sync_from_sales_dates():
    """
    What it does:
    - Verifies trip status changes based on sales dates.
    - Verifies Cancelado is not overridden.

    Why it matters:
    - This is core domain behavior you want in the app.

    Behavior:
    - Uses controlled dates relative to a chosen 'today' for deterministic assertions.
    - Cleans up inserted data to keep your Neon DB tidy.
    """
    unique = uuid.uuid4().hex[:10]
    email = f"status_sync_{unique}@example.com"

    # Deterministic "today" for the test
    today = date.today()

    with get_session() as session:
        clients = ClientRepository(session)
        trips = TripRepository(session)
        sales = SaleRepository(session)
        commissions = CommissionRepository(session)

        client = clients.create(first_name="Status", last_name="Sync", email=email)

        trip = trips.create(
            trip_name="Trip Status Test",
            status=TripStatus.PROXIMO,
            client_id=client.id,
        )

        # Sale that started yesterday and ends tomorrow -> should put trip into VIAJANDO
        sale = sales.create(
            status=SaleStatus.RESERVADA,
            client_id=client.id,
            trip_id=trip.id,
            provider=ProviderName.DISNEY,
            travel_start_date=today - timedelta(days=1),
            travel_end_date=today + timedelta(days=1),
            confirmation_number=f"CONF-{unique}",
        )
        comm = commissions.create(sale_id=sale.id)

        new_status = sync_trip_status_from_sales(session=session, trip_id=trip.id, today=today)
        assert new_status == TripStatus.VIAJANDO
        assert trips.get(trip.id).status == TripStatus.VIAJANDO.value

        # Move sale end date to the past -> trip should become FINALIZADO
        sales.update(sale.id, travel_end_date=today - timedelta(days=2))
        new_status = sync_trip_status_from_sales(session=session, trip_id=trip.id, today=today)
        assert new_status == TripStatus.FINALIZADO
        assert trips.get(trip.id).status == TripStatus.FINALIZADO.value

        # Manual cancel should never be overridden
        trips.update(trip.id, status=TripStatus.CANCELADO.value)
        new_status = sync_trip_status_from_sales(session=session, trip_id=trip.id, today=today)
        assert new_status == TripStatus.CANCELADO
        assert trips.get(trip.id).status == TripStatus.CANCELADO.value

        # Cleanup (reverse FK order)
        commissions.delete(comm.id)
        sales.delete(sale.id)
        trips.delete(trip.id)
        clients.delete(client.id)
