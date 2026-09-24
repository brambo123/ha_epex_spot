from custom_components.epex_spot.const import (
    CONF_SOURCE_AWATTAR,
    CONF_SOURCE_ENERGYCHARTS,
    CONF_SOURCE_ENERGYFORECAST,
    CONF_SOURCE_ENERGYZERO,
    CONF_SOURCE_ENTSOE,
    CONF_SOURCE_HOFER_GRUENSTROM,
    CONF_SOURCE_JEROEN,
    CONF_SOURCE_NORDPOOL,
    CONF_SOURCE_SMARD_DE,
    CONF_SOURCE_SMARTENERGY,
    CONF_SOURCE_TIBBER,
)

from .Awattar import Awattar
from .EnergyCharts import EnergyCharts
from .Energyforecast import Energyforecast
from .EnergyZero import EnergyZero
from .ENTSOE import EntsoeTransparency
from .HoferGruenstrom import HoferGruenstrom
from .Jeroen import Jeroen
from .Nordpool import Nordpool
from .SMARD import SMARD
from .smartENERGY import smartENERGY
from .Tibber import Tibber

API_REGISTRY = {
    CONF_SOURCE_AWATTAR: Awattar,
    CONF_SOURCE_SMARD_DE: SMARD,
    CONF_SOURCE_SMARTENERGY: smartENERGY,
    CONF_SOURCE_TIBBER: Tibber,
    CONF_SOURCE_ENERGYFORECAST: Energyforecast,
    CONF_SOURCE_ENTSOE: EntsoeTransparency,
    CONF_SOURCE_ENERGYCHARTS: EnergyCharts,
    CONF_SOURCE_NORDPOOL: Nordpool,
    CONF_SOURCE_HOFER_GRUENSTROM: HoferGruenstrom,
    CONF_SOURCE_ENERGYZERO: EnergyZero,
    CONF_SOURCE_JEROEN: Jeroen,
}
