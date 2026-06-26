"""ELEX API Client for EPEX Spot integration."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import aiohttp

from ...common import Marketprice, average_marketdata

_LOGGER = logging.getLogger(__name__)

class Elex:
    """Client for ELEX Day-Ahead spot prices."""

    URL = "https://api.elex.mk/v1/history/price"

    # The Dictionary Map: "UI Short Code" : "API Expected String"
    # Format: "Short_Code": "Backend_Long_Name"
    MARKET_AREAS = {
        "Albania_AL": "AL",
        "Austria_AT": "AT",
        "Belgium_BE": "BE",
        "Bosnia_BA": "BA",
        "Bulgaria_BG": "BG",
        "Croatia_HR": "HR",
        "Czech_CZ": "CZ",
        "Denmark_DK1": "DK1",
        "Denmark_DK2": "DK2",
        "Estonia_ES": "EE",
        "Finland_FI": "FI",
        "France_FR": "FR",
        "Germany_DE": "DE",
        "Greece_GR": "GR",
        "Hungary_HU": "HU",
        "Ireland_IE": "IE",
        "Italy_IT": "IT",
        "Italy_NORTH": "IT-North",
        "Italy_CNORTH": "IT-CNorth",
        "Italy_CSOUTH": "IT-CSouth",
        "Italy_SOUTH": "IT-South",
        "Italy_SICILY": "IT-Sicily",
        "Italy_SARDINIA": "IT-Sardinia",
        "Italy_CALABRIA": "IT-Calabria",
        "Kosovo_XK": "XK",
        "Latvia_LV": "LV",
        "Lithuania_LT": "LT",
        "Macedonia_MK": "MK",
        "Montenegro_ME": "ME",
        "Netherlands_NL": "NL",
        "Norway_NO1": "NO1",
        "Norway_NO2": "NO2",
        "Norway_NO3": "NO3",
        "Norway_NO4": "NO4",
        "Norway_NO5": "NO5",
        "Poland_PL": "PL",
        "Portugal_PT": "PT",
        "Romania_RO": "RO",
        "Serbia_RS": "RS",
        "Slovakia_SK": "SK",
        "Slovenia_SI": "SI",
        "Spain_ES": "ES",
        "Sweden_SE1": "SE1",
        "Sweden_SE2": "SE2",
        "Sweden_SE3": "SE3",
        "Sweden_SE4": "SE4",
        "Switzerland_CH": "CH",
        "United_Kingdom_UK": "UK",
        "Ukraine_UA": "UA"
    }                               

    SUPPORTED_DURATIONS = (15, 60)

    def __init__(self, market_area: str, api_key: str, duration: int, session: aiohttp.ClientSession):
        self._session = session
        self._market_area = market_area
        self._api_key = api_key
        self._duration = duration
        self._marketdata = []

    @property
    def name(self) -> str:
        return "ELEX Market Data"

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
        """Fetch the day-ahead prices from ELEX API."""
        
        # Ensure we use Central European Time to request the correct "today"
        tz_cet = ZoneInfo("CET")
        today_str = datetime.now(tz_cet).strftime("%Y-%m-%d")

        # Map the UI short code back to your backend string
        # api_country_string = self.MARKET_AREAS.get(self._market_area, self._market_area)

        params = {
            "country": self._market_area,
            "start_date": today_str,
            "days": 1
        }
        
        headers = {
            "x-api-key": self._api_key
        }

        _LOGGER.debug(f"Fetching ELEX history data for {self._market_area} starting {today_str}")
        

        try:
            async with self._session.get(self.URL, params=params, headers=headers) as resp:
                data = await resp.json()

                # Catch custom API errors (like the Free Tier lock) gracefully
                if resp.status != 200 or data.get("error"):
                    error_msg = data.get("message", f"HTTP {resp.status}")
                    _LOGGER.error(f"ELEX API Error: {error_msg}")
                    raise Exception(f"ELEX Access Denied: {error_msg}")

                marketdata = self._extract_marketdata(data, tz_cet)
                if self._duration > 15:
                    marketdata = average_marketdata(marketdata, self._duration)
                self._marketdata = marketdata

        except aiohttp.ClientError as err:
            _LOGGER.error(f"Network error communicating with ELEX: {err}")
            raise Exception(f"Network error: {err}")

    def _extract_marketdata(self, json_data, tz_cet):
        """Extract prices from JSON, calculate timestamps, convert to €/kWh."""
        entries = []
        results = json_data.get("result", [])

        for daily_data in results:
            base_date_str = daily_data.get("date")
            if not base_date_str:
                continue

            hourly_prices = daily_data.get("hours", [])
            data_points_count = len(hourly_prices)
            
            if data_points_count == 0:
                continue

            # Dynamically calculate if this is a 60-min or 15-min market
            duration_minutes = 60 if data_points_count <= 25 else 15

            # Get base time
            start_dt = datetime.strptime(base_date_str, "%Y-%m-%d")
            start_dt = start_dt.replace(tzinfo=tz_cet)

            for price_mwh in hourly_prices:
                # Convert ELEX €/MWh to HA expected €/kWh
                price_kwh = float(price_mwh) / 1000.0

                entries.append(
                    Marketprice(
                        duration=duration_minutes,
                        start_time=start_dt,
                        price=round(price_kwh, 6)
                    )
                )
                
                start_dt += timedelta(minutes=duration_minutes)

        return entries
