"""Tests for the hourly fetch and fallback decision in EpexSpotDataUpdateCoordinator."""
from datetime import datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import time_machine
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.epex_spot import EpexSpotDataUpdateCoordinator
from custom_components.epex_spot.common import Marketprice
from custom_components.epex_spot.const import (
    CONF_DURATION,
    CONF_MARKET_AREA,
    CONF_SOURCE,
    CONF_SOURCE_ENERGYCHARTS,
    DOMAIN,
)
from custom_components.epex_spot.SourceShell import SourceShell


def _hourly_prices(day_offsets):
    """Build 24 hourly entries per local day (0 = today, 1 = tomorrow)."""
    today = dt_util.now().date()
    entries = []
    for offset in day_offsets:
        start = datetime.combine(
            today + timedelta(days=offset), time(0), tzinfo=dt_util.DEFAULT_TIME_ZONE
        )
        entries += [Marketprice(start + timedelta(hours=h), 0.1, duration=60) for h in range(24)]
    return entries


def _prepare(mocker, tmp_path, cached, fetched):
    """Coordinator whose source holds `cached` days since the last full-hour refresh.

    The API mock returns `fetched` days, or raises when `fetched` is None.
    Returns (coordinator, source, fetch_mock, backup_mock).
    """
    hass = MagicMock()
    hass.config.config_dir = str(tmp_path)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_SOURCE: CONF_SOURCE_ENERGYCHARTS, CONF_MARKET_AREA: "NL"},
        options={CONF_DURATION: 60},
    )
    source = SourceShell(hass, entry, MagicMock())
    source._source._marketdata = _hourly_prices(cached)
    source.update_time()  # flags as calculated at the last full hour

    async def fake_fetch():
        if fetched is None:
            raise aiohttp.ClientError("API down")
        source._source._marketdata = _hourly_prices(fetched)

    fetch_mock = mocker.patch.object(source._source, "fetch", side_effect=fake_fetch)
    mocker.patch.object(source, "async_save_cache", AsyncMock())
    backup_mock = mocker.patch.object(source, "async_load_backup_cache", AsyncMock())
    mocker.patch("custom_components.epex_spot.asyncio.sleep", AsyncMock())
    # The coordinator reports its missing config entry via the frame helper,
    # which only exists on a running Home Assistant instance.
    mocker.patch("homeassistant.helpers.frame.report_usage")

    coordinator = EpexSpotDataUpdateCoordinator(hass, source=source)
    return coordinator, source, fetch_mock, backup_mock


@pytest.mark.asyncio
@time_machine.travel("2026-11-03 22:54:00 +0100")
async def test_fetch_source_keeps_fresh_tomorrow_data(mocker, tmp_path):
    """Tomorrow's prices arriving after 16:00 must not be replaced by the backup."""
    coordinator, source, fetch_mock, backup_mock = _prepare(
        mocker, tmp_path, cached=[0], fetched=[0, 1]
    )

    await coordinator.fetch_source()

    fetch_mock.assert_called_once()
    backup_mock.assert_not_called()
    assert source.has_data_today
    assert source.has_data_tomorrow
    assert len(source.marketdata) == 48


@pytest.mark.asyncio
@time_machine.travel("2026-11-03 22:54:00 +0100")
async def test_fetch_source_loads_backup_without_tomorrow_after_16(mocker, tmp_path):
    """No tomorrow data from the API after 16:00 still triggers the backup."""
    coordinator, source, fetch_mock, backup_mock = _prepare(
        mocker, tmp_path, cached=[0], fetched=[0]
    )

    await coordinator.fetch_source()

    fetch_mock.assert_called_once()
    backup_mock.assert_called_once()
    assert source.has_data_today
    assert not source.has_data_tomorrow


@pytest.mark.asyncio
@time_machine.travel("2026-11-03 22:54:00 +0100")
async def test_fetch_source_loads_backup_when_api_fails(mocker, tmp_path):
    """A failing API without any data for today triggers the backup."""
    coordinator, source, fetch_mock, backup_mock = _prepare(
        mocker, tmp_path, cached=[], fetched=None
    )

    await coordinator.fetch_source()

    fetch_mock.assert_called_once()
    backup_mock.assert_called_once()
    assert coordinator._error_count == 1
    assert not source.has_data_today


@pytest.mark.asyncio
@time_machine.travel("2026-11-03 22:54:00 +0100")
async def test_fetch_source_skips_when_data_complete(mocker, tmp_path):
    """With today's and tomorrow's data present, nothing is fetched."""
    coordinator, _source, fetch_mock, backup_mock = _prepare(
        mocker, tmp_path, cached=[0, 1], fetched=[0, 1]
    )

    await coordinator.fetch_source()

    fetch_mock.assert_not_called()
    backup_mock.assert_not_called()
