from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PortalCredentials:
    username: str
    password: str
    portal_real_submit: bool = False


@dataclass(frozen=True)
class SubmissionResult:
    confirmation_id: str


class PortalClient(Protocol):
    """
    What it does:
    - Defines the API your service expects from a portal automation client.

    Why it matters:
    - The service stays stable while the implementation can change
      (Fake for tests, Playwright for real use).

    Behavior:
    - login() establishes an authenticated session.
    - submit_sale() submits a sale and returns a confirmation ID.
    """

    def login(self, creds: PortalCredentials) -> None: ...

    def submit_sale(self, payload: dict) -> SubmissionResult: ...
