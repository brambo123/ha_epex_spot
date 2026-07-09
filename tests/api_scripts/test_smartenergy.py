import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import API_REGISTRY
from custom_components.epex_spot.const import CONF_SOURCE_SMARTENERGY


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_smartenergy_api_mock(mocker, mock_response):
    """Test the smartENERGY API with a mocked quarterly and hourly response structure."""
    
    # Define durations to test
    durations = [15, 60]

    for duration in durations:
        mock_data = {
            "interval": duration,
            "unit": "ct/kwh",
            "data": [
                {
                    "date": "2026-07-05T12:00:00+02:00",
                    "value": 12.34
                }
            ]
        }
        
        resp = mock_response(mock_data, 200)
        get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

        async with aiohttp.ClientSession() as session:
            api_class = API_REGISTRY[CONF_SOURCE_SMARTENERGY]
            service = api_class(
                market_area="at",
                duration=duration,
                session=session
            )
            
            await service.fetch()
            
            get_mock.assert_called_once_with("https://apis.smartenergy.at/market/v1/price")
            
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            # Price in ct/kWh converted to EUR/kWh (e.g. divided by 100)
            assert service.marketdata[0].market_price_per_kwh == round(12.34 / 100.0 / 1.2, 6)
            
            get_mock.reset_mock()
