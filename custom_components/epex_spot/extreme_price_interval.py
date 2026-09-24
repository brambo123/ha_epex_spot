import logging
from datetime import datetime, time, timedelta

import homeassistant.util.dt as dt_util

_LOGGER = logging.getLogger(__name__)


def calc_interval_average_price(marketdata, start_time: datetime, duration: timedelta):
    """Calculate the average price for a given start time and duration."""
    end_time = start_time + duration
    total_seconds = duration.total_seconds()

    overlaps = [
        (mp.market_price_per_kwh, (min(end_time, mp.end_time) - max(start_time, mp.start_time)).total_seconds())
        for mp in marketdata
        if mp.end_time > start_time and mp.start_time < end_time
    ]

    # Verify that the sum of overlap durations covers the total duration
    if sum(w for _, w in overlaps) < total_seconds - 0.1:
        return None

    return sum(p * w for p, w in overlaps) / total_seconds


def _calc_start_times(
    marketdata, earliest_start: datetime, latest_end: datetime, duration: timedelta
):
    """Calculate list of meaningful start times."""
    start_times = set()

    if earliest_start + duration <= latest_end:
        start_times.add(earliest_start)

    if latest_end - duration >= earliest_start:
        start_times.add(latest_end - duration)

    for md in marketdata:
        # segment start
        t_start = md.start_time
        if t_start >= earliest_start and t_start + duration <= latest_end:
            start_times.add(t_start)

        # segment end minus duration
        t_end_minus = md.end_time - duration
        if t_end_minus >= earliest_start and md.end_time <= latest_end:
            start_times.add(t_end_minus)

    return sorted(start_times)


def find_extreme_interval(marketdata, earliest_start: datetime, latest_end: datetime, duration: timedelta, cmp):
    """Find the interval within earliest_start and latest_end that has the extreme average price."""
    start_times = _calc_start_times(marketdata, earliest_start, latest_end, duration)

    best_price: float | None = None
    best_start_time: datetime | None = None

    for start_time in start_times:
        price = calc_interval_average_price(marketdata, start_time, duration)

        if price is None:
            continue

        if best_price is None or cmp(price, best_price):
            best_price = price
            best_start_time = start_time

    if best_start_time is None:
        return None

    return {
        "start": dt_util.as_local(best_start_time),
        "end": dt_util.as_local(best_start_time + duration),
        "price": round(best_price, 6),
    }


def calculate_search_window(
    earliest_start_time: time | None,
    earliest_start_post: int | None,
    latest_end_time: time | None,
    latest_end_post: int | None,
    latest_market_datetime: datetime,
):
    """Calculate the search window start and end datetime."""
    now = dt_util.now()

    earliest_start: datetime = (
        now
        if earliest_start_time is None
        else now.replace(
            hour=earliest_start_time.hour,
            minute=earliest_start_time.minute,
            second=earliest_start_time.second,
            microsecond=earliest_start_time.microsecond,
        )
    )
    if earliest_start_post is not None:
        earliest_start += timedelta(days=earliest_start_post)

    if latest_end_time is None:
        latest_end = latest_market_datetime
    else:
        latest_end: datetime = now.replace(
            hour=latest_end_time.hour,
            minute=latest_end_time.minute,
            second=latest_end_time.second,
            microsecond=latest_end_time.microsecond,
        )

        if latest_end_post is not None:
            latest_end += timedelta(days=latest_end_post)
        elif latest_end <= earliest_start:
            latest_end += timedelta(days=1)

        if latest_end > latest_market_datetime:
            if latest_market_datetime <= earliest_start:
                return None, None

            latest_end = latest_market_datetime

    if latest_end <= earliest_start:
        raise ValueError(
            f"latest_end {latest_end} is earlier or equal to earliest_start {earliest_start}"
        )

    return dt_util.as_utc(earliest_start), dt_util.as_utc(latest_end)
