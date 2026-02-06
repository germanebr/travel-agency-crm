import uuid
from datetime import date

import pytest

from epic_trips_crm.config.settings import settings
from epic_trips_crm.db.engine import get_session
from epic_trips_crm.db.enums import ProviderName, SaleStatus, TripStatus
from epic_trips_crm.db.repositories.clients import ClientRepository
from epic_trips_crm.db.repositories.commissions import CommissionRepository
from epic_trips_crm.db.repositories.sales import SaleRepository
from epic_trips_crm.db.repositories.trips import TripRepository
from epic_trips_crm.services.portal_client import PortalCredentials
from epic_trips_crm.services.sales_submission import SalesSubmissionService
from epic_trips_crm.testing.fakes import FakePortalClient

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not settings.database_url, reason="DATABASE_URL not configured")
def test_sales_submission_service_sets_commission_form_ref():
    unique = uuid.uuid4().hex[:10]
    email = f"submit_{unique}@example.com"

    fake_portal = FakePortalClient(confirmation_id=f"PORTAL-{unique}")
    service = SalesSubmissionService(portal=fake_portal)

    with get_session() as session:
        clients = ClientRepository(session)
        trips = TripRepository(session)
        sales = SaleRepository(session)
        comms = CommissionRepository(session)

        client = clients.create(first_name="Submit", last_name="Test", email=email)
        trip = trips.create(
            trip_name="Submission Flow", status=TripStatus.PROXIMO, client_id=client.id
        )

        sale = sales.create(
            status=SaleStatus.RESERVADA,
            client_id=client.id,
            trip_id=trip.id,
            provider=ProviderName.DISNEY,
            booking_date=date.today(),
            confirmation_number=f"CONF-{unique}",
        )

        # Run workflow
        outcome = service.submit_sale(
            session=session,
            sale_id=sale.id,
            creds=PortalCredentials(username="x", password="y"),
        )

        assert fake_portal.login_called is True
        assert outcome.sale_id == sale.id
        assert outcome.confirmation_id == f"PORTAL-{unique}"

        # Verify persisted to DB
        commission = comms.get_by_sale_id(sale.id)
        assert commission is not None
        assert commission.commission_form_ref == f"PORTAL-{unique}"

        # Cleanup
        comms.delete(commission.id)
        sales.delete(sale.id)
        trips.delete(trip.id)
        clients.delete(client.id)
