"""Jeroen.nl API."""

from datetime import datetime, timedelta
import aiohttp
import logging

from homeassistant.util import dt as dt_util
from ...common import Marketprice, average_marketdata

_LOGGER = logging.getLogger(__name__)


class Jeroen:
    URL = "https://jeroen.nl/api/dynamische-energieprijzen/v2/"

    MARKET_AREAS = ("nl",)
    SUPPORTED_DURATIONS = (15, 60)

    def __init__(
        self,
        market_area: str,
        duration: int,
        token: str,
        session: aiohttp.ClientSession,
    ):
        self._session = session
        self._token = token
        self._market_area = market_area
        self._duration = duration
        self._marketdata = []

    @property
    def name(self):
        return f"Jeroen.nl ({'Quarterly' if self._duration == 15 else 'Hourly'})"

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
        """Fetch market price data efficiently from Jeroen.nl."""
        now = datetime.now()
        today_date = now.date()
        tomorrow_date = today_date + timedelta(days=1)

        # Get today
        has_today = any(e.start_time.date() == today_date for e in self._marketdata)
        if not has_today:
            await self._fetch_period("vandaag")

        # Get tomorrow
        has_tomorrow = any(e.start_time.date() == tomorrow_date for e in self._marketdata)
        if not has_tomorrow and now.hour >= 13:
            await self._fetch_period("morgen")

        # Sort and cleanup
        self._marketdata.sort(key=lambda x: x.start_time)
        self._marketdata = [
            e for e in self._marketdata if e.start_time.date() >= today_date
        ]


    async def _fetch_period(self, period: str):
        """Perform the actual API call for a specific period."""
        params = {
            "period": period,
            "type": "json",
            "key": self._token
        }

        raw_quarter_data: list[Marketprice] = []
        try:
            async with self._session.get(self.URL, params=params) as resp:
                resp.raise_for_status()
                data = await resp.json()

                if isinstance(data, list):
                    for entry in data:
                        utc_str = f"{entry['datum_utc']}+00:00"
                        start_time = dt_util.parse_datetime(utc_str)

                        if not start_time:
                            continue

                        price_str = entry["prijs_excl_belastingen"].replace(",", ".")
                        price = float(price_str)
                        
                        raw_quarter_data.append(
                            Marketprice(
                                duration=15,
                                start_time=start_time,
                                price=round(price, 6)
                            )
                        )
        except Exception as e:
            _LOGGER.error(f"Error fetching Jeroen.nl data for period {period}: {e}")

        if not raw_quarter_data:
            return

        if self._duration != 15:
            raw_quarter_data.sort(key=lambda x: x.start_time)
            new_prices = average_marketdata(raw_quarter_data, target_duration=self._duration)
        else:
            new_prices = raw_quarter_data

        existing_starts = {e.start_time for e in self._marketdata}
        for e in new_prices:
            if e.start_time not in existing_starts:
                self._marketdata.append(e)
                existing_starts.add(e.start_time)        
