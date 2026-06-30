"""SourceShell"""

from datetime import timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.helpers.storage import Store
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt
from .common import Marketprice

from custom_components.epex_spot.const import (
    CONF_DURATION,
    CONF_EARLIEST_START_POST,
    CONF_EARLIEST_START_TIME,
    CONF_LATEST_END_POST,
    CONF_LATEST_END_TIME,
    CONF_MARKET_AREA,
    CONF_SOURCE,
    CONF_SOURCE_AWATTAR,
    CONF_SOURCE_ENERGYFORECAST,
    CONF_SOURCE_ENTSOE,
    CONF_SOURCE_ENERGYCHARTS,
    CONF_SOURCE_SMARD_DE,
    CONF_SOURCE_SMARTENERGY,
    CONF_SOURCE_TIBBER,
    CONF_SOURCE_HOFER_GRUENSTROM,
    CONF_SURCHARGE_ABS,
    CONF_SURCHARGE_PERC,
    CONF_TAX,
    CONF_TOKEN,
    CONF_BACKUP_ENTRY,
    DEFAULT_DURATION,
    DEFAULT_SURCHARGE_ABS,
    DEFAULT_SURCHARGE_PERC,
    DEFAULT_TAX,
    EMPTY_EXTREME_PRICE_INTERVAL_RESP,
)
from custom_components.epex_spot.EPEXSpot import (
    SMARD,
    Awattar,
    Energyforecast,
    Tibber,
    smartENERGY,
    ENTSOE,
    EnergyCharts,
    HoferGruenstrom,
)
from .extreme_price_interval import find_extreme_price_interval, get_start_times

_LOGGER = logging.getLogger(__name__)


class SourceShell:
    def __init__(self, hass, config_entry: ConfigEntry, session: aiohttp.ClientSession):
        self._hass = hass
        self._config_entry = config_entry
        self._marketdata_now = None
        self._sorted_marketdata_today = []
        self._cheapest_sorted_marketdata_today = None
        self._most_expensive_sorted_marketdata_today = None
        self._has_data_today = False
        self._has_data_tomorrow = False
        self._store = Store(self._hass, 1, f"epex_spot.{self._config_entry.entry_id}")

        # create source object
        if config_entry.data[CONF_SOURCE] == CONF_SOURCE_AWATTAR:
            self._source = Awattar.Awattar(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_SMARD_DE:
            self._source = SMARD.SMARD(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_SMARTENERGY:
            self._source = smartENERGY.smartENERGY(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_TIBBER:
            self._source = Tibber.Tibber(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                token=self._config_entry.data[CONF_TOKEN],
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_ENERGYFORECAST:
            self._source = Energyforecast.Energyforecast(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                token=self._config_entry.data[CONF_TOKEN],
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_ENTSOE:
            self._source = ENTSOE.EntsoeTransparency(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                token=self._config_entry.data[CONF_TOKEN],
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_ENERGYCHARTS:
            self._source = EnergyCharts.EnergyCharts(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                session=session,
            )
        elif config_entry.data[CONF_SOURCE] == CONF_SOURCE_HOFER_GRUENSTROM:
            self._source = HoferGruenstrom.HoferGruenstrom(
                market_area=config_entry.data[CONF_MARKET_AREA],
                duration=config_entry.options.get(CONF_DURATION, DEFAULT_DURATION),
                session=session,
            )
        else:
            raise ValueError(f"Unsupported source: {config_entry.data[CONF_SOURCE]}")

    @property
    def unique_id(self):
        return self._config_entry.unique_id

    @property
    def name(self):
        return self._source.name

    @property
    def market_area(self):
        return self._source.market_area

    @property
    def duration(self):
        return self._source.duration

    @property
    def currency(self):
        return self._source.currency

    @property
    def marketdata(self):
        return self._source.marketdata

    @property
    def marketdata_now(self):
        return self._marketdata_now

    @property
    def sorted_marketdata_today(self):
        """Sorted by price."""
        return self._sorted_marketdata_today

    @property
    def has_data_today(self) -> bool:
        return self._has_data_today

    @property
    def has_data_tomorrow(self) -> bool:
        return self._has_data_tomorrow

    @property
    def minimal_daily_points(self):
        return int(23 * 60 / self._source.duration)

    async def fetch(self, *args: Any):
        await self._source.fetch()

    def update_time(self):
        if (len(self.marketdata)) == 0:
            self._marketdata_now = None
            self._sorted_marketdata_today = []
            return

        now = dt.now()

        # find current entry in marketdata list
        try:
            self._marketdata_now = next(
                filter(
                    lambda e: e.start_time <= now and e.end_time > now, self.marketdata
                )
            )
        except StopIteration:
            _LOGGER.error(f"no data found for {self._source}")
            self._marketdata_now = None
            self._sorted_marketdata_today = []

        # get list of entries for today
        current_date = now.date()
        sorted_marketdata_today = filter(
            lambda e: dt.as_local(e.start_time).date() == current_date,
            self.marketdata,
        )
        sorted_sorted_marketdata_today = sorted(
            sorted_marketdata_today, key=lambda e: e.market_price_per_kwh
        )
        self._sorted_marketdata_today = sorted_sorted_marketdata_today
        self._has_data_today = len(sorted_sorted_marketdata_today) >= self.minimal_daily_points

        # get list of entries for tomorrow
        tomorrow_date = current_date + timedelta(days=1)
        marketdata_tomorrow = filter(
            lambda e: dt.as_local(e.start_time).date() == tomorrow_date,
            self.marketdata,
        )
        self._has_data_tomorrow = len(list(marketdata_tomorrow)) >= self.minimal_daily_points

    def to_total_price(self, market_price_per_kwh):
        total_price = market_price_per_kwh

        # Standard calculation for other cases
        if "Tibber API" not in self.name:
            # Retrieve tax and surcharge values from config
            surcharge_abs = self._config_entry.options.get(
                CONF_SURCHARGE_ABS, DEFAULT_SURCHARGE_ABS
            )
            tax = self._config_entry.options.get(CONF_TAX, DEFAULT_TAX)

            surcharge_pct = self._config_entry.options.get(
                CONF_SURCHARGE_PERC, DEFAULT_SURCHARGE_PERC
            )

            total_price = total_price + abs(total_price) * surcharge_pct / 100
            total_price += surcharge_abs
            total_price *= 1 + (tax / 100.0)

        return round(total_price, 6)

    def find_extreme_price_interval(self, call_data, cmp):
        duration: timedelta = call_data[CONF_DURATION]

        start_times = get_start_times(
            marketdata=self.marketdata,
            earliest_start_time=call_data.get(CONF_EARLIEST_START_TIME),
            earliest_start_post=call_data.get(CONF_EARLIEST_START_POST),
            latest_end_time=call_data.get(CONF_LATEST_END_TIME),
            latest_end_post=call_data.get(CONF_LATEST_END_POST),
            latest_market_datetime=self.marketdata[-1].end_time,
            duration=duration,
        )

        result = find_extreme_price_interval(
            self.marketdata, start_times, duration, cmp
        )

        if result is None:
            return EMPTY_EXTREME_PRICE_INTERVAL_RESP

        return {
            "start": result["start"],
            "end": result["start"] + duration,
            "market_price_per_kwh": round(result["market_price_per_hour"], 6),
            "total_price_per_kwh": self.to_total_price(result["market_price_per_hour"]),
        }

    async def async_load_cache(self) -> None:
        """Load marketdata from the isolated .storage file into the active source."""
        try:
            cached_data = await self._store.async_load()
            if cached_data:

                cached_duration = cached_data.get("duration")
                if cached_duration != self.duration:
                    _LOGGER.warning(
                        f"Cache duration mismatch for entry {self._config_entry.entry_id}. "
                        f"Configured: {self.duration}m, Cached: {cached_duration}m. "
                    )
                    return

                if "marketdata" in cached_data:
                    self._source._marketdata = [
                        Marketprice.from_dict(e) for e in cached_data["marketdata"]
                    ]
                    self.update_time()
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(f"Error loading EPEX Spot storage cache: {err}")

    async def async_save_cache(self) -> None:
        """Save current marketdata from the active source to the isolated .storage file."""
        try:
            serializable = [e.to_dict() for e in self._source.marketdata]
            await self._store.async_save({
                    "duration": self.duration,
                    "marketdata": serializable
                })
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.warning(f"Error saving EPEX Spot storage cache: {err}")

    async def async_load_backup_cache(self) -> None:
        """Load marketdata from the backup cache file."""
        backup_id = self._config_entry.options.get(CONF_BACKUP_ENTRY, "none")
        if backup_id != "none":
            _LOGGER.info(f"Attempting to read backup cache from entry {backup_id}")
            try:
                backup_store = Store(self._hass, 1, f"epex_spot.{backup_id}")
                cached_data = await backup_store.async_load()
                if cached_data:

                    cached_duration = cached_data.get("duration")
                    if cached_duration != self.duration:
                        _LOGGER.warning(
                            f"Cache duration mismatch for entry {self._config_entry.entry_id}. "
                            f"Configured: {self.duration}m, Cached: {cached_duration}m. "
                        )
                        return

                    if "marketdata" in cached_data:
                        backup_marketdata = [
                            Marketprice.from_dict(e) for e in cached_data["marketdata"]
                        ]

                        today_points = sum(
                            1 for e in backup_marketdata 
                            if dt.as_local(e.start_time).date() == dt.now().date()
                        )
                        if today_points >= self.minimal_daily_points:
                            self._source._marketdata = backup_marketdata
                            _LOGGER.info(f"Successfully loaded backup data from other entry cache!")
                            return

            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(f"Failed to read backup entry cache: {err}")

        _LOGGER.error(f"No live data and no valid backup data available for {self.name}")
