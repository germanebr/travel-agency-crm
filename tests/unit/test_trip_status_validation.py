import pytest

from epic_trips_crm.db.enums import TripStatus
from epic_trips_crm.db.repositories.trips import _normalize_trip_status


def test_trip_status_accepts_enum():
    assert _normalize_trip_status(TripStatus.PROXIMO) == "Próximo"


def test_trip_status_rejects_invalid_string():
    with pytest.raises(ValueError):
        _normalize_trip_status("Proximo")  # missing accent


def test_trip_status_accepts_all_values():
    # Ensures all enum values are valid inputs
    for s in TripStatus:
        assert _normalize_trip_status(s.value) == s.value
