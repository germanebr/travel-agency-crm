from __future__ import annotations

from importlib import import_module


def import_first(module_path: str, candidates: list[str]):
    mod = import_module(module_path)
    for name in candidates:
        if hasattr(mod, name):
            return getattr(mod, name)
    raise ImportError(f"None of {candidates} found in {module_path}")


def enum_member(enum_cls: object | None, preferred_names: list[str], fallback: object):
    if enum_cls is None:
        return fallback
    for n in preferred_names:
        if hasattr(enum_cls, n):
            return getattr(enum_cls, n)
    return fallback


def test_trip_portal_form_ref_roundtrip_and_lookup(session):
    """
    Ensures:
    - TripRepository.create can persist portal_form_ref
    - TripRepository.get_by_portal_form_ref returns the owning trip
    """
    # Repos (support minor naming differences)
    ClientsRepoCls = import_first(
        "epic_trips_crm.db.repositories.clients",
        ["ClientsRepository", "ClientRepository"],
    )
    TripRepoCls = import_first(
        "epic_trips_crm.db.repositories.trips",
        ["TripRepository", "TripsRepository"],
    )

    # Enums (support both enum and raw string usage)
    enums_mod = import_module("epic_trips_crm.db.enums")
    TripStatus = getattr(enums_mod, "TripStatus", None)

    clients = ClientsRepoCls(session)
    trips = TripRepoCls(session)

    c = clients.create(
        first_name="Portal",
        last_name="RefTest",
        country="MX",
        phone="5553334444",
        email="portal.reftest@example.com",
        address="CDMX",
    )

    status_value = enum_member(
        TripStatus,
        ["PROXIMO", "PROXIMA", "NEXT", "UPCOMING"],
        "Próximo",
    )

    form_ref = "EVO_TEST_123456"

    created = trips.create(
        trip_name="Trip with Portal Ref",
        status=status_value,
        client_id=c.id,
        start_month="Julio",
        start_year=2026,
        end_month="Julio",
        end_year=2026,
        companions=None,
        flights=None,
        reservation_id=None,
        notes="",
        checklist_id=None,
        portal_form_ref=form_ref,
    )
    assert created.id is not None
    assert getattr(created, "portal_form_ref", None) == form_ref

    # list() should include the column too
    rows = trips.list(limit=50)
    assert any(getattr(t, "portal_form_ref", None) == form_ref for t in rows)

    # get_by_portal_form_ref should return the same trip
    found = trips.get_by_portal_form_ref(form_ref)
    assert found is not None
    assert found.id == created.id
    assert found.portal_form_ref == form_ref


def test_get_by_portal_form_ref_returns_none_when_missing(session):
    ClientsRepoCls = import_first(
        "epic_trips_crm.db.repositories.clients",
        ["ClientsRepository", "ClientRepository"],
    )
    TripRepoCls = import_first(
        "epic_trips_crm.db.repositories.trips",
        ["TripRepository", "TripsRepository"],
    )

    clients = ClientsRepoCls(session)
    trips = TripRepoCls(session)

    # Create at least one trip to ensure table isn't empty (not strictly required)
    c = clients.create(
        first_name="Any",
        last_name="Client",
        country="MX",
        phone="5550009999",
        email="any.client@example.com",
        address="CDMX",
    )

    enums_mod = import_module("epic_trips_crm.db.enums")
    TripStatus = getattr(enums_mod, "TripStatus", None)
    status_value = enum_member(
        TripStatus,
        ["PROXIMO", "PROXIMA", "NEXT", "UPCOMING"],
        "Próximo",
    )

    trips.create(
        trip_name="Trip without Portal Ref",
        status=status_value,
        client_id=c.id,
        portal_form_ref=None,
    )

    assert trips.get_by_portal_form_ref("EVO_DOES_NOT_EXIST") is None