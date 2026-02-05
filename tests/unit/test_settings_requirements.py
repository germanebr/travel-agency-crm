import pytest

from epic_trips_crm.config.settings import require_database_url


def test_require_database_url_raises_when_missing():
    with pytest.raises(RuntimeError):
        require_database_url(None)
