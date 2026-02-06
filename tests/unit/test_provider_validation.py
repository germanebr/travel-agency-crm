import pytest

from epic_trips_crm.db.enums import ProviderName
from epic_trips_crm.db.repositories.sales import _normalize_provider


def test_provider_accepts_enum():
    assert _normalize_provider(ProviderName.DISNEY) == "Disney"


def test_provider_rejects_invalid_string():
    with pytest.raises(ValueError):
        _normalize_provider("Disny")
