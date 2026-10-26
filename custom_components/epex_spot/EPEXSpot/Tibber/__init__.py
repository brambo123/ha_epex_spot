"""Tibber API."""

import logging
from datetime import datetime

import aiohttp

from ...common import Marketprice
from ...const import TIBBER_DEMO_TOKEN, UOM_EUR_PER_KWH

_LOGGER = logging.getLogger(__name__)

TIBBER_QUERY = """
{
  viewer {
    homes {
      currentSubscription {
        priceInfo(resolution: {resolution}) {
          today {
            total
            energy
            tax
            startsAt
            currency
          }
          tomorrow {
            total
            energy
            tax
            startsAt
            currency
          }
        }
      }
    }
  }
}
"""


class Tibber:
    URL = "https://api.tibber.com/v1-beta/gql"

    MARKET_AREAS = ("de", "nl", "no", "se")
    SUPPORTED_DURATIONS = (15, 60)
    REQUIRES_TOKEN = True

    def __init__(
        self,
        market_area: str,
        duration: int,
        token: str,
        session: aiohttp.ClientSession,
    ):
        self._session = session
        self._token = token if token != "demo" else TIBBER_DEMO_TOKEN
        self._market_area = market_area
        self._duration = duration
        self._marketdata = []

    @property
    def name(self):
        return "Tibber API v1-beta"

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
        data = await self._fetch_data(self.URL)
        
        active_home = next(
            (
                home for home in data["data"]["viewer"]["homes"]
                if home.get("currentSubscription") and home["currentSubscription"].get("priceInfo")
            ),
            None
        )

        if not active_home:
            _LOGGER.error("No active Tibber subscription with priceInfo found")
            return

        self._marketdata = self._extract_marketdata(
            active_home["currentSubscription"]["priceInfo"]
        )

    async def _fetch_data(self, url):
        async with self._session.post(
            url,
            json={
                "query": TIBBER_QUERY.replace(
                    "{resolution}",
                    "QUARTER_HOURLY" if self._duration == 15 else "HOURLY",
                )
            },
            headers={"Authorization": f"Bearer {self._token}"},
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    def _extract_marketdata(self, data):
        entries = []

        if "today" in data and data["today"] is not None:
            for entry in data["today"]:
                entries.append(
                    Marketprice(
                        duration=self._duration,
                        start_time=datetime.fromisoformat(entry["startsAt"]),
                        price=round(float(entry["energy"]), 6),
                        unit=UOM_EUR_PER_KWH,
                        attributes={"surcharge": round(float(entry["tax"]), 6)}
                    )
                )

        if "tomorrow" in data and data["tomorrow"] is not None:
            for entry in data["tomorrow"]:
                entries.append(
                    Marketprice(
                        duration=self._duration,
                        start_time=datetime.fromisoformat(entry["startsAt"]),
                        price=round(float(entry["energy"]), 6),
                        unit=UOM_EUR_PER_KWH,
                        attributes={"surcharge": round(float(entry["tax"]), 6)}
                    )
                )

        return entries
