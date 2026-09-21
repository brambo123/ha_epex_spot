"""Hofer Gruenstrom API."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import logging

import aiohttp

from homeassistant.util import dt as dt_util
from ...common import Marketprice, compress_marketdata

_LOGGER = logging.getLogger(__name__)


class HoferGruenstrom:
    URL = "https://www.xn--hofer-grnstrom-nsb.at/service/energy-manager/spot-prices"

    MARKET_AREAS = ("at",)
    SUPPORTED_DURATIONS = (
        15,
        60,
    )
    REQUIRES_TOKEN = False

    def __init__(self, market_area: str, duration: int, session: aiohttp.ClientSession):
        if market_area not in self.MARKET_AREAS:
            raise ValueError(f"Unsupported bidding zone: {market_area}")

        if duration not in self.SUPPORTED_DURATIONS:
            raise ValueError(f"Unsupported duration: {duration}")

        self._session = session
        self._market_area = market_area
        self._duration = duration
        self._marketdata = []

    @property
    def name(self):
        return "Hofer Gruenstrom API"

    @property
    def market_area(self):
        return self._market_area

    @property
    def duration(self):
        return self._duration

    @property
    def currency(self):
        return "EUR"

    @property
    def marketdata(self):
        return self._marketdata

    async def fetch(self):
        # get todays and tomorrows date components
        today = dt_util.now().date()
        tomorrow = today + timedelta(days=1)
        dates = [today, tomorrow]

        # fetch data for today and tomorrow

        marketdata: list[Marketprice] = []
        for date in dates:
            raw_data = await self._fetch_data_for_date(date)
            if raw_data is None:
                continue

            # get the data key from the response
            data = raw_data.get("data")
            if not data:
                _LOGGER.error("No data found in response for %s", date.isoformat())
                continue

            # extract market data
            complete_marketdata = self._extract_marketdata(data)
            if complete_marketdata[0].duration < self.duration:
                complete_marketdata = average_marketdata(
                    complete_marketdata, self.duration
                )

            marketdata += complete_marketdata

        self._marketdata = marketdata

    def _extract_marketdata(self, data):
        entries: list[Marketprice] = []
        last_dt = None
        use_fold = 0
        for entry in data:
            dt = datetime.fromisoformat(entry["from"])
            if last_dt and dt < last_dt:
                use_fold = 1
            last_dt = dt

            start_time = dt.replace(tzinfo=self.TIMEZONE_HOFER_GRUENSTROM, fold=use_fold)
            end_time = datetime.fromisoformat(entry["to"]).replace(tzinfo=self.TIMEZONE_HOFER_GRUENSTROM, fold=use_fold)

            entries.append(
                Marketprice(
                    start_time=start_time,
                    end_time=end_time,
                    price=round(float(entry["price"]) / 100, 6),
                )
            )
        return entries

    async def _fetch_data_for_date(self, date):
        """Fetch data for a specific date."""
        url = f"{self.URL}?year={date.year}&month={date.month}&day={date.day}"
        async with self._session.get(url) as response:
            if response.status != 200:
                if response.status == 204:
                    _LOGGER.debug("No data available for %s yet.", date.isoformat())
                    return None
                _LOGGER.error(
                    "Failed to fetch data from Hofer Gruenstrom API: %s",
                    response.status,
                )
                return None
            return await response.json()
