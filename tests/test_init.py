"""Test for the ha_epex_spot integration initialization."""
import pytest
from custom_components.epex_spot.const import DOMAIN

@pytest.mark.asyncio
async def test_domain_const():
    """Check if the DOMAIN constant is correctly defined."""
    assert DOMAIN == "epex_spot"
