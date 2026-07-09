import os
import sys
import aiohttp
import pytest

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import API_REGISTRY
from custom_components.epex_spot.const import CONF_SOURCE_ENERGYFORECAST

@pytest.mark.asyncio
async def test_energyforecast_api_mock(mocker, mock_response):
    """Test the Energyforecast API with a mocked response and validate query parameters."""
    
    # 1. Prepare simulated API response matching data["forecast"]["data"]
    mock_data = {
        "forecast": {
            "data": [
                {
                    "start": "2026-07-05T12:00:00+00:00",
                    "end": "2026-07-05T13:00:00+00:00",
                    "price": 0.123456
                },
                {
                    "start": "2026-07-05T13:00:00+00:00",
                    "end": "2026-07-05T14:00:00+00:00",
                    "price": 0.145678
                }
            ]
        }
    }
    
    resp = mock_response(mock_data, 200)
    get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Test matrix for both supported resolutions/durations
    test_matrix = {
        "de": 60,   # Will map to resolution "HOURLY"
        "fr": 15    # Will map to resolution "QUARTER_HOURLY"
    }
    
    demo_token = "test_secure_token"

    for area, duration in test_matrix.items():
        async with aiohttp.ClientSession() as session:
            api_class = API_REGISTRY[CONF_SOURCE_ENERGYFORECAST]
            service = api_class(
                market_area=area, token=demo_token, session=session, duration=duration
            )
            
            # Execute the fetch logic
            await service.fetch()
            
            # Verify aiohttp was triggered
            get_mock.assert_called_once()
            
            # Extract and validate call arguments
            called_url, called_kwargs = get_mock.call_args
            
            # Validate Base URL
            assert called_url[0] == "https://www.energyforecast.de/api/v1/predictions/prices_for_ha"
            
            # Validate Query Parameters
            assert "params" in called_kwargs
            params = called_kwargs["params"]
            assert params["token"] == demo_token
            assert params["fixed_cost_cent"] == 0
            assert params["vat"] == 0
            
            expected_resolution = "HOURLY" if duration == 60 else "QUARTER_HOURLY"
            assert params["resolution"] == expected_resolution
            
            # Validate market data processing
            assert service.marketdata is not None
            assert len(service.marketdata) == 2
            assert service.marketdata[0].market_price_per_kwh == 0.123456
            
            # Reset mock counter for the next iteration
            get_mock.reset_mock()