import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import EnergyCharts


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")  # Freeze time to July 5, 2026
async def test_energycharts_api_mock(mocker, mock_response):
    """Test the EnergyCharts API with a mocked response and date validations."""
    
    # 1. Prepare simulated Energy-Charts array structure
    mock_data = {
        "unix_seconds": [1783256400, 1783257300, 1783258200, 1783259100, 1783260000],
        "price": [50.5, 62.1, 40.8, 50.6, 65.3]
    }
    
    resp = mock_response(mock_data, 200)
    get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Test matrix for supported market areas and durations
    test_matrix = {"FR": 15, "NL": 60}
    
    for area, duration in test_matrix.items():
        async with aiohttp.ClientSession() as session:
            service = EnergyCharts.EnergyCharts(
                market_area=area, duration=duration, session=session
            )
            
            # Execute the fetch logic
            await service.fetch()
            
            # Verify aiohttp was triggered
            get_mock.assert_called_once()
            
            # Extract and validate call arguments
            called_url, called_kwargs = get_mock.call_args
            
            # Validate Base URL
            assert called_url[0] == "https://api.energy-charts.info/price"
            
            # Validate Query Parameters
            assert "params" in called_kwargs
            params = called_kwargs["params"]
            assert params["bzn"] == area
            
            # Due to time_machine, date.today() should match exactly
            assert params["start"] == "2026-07-05"
            assert params["end"] == "2026-07-06"
            
            # Validate market data processing
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            
            # Validate specific processing (e.g. average calculation for 60m duration)
            if duration == 60:
                assert len(service.marketdata) == 2
                # (15 min intervals averaged into 1 hour interval)
                expected_avg = (50.5 + 62.1 + 40.8 + 50.6) / 4.0 / 1000.0
                assert service.marketdata[0].market_price_per_kwh == pytest.approx(expected_avg, rel=1e-5)
            else:
                assert len(service.marketdata) == 5
                assert service.marketdata[0].market_price_per_kwh == 50.5 / 1000.0
            
            # Reset mock counter for the next iteration
            get_mock.reset_mock()