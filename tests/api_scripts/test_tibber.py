import os
import sys
import aiohttp
import pytest
import time_machine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.EPEXSpot import Tibber


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_tibber_api_mock(mocker, mock_response):
    """Test the Tibber GraphQL API with POST requests and resolution configurations."""
    
    durations = [15, 60]

    for duration in durations:
        mock_data = {
            "data": {
                "viewer": {
                    "homes": [
                        {
                            "currentSubscription": {
                                "priceInfo": {
                                    "today": [
                                        {
                                            "startsAt": "2026-07-05T12:00:00+02:00",
                                            "energy": 0.254,
                                            "tax": 0.0251,
                                            "total": 0.2791
                                        }
                                    ],
                                    "tomorrow": [
                                        {
                                            "startsAt": "2026-07-06T12:00:00+02:00",
                                            "energy": 0.281,
                                            "tax": 0.0251,
                                            "total": 0.3061
                                        }
                                    ]
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        resp = mock_response(mock_data, 200)
        # Note: Tibber uses POST instead of GET
        post_mock = mocker.patch("aiohttp.ClientSession.post", return_value=resp)

        async with aiohttp.ClientSession() as session:
            service = Tibber.Tibber(
                market_area="de",
                token="test_token",
                duration=duration,
                session=session
            )
            
            await service.fetch()
            
            post_mock.assert_called_once()
            called_url, called_kwargs = post_mock.call_args
            
            assert called_url[0] == "https://api.tibber.com/v1-beta/gql"
            assert called_kwargs["headers"]["Authorization"] == "Bearer test_token"
            
            # Validate GraphQL query parameters payload
            expected_res = "QUARTER_HOURLY" if duration == 15 else "HOURLY"
            assert expected_res in called_kwargs["json"]["query"]
            
            assert len(service.marketdata) == 2
            assert service.marketdata[0].market_price_per_kwh == 0.254
            assert service.marketdata[1].market_price_per_kwh == 0.281
            
            post_mock.reset_mock()
