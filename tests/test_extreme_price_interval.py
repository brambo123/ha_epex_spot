import zoneinfo
from datetime import datetime, time, timedelta

import pytest
import time_machine

from custom_components.epex_spot.common import Marketprice
from custom_components.epex_spot.extreme_price_interval import (
    _calc_start_times,
    calc_interval_average_price,
    calculate_search_window,
    find_extreme_interval,
)

TZ_AMSTERDAM = zoneinfo.ZoneInfo("Europe/Amsterdam")
TZ_UTC = zoneinfo.ZoneInfo("UTC")


@pytest.fixture
def marketdata():
    base_time = datetime(2026, 7, 8, 0, 0, 0, tzinfo=TZ_UTC)
    prices = [
        0.10, 0.09, 0.08, 0.07, 0.06, 0.05,  # 00:00 - 06:00
        0.08, 0.12, 0.15, 0.18, 0.20, 0.22,  # 06:00 - 12:00
        0.24, 0.23, 0.02, 0.01, 0.03, 0.15,  # 12:00 - 18:00 (dip at 14:00 - 16:00: 0.02, 0.01)
        0.18, 0.22, 0.24, 0.20, 0.15, 0.12   # 18:00 - 24:00
    ]
    return [
        Marketprice(
            start_time=base_time + timedelta(hours=i),
            duration=60,
            price=price
        )
        for i, price in enumerate(prices)
    ]

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_calc_interval_average_price_exact_match(marketdata):
    start_time = datetime(2026, 7, 8, 14, 0, 0, tzinfo=TZ_UTC)
    duration = timedelta(hours=1)
    avg_price = calc_interval_average_price(marketdata, start_time, duration)
    assert avg_price == pytest.approx(0.02)

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_calc_interval_average_price_overlapping(marketdata):
    # 13:00 - 14:00 is 0.23, 14:00 - 15:00 is 0.02
    # Average should be (0.23 * 0.5) + (0.02 * 0.5) = 0.125
    start_time = datetime(2026, 7, 8, 13, 30, 0, tzinfo=TZ_UTC)
    duration = timedelta(hours=1)
    avg_price = calc_interval_average_price(marketdata, start_time, duration)
    assert avg_price == pytest.approx(0.125)

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_calc_interval_average_price_incomplete_coverage(marketdata):
    start_time = datetime(2026, 7, 8, 23, 30, 0, tzinfo=TZ_UTC)
    duration = timedelta(hours=1)
    avg_price = calc_interval_average_price(marketdata, start_time, duration)
    assert avg_price is None

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_calculate_search_window():
    latest_market = datetime(2026, 7, 9, 0, 0, 0, tzinfo=TZ_UTC)
    start_time = time(10, 0, 0)
    end_time = time(15, 0, 0)
    earliest_start, latest_end = calculate_search_window(
        earliest_start_time=start_time,
        earliest_start_post=0,
        latest_end_time=end_time,
        latest_end_post=0,
        latest_market_datetime=latest_market
    )
    assert earliest_start.astimezone(TZ_AMSTERDAM).time() == start_time
    assert latest_end.astimezone(TZ_AMSTERDAM).time() == end_time

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_get_start_times_bugfix_and_corners(marketdata):
    duration = timedelta(hours=1)
    earliest_start, latest_end = calculate_search_window(
        earliest_start_time=time(13, 30, 0),
        earliest_start_post=0,
        latest_end_time=time(16, 30, 0),
        latest_end_post=0,
        latest_market_datetime=datetime(2026, 7, 9, 0, 0, 0, tzinfo=TZ_UTC),
    )
    start_times = _calc_start_times(
        marketdata=marketdata,
        earliest_start=earliest_start,
        latest_end=latest_end,
        duration=duration
    )
    
    expected = [
        datetime(2026, 7, 8, 11, 30, 0, tzinfo=TZ_UTC),
        datetime(2026, 7, 8, 12, 0, 0, tzinfo=TZ_UTC),
        datetime(2026, 7, 8, 13, 0, 0, tzinfo=TZ_UTC),
        datetime(2026, 7, 8, 13, 30, 0, tzinfo=TZ_UTC),
    ]
    assert [d.astimezone(TZ_UTC) for d in start_times] == expected

@time_machine.travel("2026-07-08 12:00:00 +0000")
def test_find_extreme_price_interval_lowest(marketdata):
    duration = timedelta(minutes=90)
    earliest_start, latest_end = calculate_search_window(
        earliest_start_time=time(13, 30, 0),
        earliest_start_post=0,
        latest_end_time=time(17, 30, 0),
        latest_end_post=0,
        latest_market_datetime=datetime(2026, 7, 9, 0, 0, 0, tzinfo=TZ_UTC),
    )
    
    result = find_extreme_interval(
        marketdata, earliest_start, latest_end, duration, lambda a, b: a < b
    )
    
    assert result is not None
    assert result["start"].astimezone(TZ_UTC) == datetime(2026, 7, 8, 14, 0, 0, tzinfo=TZ_UTC)
    assert result["end"].astimezone(TZ_UTC) == datetime(2026, 7, 8, 15, 30, 0, tzinfo=TZ_UTC)
    assert result["price"] == pytest.approx(0.016667)
