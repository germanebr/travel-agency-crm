from __future__ import annotations

from dataclasses import dataclass

from epic_trips_crm.services.portal_client import PortalCredentials, SubmissionResult


@dataclass
class FakePortalClient:
    """
    What it does:
    - Fake portal client used for service tests (no web automation).

    Why it matters:
    - Lets us test business workflow deterministically without hitting the real portal.

    Behavior:
    - login() records that it was called.
    - submit_sale() stores payload and returns a fixed confirmation id.
    """

    confirmation_id: str = "FAKE-CONF-123"
    login_called: bool = False
    last_payload: dict | None = None

    def login(self, creds: PortalCredentials) -> None:
        self.login_called = True

    def submit_sale(self, payload: dict) -> SubmissionResult:
        self.last_payload = payload
        return SubmissionResult(confirmation_id=self.confirmation_id)
