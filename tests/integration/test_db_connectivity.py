import pytest
from sqlalchemy import text

from epic_trips_crm.config.settings import settings
from epic_trips_crm.db.engine import get_session

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not settings.database_url, reason="DATABASE_URL not set (via .env or env var)")
def test_can_connect_to_neon():
    with get_session() as s:
        assert s.execute(text("SELECT 1")).scalar_one() == 1
