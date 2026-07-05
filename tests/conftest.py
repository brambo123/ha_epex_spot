import pytest
import aiohttp

class CentralMockResponse:
    def __init__(self, json_data, status):
        self._json_data = json_data
        self.status = status

    async def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                request_info=None, history=None, status=self.status, message="HTTP Error"
            )
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.fixture
def mock_response():
    def _create_mock(json_data, status=200):
        return CentralMockResponse(json_data, status)
    return _create_mock
