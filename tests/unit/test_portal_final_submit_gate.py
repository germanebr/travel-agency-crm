from __future__ import annotations

import inspect
import sys
import types

import pytest


class FakePortalClient:
    """
    Fake replacement for PlaywrightPortalClient.

    What it does:
    - Records calls without launching a real browser.

    Why it matters:
    - Unit tests must not hit the real portal.
    """
    def __init__(self, **kwargs):
        self.calls: list[tuple[str, object]] = []

    def login(self, creds):
        self.calls.append(("login", creds))

    def submit_sale(self, payload):
        self.calls.append(("submit_sale", payload))
        return types.SimpleNamespace(confirmation_id="EVO-FAKE-NO-SUBMIT")

    def final_submit_existing_form(self, form_id: str):
        self.calls.append(("final_submit_existing_form", form_id))
        return types.SimpleNamespace(confirmation_id=form_id)

    def close(self):
        self.calls.append(("close", None))


def _fake_settings():
    """
    Minimal settings stub.

    Behavior:
    - Satisfies _require_portal_settings() checks in run_submit_sale.py.
    """
    return types.SimpleNamespace(
        portal_url="https://example.invalid",
        portal_username="user",
        portal_password="pass",
    )


@pytest.mark.unit
def test_cli_final_submit_refuses_without_ack(monkeypatch):
    """
    What it does:
    - Runs CLI portal-final-submit without the acknowledgement flag.

    Why it matters:
    - Prevents accidental irreversible submission.

    Behavior:
    - Must raise RuntimeError before calling final_submit_existing_form.
    """
    import epic_trips_crm.scraping.run_submit_sale as runner

    monkeypatch.setattr(runner, "settings", _fake_settings(), raising=True)

    fake = FakePortalClient()
    monkeypatch.setattr(runner, "PlaywrightPortalClient", lambda **kwargs: fake, raising=True)

    # Ensure PortalCredentials creation doesn't depend on real dataclass behavior
    monkeypatch.setattr(
        runner,
        "PortalCredentials",
        lambda username, password: types.SimpleNamespace(username=username, password=password),
        raising=True,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["prog", "portal-final-submit", "--form-id", "EVO2026153349"],
        raising=True,
    )

    with pytest.raises(RuntimeError, match="Refusing to final-submit"):
        runner.main()

    assert ("final_submit_existing_form", "EVO2026153349") not in fake.calls
    assert any(name == "close" for name, _ in fake.calls)


@pytest.mark.unit
def test_cli_final_submit_calls_portal_when_ack(monkeypatch):
    """
    What it does:
    - Runs CLI portal-final-submit with the acknowledgement flag.

    Why it matters:
    - Guarantees the CLI is wired correctly to the portal client.

    Behavior:
    - Must call final_submit_existing_form(form_id) exactly once.
    """
    import epic_trips_crm.scraping.run_submit_sale as runner

    monkeypatch.setattr(runner, "settings", _fake_settings(), raising=True)

    fake = FakePortalClient()
    monkeypatch.setattr(runner, "PlaywrightPortalClient", lambda **kwargs: fake, raising=True)

    monkeypatch.setattr(
        runner,
        "PortalCredentials",
        lambda username, password: types.SimpleNamespace(username=username, password=password),
        raising=True,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "prog",
            "portal-final-submit",
            "--form-id",
            "EVO2026153349",
            "--i-understand-this-will-submit",
        ],
        raising=True,
    )

    runner.main()

    assert ("final_submit_existing_form", "EVO2026153349") in fake.calls
    # Ensure this command does not call SAFE submit_sale
    assert not any(name == "submit_sale" for name, _ in fake.calls)
    assert any(name == "close" for name, _ in fake.calls)


@pytest.mark.unit
def test_safe_submit_sale_does_not_reference_btnsubmit():
    """
    What it does:
    - Source-inspects PlaywrightPortalClient.submit_sale.

    Why it matters:
    - Enforces a safety invariant: SAFE path must never touch #btnSubmit.
    """
    from epic_trips_crm.scraping.travelagentportal_playwright import PlaywrightPortalClient

    src = inspect.getsource(PlaywrightPortalClient.submit_sale)
    assert "#btnSubmit" not in src
    assert "final_submit" not in src


@pytest.mark.unit
def test_final_submit_helper_references_btnsubmit():
    """
    What it does:
    - Source-inspects the final-submit helper implementation.

    Why it matters:
    - Ensures the real final-submit path actually targets #btnSubmit.
    """
    from epic_trips_crm.scraping.travelagentportal_playwright import PlaywrightPortalClient

    src = inspect.getsource(PlaywrightPortalClient._final_submit_commission_form)
    assert "#btnSubmit" in src