import aiohttp
import pytest
from homeassistant.util import dt as dt_util


class CentralMockResponse:
    def __init__(self, data, status):
        self._data = data
        self.status = status

    async def json(self):
        return self._data
        
    async def text(self):
        return self._data

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None, history=None, status=self.status, message="HTTP Error"
            )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_response():
    def _create_mock(json_data, status=200):
        return CentralMockResponse(json_data, status)
    return _create_mock

@pytest.fixture(autouse=True)
def set_home_assistant_timezone():
    original_tz = dt_util.DEFAULT_TIME_ZONE
    tz = dt_util.get_time_zone("Europe/Amsterdam")
    dt_util.set_default_time_zone(tz)
    yield
    dt_util.set_default_time_zone(original_tz)
