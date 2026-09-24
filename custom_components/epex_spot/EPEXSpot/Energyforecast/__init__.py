"""Energyforecast.de"""

import logging
from datetime import datetime

import aiohttp

from ...common import Marketprice

_LOGGER = logging.getLogger(__name__)

class Energyforecast:
    URL = "https://www.energyforecast.de/api/v1/predictions/prices_for_ha"

    MARKET_AREAS = ("AT", "BE", "DE-LU", "DK1", "DK2", "FR", "NL", "PL")
    SUPPORTED_DURATIONS = (15, 60)
    REQUIRES_TOKEN = True

    def __init__(
        self,
        market_area: str,
        duration: int,
        token: str,
        session: aiohttp.ClientSession,
    ):
        self._token = token
        self._session = session
        self._market_area = market_area
        self._marketdata = []
        self._duration = duration
        self._resolution = "HOURLY" if duration == 60 else "QUARTER_HOURLY"

    @property
    def name(self) -> str:
        return "Energyforecast API V1"

    @property
    def market_area(self) -> str:
        return self._market_area

    @property
    def duration(self) -> int:
        return self._duration

    @property
    def currency(self) -> str:
        return "EUR"

    @property
    def marketdata(self):
        return self._marketdata

    async def fetch(self):
        data = await self._fetch_data(self.URL)
        self._marketdata = self._extract_marketdata(data["forecast"]["data"])

    async def _fetch_data(self, url):
        async with self._session.get(
            url,
            params={
                "token": self._token,
                "fixed_cost_cent": 0,
                "vat": 0,
                "resolution": self._resolution,
                "market_zone": self._market_area,
            },
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _extract_marketdata(self, data):
        entries = []
        for entry in data:
            start_time = datetime.fromisoformat(entry["start"])
            end_time = datetime.fromisoformat(entry["end"])
            price = round(float(entry["price"]), 6)
            entries.append(
                Marketprice(
                    start_time=start_time,
                    end_time=end_time,
                    price=price
                )
            )
        return entries
