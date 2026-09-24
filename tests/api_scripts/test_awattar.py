import os
import sys
from datetime import datetime

import aiohttp
import pytest
import time_machine
from homeassistant.util import dt as dt_util

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.const import CONF_SOURCE_AWATTAR
from custom_components.epex_spot.EPEXSpot import API_REGISTRY


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")  # Freeze time to July 5, 2026
async def test_awattar_api_mock(mocker, mock_response):
    """Test the Awattar API with a mocked response, query parameters, and fixed timestamps."""
    
    mock_data = {
        "object": "list",
        "data": [
            {
                "start_timestamp": 1783252800000,  # July 5, 2026 12:00:00 UTC
                "end_timestamp": 1783256400000,    # July 5, 2026 13:00:00 UTC
                "marketprice": 85.50,
                "unit": "Eur/MWh"
            }
        ]
    }
    
    resp = mock_response(mock_data, 200)
    get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Test matrix for supported market areas and durations
    check = {"at": 15, "de": 60}
    
    # Pre-calculate expected timestamps based on the frozen time (July 5, 2026)
    tz = dt_util.get_time_zone("Europe/Amsterdam")
    # Start: July 4, 2026 00:00:00 +02:00
    expected_start_dt = datetime(2026, 7, 4, 0, 0, 0, tzinfo=tz)
    expected_start_ms = int(expected_start_dt.timestamp() * 1000)
    
    # End: July 7, 2026 00:00:00 +02:00
    expected_end_dt = datetime(2026, 7, 7, 0, 0, 0, tzinfo=tz)
    expected_end_ms = int(expected_end_dt.timestamp() * 1000)

    for area, duration in check.items():
        async with aiohttp.ClientSession() as session:
            api_class = API_REGISTRY[CONF_SOURCE_AWATTAR]
            service = api_class(
                market_area=area, session=session, duration=duration
            )
            
            # Execute the fetch logic
            await service.fetch()
            
            # Verify aiohttp was triggered
            get_mock.assert_called_once()
            
            # Extract and validate call arguments
            called_url, called_kwargs = get_mock.call_args
            
            # Validate dynamic URL substitution
            assert called_url[0] == f"https://api.awattar.{area}/v1/marketdata"
            
            # Validate query parameters
            assert "params" in called_kwargs
            params = called_kwargs["params"]
            
            # Validate exact timestamps calculated by the integration
            assert params["start"] == expected_start_ms
            assert params["end"] == expected_end_ms
            
            # Validate market data processing
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            assert service.marketdata[0].market_price_per_kwh == 0.0855
            
            # Reset mock counter for the next loop iteration
            get_mock.reset_mock()