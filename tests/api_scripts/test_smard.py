import os
import sys

import aiohttp
import pytest
import time_machine

# Dynamic path fix
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from custom_components.epex_spot.const import CONF_SOURCE_SMARD_DE
from custom_components.epex_spot.EPEXSpot import API_REGISTRY


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +2000")
async def test_smard_api_single_request_needed(mocker, mock_response):
    """Scenario 1: Index contains an old timestamp. Only 1 data request is needed."""
    
    # The latest timestamp in index is from days ago (e.g., July 4st)
    mock_index_data = {"timestamps": [1781906400000, 1782511200000, 1783116000000]}  
    
    mock_actual_data = {
        "series": [
            [1783252800000, 45.50],  # July 5, 2026 12:00:00 UTC
            [1783256400000, 52.10]   # July 5, 2026 13:00:00 UTC
        ]
    }
    
    resp_index = mock_response(mock_index_data, 200)
    resp_data = mock_response(mock_actual_data, 200)
    
    get_mock = mocker.patch("aiohttp.ClientSession.get", side_effect=[resp_index, resp_data])

    async with aiohttp.ClientSession() as session:
        api_class = API_REGISTRY[CONF_SOURCE_SMARD_DE]
        service = api_class(market_area="DE-LU", duration=60, session=session)
        await service.fetch()
        
        # If your optimized logic is applied, this should only be 2 calls in total:
        # 1 for index, 1 for data. (Instead of fetching 2 data files blindly)
        assert get_mock.call_count == 2
        
        # Check that it fetched the correct data file
        call_data_args, _ = get_mock.call_args_list[1]
        assert "1783116000000.json" in call_data_args[0]


@pytest.mark.asyncio
@time_machine.travel("2026-07-05 12:00:00 +0000")
async def test_smard_api_two_requests_needed(mocker, mock_response):
    """Scenario 2: A new data-series started tomorrow. 2 data requests are required."""
    
    # Index has an older file AND a brand new file that started tomorrow (July 6th)
    mock_index_data = {"timestamps": [1782079200000, 1782684000000, 1783288800000]}  
    
    mock_data_old = {"series": [[1783209600000, 40.00]]}
    mock_data_new = {"series": [[1783252800000, 45.50]]}
    
    resp_index = mock_response(mock_index_data, 200)
    resp_old = mock_response(mock_data_old, 200)
    resp_new = mock_response(mock_data_new, 200)
    
    get_mock = mocker.patch("aiohttp.ClientSession.get", side_effect=[resp_index, resp_old, resp_new])

    async with aiohttp.ClientSession() as session:
        api_class = API_REGISTRY[CONF_SOURCE_SMARD_DE]
        service = api_class(market_area="NL", duration=15, session=session)
        await service.fetch()
        
        # Here it should call the index + 2 data files = 3 calls
        assert get_mock.call_count == 3
        
        # Verify both files were requested
        assert "1782684000000.json" in get_mock.call_args_list[1][0][0]
        assert "1783288800000.json" in get_mock.call_args_list[2][0][0]
