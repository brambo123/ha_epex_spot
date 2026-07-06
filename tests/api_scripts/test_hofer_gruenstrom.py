import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import HoferGruenstrom

@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")  # Freeze time to July 5, 2026
async def test_hofer_gruenstrom_api_mock(mocker, mock_response):
    """Test the Hofer Gruenstrom API with a mocked response for today and tomorrow."""
    
    # Define durations to test
    durations = [15, 60]

    for duration in durations:
        end_minute = 15 if duration == 15 else 0
        end_hour = 12 if duration == 15 else 13
        
        # Corrected structure: wrap the list inside a 'data' dictionary key
        mock_data_today = {
            "data": [
                {
                    "from": "2026-07-05T12:00:00+02:00",
                    "to": f"2026-07-05T{end_hour:02d}:{end_minute:02d}:00+02:00",
                    "price": 12.345
                }
            ]
        }
        
        mock_data_tomorrow = {
            "data": [
                {
                    "from": "2026-07-06T12:00:00+02:00",
                    "to": f"2026-07-06T{end_hour:02d}:{end_minute:02d}:00+02:00",
                    "price": 15.678
                }
            ]
        }
        
        resp_today = mock_response(mock_data_today, 200)
        resp_tomorrow = mock_response(mock_data_tomorrow, 200)
        
        # Patch using side_effect to return resp_today on call 1, and resp_tomorrow on call 2
        get_mock = mocker.patch("aiohttp.ClientSession.get", side_effect=[resp_today, resp_tomorrow])

        async with aiohttp.ClientSession() as session:
            service = HoferGruenstrom.HoferGruenstrom(
                market_area="at",
                duration=duration,
                session=session
            )
            
            # Execute the fetch logic (this triggers 2 requests internally)
            await service.fetch()
            
            # Verify aiohttp was triggered exactly twice
            assert get_mock.call_count == 2
            
            # Inspect the first call (Today)
            call_today_args, call_today_kwargs = get_mock.call_args_list[0]
            expected_url_today = "https://www.xn--hofer-grnstrom-nsb.at/service/energy-manager/spot-prices?year=2026&month=7&day=5"
            assert call_today_args[0] == expected_url_today
            
            # Inspect the second call (Tomorrow)
            call_tomorrow_args, call_tomorrow_kwargs = get_mock.call_args_list[1]
            expected_url_tomorrow = "https://www.xn--hofer-grnstrom-nsb.at/service/energy-manager/spot-prices?year=2026&month=7&day=6"
            assert call_tomorrow_args[0] == expected_url_tomorrow
            
            # Validate combined market data processing
            assert service.marketdata is not None
            assert len(service.marketdata) == 2
            assert service.marketdata[0].market_price_per_kwh == .12345
            assert service.marketdata[1].market_price_per_kwh == .15678
            
            # Reset mock counter for the next duration iteration
            get_mock.reset_mock()
