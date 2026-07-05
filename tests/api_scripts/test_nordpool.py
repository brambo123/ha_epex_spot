import os
import sys
import aiohttp
import pytest
import time_machine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import Nordpool


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_nordpool_api_mock(mocker, mock_response):
    """Test Nordpool DayAhead API with sequential calls for today and tomorrow."""
    
    durations = [15, 60]

    for duration in durations:
        mock_data_today = {
            "multiIndexEntries": [
                {
                    "deliveryStart": "2026-07-05T12:00:00Z",
                    "deliveryEnd": "2026-07-05T13:00:00Z",
                    "entryPerArea": {
                        "NL": 85.50
                    }
                }
            ]
        }
        
        mock_data_tomorrow = {
            "multiIndexEntries": [
                {
                    "deliveryStart": "2026-07-06T12:00:00Z",
                    "deliveryEnd": "2026-07-06T13:00:00Z",
                    "entryPerArea": {
                        "NL": 92.10
                    }
                }
            ]
        }
        
        resp_today = mock_response(mock_data_today, 200)
        resp_tomorrow = mock_response(mock_data_tomorrow, 200)
        
        get_mock = mocker.patch("aiohttp.ClientSession.get", side_effect=[resp_today, resp_tomorrow])

        async with aiohttp.ClientSession() as session:
            service = Nordpool.Nordpool(
                market_area="NL",
                duration=duration,
                session=session
            )
            
            await service.fetch()
            
            # Nordpool requests today & tomorrow sequentially
            assert get_mock.call_count == 2
            
            # Validate query parameters of the first call (Today)
            call_today_args, call_today_kwargs = get_mock.call_args_list[0]
            assert call_today_args[0] == "https://dataportal-api.nordpoolgroup.com/api/DayAheadPriceIndices"
            
            params_today = call_today_kwargs["params"]
            assert params_today["date"] == "2026-07-05"
            assert params_today["indexNames"] == "NL"
            assert params_today["resolutionInMinutes"] == duration
            
            # Validate query parameters of the second call (Tomorrow)
            call_tomorrow_args, call_tomorrow_kwargs = get_mock.call_args_list[1]
            assert call_tomorrow_kwargs["params"]["date"] == "2026-07-06"
            
            # Validate combined market data entries
            assert len(service.marketdata) == 2
            assert service.marketdata[0].market_price_per_kwh == 0.08550
            assert service.marketdata[1].market_price_per_kwh == 0.09210
            
            get_mock.reset_mock()
