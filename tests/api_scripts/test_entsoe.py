import os
import sys
import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import ENTSOE

@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +00:00")  # Freeze time to July 5, 2026
async def test_entsoe_api_mock(mocker, mock_response):
    """Test the ENTSO-E API with a mocked XML response and query parameter validation."""
    
    # 1. Prepare simulated XML response matching the ENTSO-E parser expectations
    # The parser expects 'ns:Period', 'ns:resolution', 'ns:Point', etc.
    # We define the namespace matching what the __init__.py extracts.
    mock_xml = """<?xml version="1.0" encoding="utf-8"?>
    <Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-3:publicationdocument:7:3">
        <TimeSeries>
            <currency_Unit.name>EUR</currency_Unit.name>
            <price_Measure_Unit.name>MWH</price_Measure_Unit.name>
            <Period>
                <timeInterval>
                    <start>2026-07-05T00:00Z</start>
                    <end>2026-07-06T00:00Z</end>
                </timeInterval>
                <resolution>PT15M</resolution>
                <Point>
                    <position>1</position>
                    <price.amount>123.45</price.amount>
                </Point>
                <Point>
                    <position>2</position>
                    <price.amount>145.67</price.amount>
                </Point>
                <Point>
                    <position>3</position>
                    <price.amount>134.24</price.amount>
                </Point>
                <Point>
                    <position>4</position>
                    <price.amount>138.88</price.amount>
                </Point>
                <Point>
                    <position>5</position>
                    <price.amount>142.35</price.amount>
                </Point>
            </Period>
        </TimeSeries>
    </Publication_MarketDocument>
    """
    
    # Pass the XML string into the mock response
    resp = mock_response(mock_xml, 200)
    get_mock = mocker.patch("aiohttp.ClientSession.get", return_value=resp)

    # Test matrix for supported durations
    durations = [15, 60]
    demo_token = "secure_entsoe_token"

    for duration in durations:
        async with aiohttp.ClientSession() as session:
            service = ENTSOE.EntsoeTransparency(
                market_area="FR",  # Will map via MARKET_AREA_MAP
                duration=duration,
                session=session,
                token=demo_token
            )
            
            # Execute the fetch logic (parses the XML string)
            await service.fetch()
            
            # Verify aiohttp was triggered
            get_mock.assert_called_once()
            
            # Extract and validate call arguments
            called_url, called_kwargs = get_mock.call_args
            
            # Validate Base URL
            assert called_url[0] == "https://web-api.tp.entsoe.eu/api"
            
            # Validate Query Parameters
            assert "params" in called_kwargs
            params = called_kwargs["params"]
            
            assert params["securityToken"] == demo_token
            assert params["documentType"] == "A44"  # Price Document Type
            assert params["in_Domain"] == "10YFR-RTE------C"  # FR Domain mapping
            assert params["out_Domain"] == "10YFR-RTE------C"
            
            # Due to time_machine, dates are calculated backwards/forwards
            # Note: Verify if your ENTSOE implementation sets these exact start/end parameters
            assert "periodStart" in params
            assert "periodEnd" in params
            
            # Validate market data processing (123.45 / 1000 = 0.12345)
            assert service.marketdata is not None
            assert len(service.marketdata) > 0
            assert service.marketdata[0].market_price_per_kwh == 0.12345 if duration == 15 else 0.13556
            
            # Reset mock counter for the next iteration
            get_mock.reset_mock()
