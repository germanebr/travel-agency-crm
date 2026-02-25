import pytest

from epic_trips_crm.db.enums import SaleStatus
from epic_trips_crm.db.repositories.sales import _normalize_sale_status


def test_sale_status_accepts_enum():
    assert _normalize_sale_status(SaleStatus.RESERVADA) == "Reservada"


def test_sale_status_rejects_invalid_string():
    with pytest.raises(ValueError):
        _normalize_sale_status("Reservado")  # typo
