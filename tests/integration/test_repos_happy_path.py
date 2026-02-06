import uuid
from datetime import date

import pytest
from sqlalchemy import text

from epic_trips_crm.config.settings import settings
from epic_trips_crm.db.engine import get_session
from epic_trips_crm.db.enums import ProviderName, SaleStatus, TripStatus
from epic_trips_crm.db.repositories.clients import ClientRepository
from epic_trips_crm.db.repositories.commissions import CommissionRepository
from epic_trips_crm.db.repositories.sales import SaleRepository
from epic_trips_crm.db.repositories.trips import TripRepository

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not settings.database_url, reason="DATABASE_URL not configured")
def test_repos_happy_path_end_to_end():
    """
    What it does:
    - Creates a client, trip, sale, commission.
    - Updates commission confirmation reference (portal confirmation ID).

    Why it matters:
    - Validates the core business flow your scraper + UI will rely on.

    Behavior:
    - Runs against the real Neon DB.
    - Uses a unique email per run to avoid collisions.
    - Cleans up created rows at the end (reverse FK order).
    """
    unique = uuid.uuid4().hex[:10]
    email = f"e2e_{unique}@example.com"

    with get_session() as session:
        # Optional: smoke ping to ensure connection is truly live
        assert session.execute(text("SELECT 1")).scalar_one() == 1

        clients = ClientRepository(session)
        trips = TripRepository(session)
        sales = SaleRepository(session)
        commissions = CommissionRepository(session)

        # 1) Create Client
        client = clients.create(first_name="E2E", last_name="Test", email=email)
        assert client.id is not None

        # 2) Create Trip
        trip = trips.create(
            trip_name="Disney World Feb",
            status=TripStatus.PROXIMO,
            client_id=client.id,
            start_month="Febrero",
            start_year=2026,
        )
        assert trip.id is not None
        assert trip.client_id == client.id

        # 3) Create Sale
        sale = sales.create(
            status=SaleStatus.RESERVADA,
            client_id=client.id,
            trip_id=trip.id,
            provider=ProviderName.DISNEY,
            booking_date=date.today(),
            destination="Orlando",
            confirmation_number=f"CONF-{unique}",
        )
        assert sale.id is not None
        assert sale.trip_id == trip.id

        # 4) Create Commission
        commission = commissions.create(sale_id=sale.id)
        assert commission.id is not None
        assert commission.sale_id == sale.id

        # 5) Update Commission confirmation ref (simulates scraper writing portal ID)
        updated = commissions.set_form_ref(sale.id, f"PORTAL-{unique}")
        assert updated.commission_form_ref == f"PORTAL-{unique}"

        # Cleanup (important because some FKs are RESTRICT)
        commissions.delete(commission.id)
        sales.delete(sale.id)
        trips.delete(trip.id)
        clients.delete(client.id)
