import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import SMARD


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_smard_api_mock(mocker, mock_response):
    """Test the SMARD.de API by validating the index request followed by the actual data request."""
    
    durations = [15, 60]

    for duration in durations:
        # Request 1: The API first fetches the index file containing available timestamps
        mock_index_data = {"timestamps": [1783252800000]}  # Array of available epoch timestamps in milliseconds
        
        # Request 2: The API then fetches the actual price data for the chosen timestamp
        mock_actual_data = {
            "series": [
                [1783252800000, 45.50],  # July 5, 2026 12:00:00 UTC
                [1783256400000, 52.10]   # July 5, 2026 13:00:00 UTC
            ]
        }
        
        resp_index = mock_response(mock_index_data, 200)
        resp_data = mock_response(mock_actual_data, 200)
        
        # Patch aiohttp to return the index first, and the actual series data second
        get_mock = mocker.patch("aiohttp.ClientSession.get", side_effect=[resp_index, resp_data])

        async with aiohttp.ClientSession() as session:
            service = SMARD.SMARD(
                market_area="DE-LU",
                duration=duration,
                session=session
            )
            
            # Execute the fetch logic (this triggers both requests sequentially)
            await service.fetch()
            
            # Verify aiohttp was triggered exactly twice per duration loop
            assert get_mock.call_count == 2
            
            # Inspect call 1: Requesting the index file
            call_index_args, _ = get_mock.call_args_list[0]
            assert "index_" in call_index_args[0]
            assert call_index_args[0].endswith(".json")
            
            # Inspect call 2: Requesting the data file based on the timestamp from the index
            call_data_args, _ = get_mock.call_args_list[1]
            assert "1783252800000.json" in call_data_args[0]
            
            # Validate mapping values divided by 1000.0 (MWh -> kWh conversion)
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            assert service.marketdata[0].market_price_per_kwh == pytest.approx(45.50 / 1000.0)
            
            # Reset mock counter for the next duration iteration
            get_mock.reset_mock()
