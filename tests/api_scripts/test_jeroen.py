import os
import sys

import aiohttp
import pytest
import time_machine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.const import CONF_SOURCE_JEROEN
from custom_components.epex_spot.EPEXSpot import API_REGISTRY


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_jeroen_api_mock(mocker, mock_response):
    """Test the Jeroen.nl API mock and string-to-float comma replacement."""
    
    durations = [15, 60]

    for duration in durations:
        # Returns a flat list of items
        mock_data = [
            {
                "datum_utc": "2026-07-05 12:00:00",
                "prijs_excl_belastingen": "0,123400"
            },
            {
                "datum_utc": "2026-07-05 12:15:00",
                "prijs_excl_belastingen": "0,145000"
            },
            {
                "datum_utc": "2026-07-05 12:30:00",
                "prijs_excl_belastingen": "0,112000"
            },
            {
                "datum_utc": "2026-07-05 12:45:00",
                "prijs_excl_belastingen": "0,134000"
            }
        ]
        
        resp = mock_response(mock_data, 200)
        get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

        async with aiohttp.ClientSession() as session:
            api_class = API_REGISTRY[CONF_SOURCE_JEROEN]
            service = api_class(
                market_area="nl",
                token="demo",
                duration=duration,
                session=session
            )
            
            await service.fetch()
            
            assert get_mock.call_count > 0
            called_url, _ = get_mock.call_args
            assert "https://jeroen.nl/api/dynamische-energieprijzen/v2/" in called_url[0]
            
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            
            if duration == 15:
                assert service.marketdata[0].market_price_per_kwh == 0.1234
            else:
                # 60 min compresses/averages the four 15 min points
                expected_avg = (0.1234 + 0.145 + 0.112 + 0.134) / 4.0
                assert service.marketdata[0].market_price_per_kwh == round(expected_avg, 6)
                
            get_mock.reset_mock()
