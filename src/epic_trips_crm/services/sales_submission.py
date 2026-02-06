from __future__ import annotations

from dataclasses import dataclass

from epic_trips_crm.db.repositories.commissions import CommissionRepository
from epic_trips_crm.db.repositories.sales import SaleRepository
from epic_trips_crm.services.portal_client import PortalClient, PortalCredentials, SubmissionResult


@dataclass(frozen=True)
class SalesSubmissionOutcome:
    sale_id: int
    confirmation_id: str


class SalesSubmissionService:
    """
    What it does:
    - Orchestrates submitting a sale to the portal and storing confirmation ID in commissions.

    Why it matters:
    - Cross-table logic (sales + commissions + portal) does not belong in repositories.
    - This becomes the single entry point for your UI and future automation.

    Behavior:
    - Uses repositories for DB access.
    - Uses PortalClient for the portal interaction.
    - Flushes DB changes; commit/rollback are handled by the caller's session context manager.
    """

    def __init__(self, *, portal: PortalClient) -> None:
        self.portal = portal

    def submit_sale(
        self,
        *,
        session,
        sale_id: int,
        creds: PortalCredentials,
    ) -> SalesSubmissionOutcome:
        sales_repo = SaleRepository(session)
        comm_repo = CommissionRepository(session)

        # 1) Load sale (include relationships only if needed by payload)
        sale = sales_repo.get(sale_id, include_client=True, include_trip=True)

        # 2) Ensure commission record exists (so we always have somewhere to store confirmation_id)
        commission = comm_repo.get_by_sale_id(sale_id)
        if commission is None:
            commission = comm_repo.create(sale_id=sale_id)

        # 3) Build payload for the portal
        payload = self._build_payload(sale)

        # 4) Login + submit
        self.portal.login(creds)
        result: SubmissionResult = self.portal.submit_sale(payload)

        # 5) Store confirmation id
        comm_repo.set_form_ref(sale_id, result.confirmation_id)

        return SalesSubmissionOutcome(sale_id=sale_id, confirmation_id=result.confirmation_id)

    def _build_payload(self, sale) -> dict:
        """
        What it does:
        - Converts your Sale + related entities into a portal submission payload.

        Why it matters:
        - Keeps a single place to map DB fields to portal fields.
        - Easy to update when the portal form changes.

        Behavior:
        - Returns a dict with only the fields you need to submit.
        """
        client = sale.client
        trip = sale.trip

        return {
            "sale_id": sale.id,
            "provider": sale.provider,
            "booking_date": sale.booking_date.isoformat() if sale.booking_date else None,
            "travel_start_date": sale.travel_start_date.isoformat()
            if sale.travel_start_date
            else None,
            "travel_end_date": sale.travel_end_date.isoformat() if sale.travel_end_date else None,
            "confirmation_number": sale.confirmation_number,
            "destination": sale.destination,
            "total_amount": str(sale.total_amount) if sale.total_amount is not None else None,
            "client": {
                "first_name": client.first_name if client else None,
                "last_name": client.last_name if client else None,
                "email": client.email if client else None,
                "phone": client.phone if client else None,
            },
            "trip": {
                "trip_name": trip.trip_name if trip else None,
                "status": trip.status if trip else None,
            },
        }
