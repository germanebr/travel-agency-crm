from __future__ import annotations

from datetime import date
from decimal import Decimal
from importlib import import_module
from typing import Any

from sqlalchemy import Boolean

# --- Import helpers (robust to small naming differences) ---------------------


def import_first(module_path: str, candidates: list[str]) -> Any:
    mod = import_module(module_path)
    for name in candidates:
        if hasattr(mod, name):
            return getattr(mod, name)
    raise ImportError(f"None of {candidates} found in {module_path}")


def enum_member(enum_cls: Any, preferred_names: list[str], fallback: Any) -> Any:
    """
    Tries to fetch enum members by name; if enums aren't used or names differ,
    returns the fallback value.
    """
    for n in preferred_names:
        if hasattr(enum_cls, n):
            return getattr(enum_cls, n)
    return fallback


# --- Imports (adjust module paths only if your project differs) --------------


# Models
Checklist = import_first("epic_trips_crm.db.models", ["Checklist"])

# Enums
enums_mod = import_module("epic_trips_crm.db.enums")
TripStatus = getattr(enums_mod, "TripStatus", None)
SaleStatus = getattr(enums_mod, "SaleStatus", None)
ProviderName = getattr(enums_mod, "ProviderName", None)

# Repositories
ClientsRepoCls = import_first(
    "epic_trips_crm.db.repositories.clients",
    ["ClientsRepository", "ClientRepository"],
)
TripsRepoCls = import_first(
    "epic_trips_crm.db.repositories.trips",
    ["TripsRepository", "TripRepository"],
)
SaleRepoCls = import_first(
    "epic_trips_crm.db.repositories.sales",
    ["SaleRepository", "SalesRepository"],
)
ChecklistRepoCls = import_first(
    "epic_trips_crm.db.repositories.checklist",
    ["ChecklistRepository"],
)


# --- Tests ------------------------------------------------------------------


def test_clients_create_and_list(session):
    clients = ClientsRepoCls(session)

    created = clients.create(
        first_name="Ana",
        last_name="García",
        country="MX",
        phone="5551234567",
        email="ana@example.com",
        address="CDMX",
    )
    assert created.id is not None

    rows = clients.list(limit=50)
    assert any(r.id == created.id for r in rows)


def test_trips_create_and_list(session):
    clients = ClientsRepoCls(session)
    trips = TripsRepoCls(session)

    c = clients.create(
        first_name="Luis",
        last_name="Pérez",
        country="MX",
        phone="5550000000",
        email="luis@example.com",
        address="CDMX",
    )

    # TripStatus names often vary; try common ones, otherwise fallback to a string
    status_value = (
        enum_member(TripStatus, ["PROXIMO", "PROXIMA", "NEXT", "UPCOMING"], "Próximo")
        if TripStatus is not None
        else "Próximo"
    )

    t = trips.create(
        trip_name="Orlando 2026",
        status=status_value,
        client_id=c.id,
        start_month="JUN",
        start_year=2026,
        end_month="JUN",
        end_year=2026,
        notes="Test trip",
    )
    assert t.id is not None

    rows = trips.list(limit=50)
    assert any(r.id == t.id for r in rows)


def test_sales_create_and_list(session):
    clients = ClientsRepoCls(session)
    trips = TripsRepoCls(session)
    sales = SaleRepoCls(session)

    c = clients.create(
        first_name="María",
        last_name="López",
        country="MX",
        phone="5551111111",
        email="maria@example.com",
        address="CDMX",
    )

    status_value = (
        enum_member(TripStatus, ["PROXIMO", "PROXIMA", "NEXT", "UPCOMING"], "Próximo")
        if TripStatus is not None
        else "Próximo"
    )

    t = trips.create(
        trip_name="Disney 2026",
        status=status_value,
        client_id=c.id,
        start_month="JUL",
        start_year=2026,
        end_month="JUL",
        end_year=2026,
        notes="",
    )

    sale_status = (
        enum_member(SaleStatus, ["RESERVADA", "BOOKED", "RESERVED"], "Reservada")
        if SaleStatus is not None
        else "Reservada"
    )
    provider = (
        enum_member(ProviderName, ["DISNEY", "Disney"], "Disney")
        if ProviderName is not None
        else "Disney"
    )

    # IMPORTANT:
    # - SaleRepository.create() in your repo does NOT accept notes=.
    # - children is typed as str|None in your repo, so we pass "0".
    s = sales.create(
        status=sale_status,
        client_id=c.id,
        trip_id=t.id,
        provider=provider,
        destination="Orlando",
        concept="Parks + hotel",
        hotel="Pop Century",
        room_type="Standard",
        adults=2,
        children="0",
        confirmation_number="ABC123",
        booking_date=date(2026, 7, 1),
        travel_start_date=date(2026, 7, 10),
        travel_end_date=date(2026, 7, 16),
        total_amount=Decimal("1234.56"),
        client_payments=Decimal("200.00"),
        balance_amount=Decimal("1034.56"),
        payment_deadline=date(2026, 6, 15),
        park_days=4,
        ticket_type="Park Hopper",
        photos="Memory Maker",
        express_passes="No",
        meal_plan="No",
        promotion="Summer promo",
        extras="",
        app_account="maria@example.com",
    )
    assert s.id is not None

    rows = sales.list(limit=50)
    assert any(r.id == s.id for r in rows)


def test_checklist_get_or_create_and_update(session):
    clients = ClientsRepoCls(session)
    trips = TripsRepoCls(session)
    checklists = ChecklistRepoCls(session)

    c = clients.create(
        first_name="Carlos",
        last_name="Ruiz",
        country="MX",
        phone="5552222222",
        email="carlos@example.com",
        address="CDMX",
    )

    status_value = (
        enum_member(TripStatus, ["PROXIMO", "PROXIMA", "NEXT", "UPCOMING"], "Próximo")
        if TripStatus is not None
        else "Próximo"
    )

    t = trips.create(
        trip_name="Universal 2026",
        status=status_value,
        client_id=c.id,
        start_month="AUG",
        start_year=2026,
        end_month="AUG",
        end_year=2026,
        notes="",
    )

    ck = checklists.get_or_create_by_trip_id(t.id)
    assert ck.trip_id == t.id

    # Your ChecklistRepository.update_by_trip_id only updates attributes
    # that exist on the model, so we introspect to pick a real boolean column. :contentReference[oaicite:1]{index=1}
    bool_cols = [col.name for col in Checklist.__table__.columns if isinstance(col.type, Boolean)]
    assert bool_cols, "Checklist model has no boolean columns; update test cannot run."

    field_name = bool_cols[0]
    updated = checklists.update_by_trip_id(t.id, **{field_name: True})

    # Avoid static attribute access so linters don't complain on unknown attrs
    updated_any: Any = updated
    assert getattr(updated_any, field_name) is True
