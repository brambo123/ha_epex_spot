import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import EnergyZero

@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +00:00")  # Freeze time to July 5, 2026
async def test_energyzero_api_mock(mocker, mock_response):
    """Test the EnergyZero API with a mocked response, query parameters, and minimum points validation."""
    
    # 1. Generate enough mock data to bypass the minimal data points requirement
    # For a 15-minute interval, it expects at least 23 * 4 = 92 points.
    # Let's generate 96 points (a full 24-hour day of quarter-hourly entries) to be safe.
    mock_base_entries = []
    for hour in range(24):
        for minute in [0, 15, 30, 45]:
            mock_base_entries.append({
                "start": f"2026-07-05T{hour:02d}:{minute:02d}:00+00:00",
                "price": {"value": 0.23456}
            })
            
    mock_data = {"base": mock_base_entries}
    
    resp = mock_response(mock_data, 200)
    get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Test matrix for both supported durations
    test_matrix = {
        "nl": 15,
        "nl": 60
    }

    for area, duration in test_matrix.items():
        async with aiohttp.ClientSession() as session:
            service = EnergyZero.EnergyZero(
                market_area=area, duration=duration, session=session
            )
            
            # Execute the fetch logic
            await service.fetch()
            
            # Verify aiohttp was triggered
            get_mock.assert_called_once()
            
            # Extract and validate call arguments
            called_url, called_kwargs = get_mock.call_args
            
            # Validate Base URL
            assert called_url[0] == "https://public.api.energyzero.nl/public/v1/prices"
            
            # Validate Query Parameters
            assert "params" in called_kwargs
            params = called_kwargs["params"]
            
            # Due to time_machine, the formatted date should match exactly
            assert params["date"] == "05-07-2026"
            assert params["energyType"] == "ENERGY_TYPE_ELECTRICITY"
            
            expected_interval = "INTERVAL_QUARTER" if duration == 15 else "INTERVAL_HOUR"
            assert params["interval"] == expected_interval
            
            # Validate market data processing
            assert service.marketdata is not None
            assert len(service.marketdata) == 96
            assert service.marketdata[0].market_price_per_kwh == 0.23456
            
            # Reset mock counter for the next iteration
            get_mock.reset_mock()
