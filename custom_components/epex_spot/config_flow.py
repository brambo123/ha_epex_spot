"""Config flow for EPEXSpot component.

Used by UI to setup integration.
"""

import logging
import voluptuous as vol
from typing import Dict, List, Tuple

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlowWithReload
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_MARKET_AREA,
    CONF_SOURCE,
    CONF_SOURCE_AWATTAR,
    CONF_SOURCE_ENTSOE,
    CONF_SOURCE_SMARD_DE,
    CONF_SOURCE_SMARTENERGY,
    CONF_SOURCE_TIBBER,
    CONF_SOURCE_ENERGYFORECAST,
    CONF_SOURCE_ENERGYCHARTS,
    CONF_SOURCE_NORDPOOL,
    CONF_SOURCE_HOFER_GRUENSTROM,
    CONF_SOURCE_ENERGYZERO,
    CONF_SOURCE_JEROEN,
    CONF_SURCHARGE_ABS,
    CONF_SURCHARGE_PERC,
    CONF_TEMPLATE_IMPORT,
    CONF_TEMPLATE_EXPORT,
    CONF_TAX,
    CONF_TOKEN,
    CONF_DURATION,
    CONF_BACKUP_ENTRY,
    CONFIG_VERSION,
    DEFAULT_DURATION,
    DEFAULT_SURCHARGE_ABS,
    DEFAULT_SURCHARGE_PERC,
    DEFAULT_TAX,
    DOMAIN,
)
from .EPEXSpot import API_REGISTRY

CONF_SOURCE_LIST = tuple(API_REGISTRY.keys())

_LOGGER = logging.getLogger(__name__)

async def _async_validate_token(
    hass: HomeAssistant, source: str, market_area: str, token: str
) -> bool:
    """Validate the API token by performing a test fetch."""
    session = async_get_clientsession(hass)
    api_class = API_REGISTRY[source]
    duration = api_class.SUPPORTED_DURATIONS[0]
    market_area = api_class.SUPPORTED_DURATIONS[0]
    
    try:
        service = api_class(
            market_area=market_area,
            duration=duration,
            session=session,
            token=token
        )
        await service.fetch()
        return len(service.marketdata) >= 23
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.error("Token validation failed for %s: %s", source, err)
        return False

class EpexSpotConfigFlow(ConfigFlow, domain=DOMAIN):  # type: ignore
    """Component config flow."""

    VERSION = CONFIG_VERSION

    def __init__(self):
        self._source_name = None

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow.

        Called after integration has been selected in the 'add integration
        UI'. The user_input is set to None in this case. We will open a config
        flow form then.
        This function is also called if the form has been submitted. user_input
        contains a dict with the user entered values then.
        """
        if user_input is not None:
            self._source_name = user_input[CONF_SOURCE]
            return await self.async_step_source()
        
        # query top level source
        data_schema = vol.Schema(
            {
                vol.Required(CONF_SOURCE): vol.In(
                    sorted(CONF_SOURCE_LIST, key=lambda s: s.casefold())
                )
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, last_step=False
        )

    async def async_step_source(self, user_input=None):
        errors: Dict[str, str] = {}

        areas, durations, requires_token = getParametersForSource(self._source_name)

        if user_input is not None:
            
            if requires_token:
                # --- TOKEN VALIDATION ---
                is_valid = await _async_validate_token(
                    self.hass, self._source_name, user_input[CONF_MARKET_AREA], user_input[CONF_TOKEN]
                )
                if not is_valid:
                    errors["base"] = "invalid_auth"

            if not errors:
                # create an entry for this configuration
                market_area = user_input[CONF_MARKET_AREA]
                title = f"{self._source_name} ({market_area})"

                unique_id = f"{DOMAIN} {self._source_name} {market_area}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                data = {
                    CONF_SOURCE: self._source_name,
                    CONF_MARKET_AREA: market_area
                }
                if CONF_TOKEN in user_input:
                    data[CONF_TOKEN] = user_input[CONF_TOKEN]

                options = {
                    CONF_DURATION: str(user_input.get(CONF_DURATION, DEFAULT_DURATION))
                }

                return self.async_create_entry(
                    title=title,
                    data=data,
                    options=options,
                )

        duration_options = [
            {"value": str(d), "label": f"{d} min"} for d in durations
        ]

        schema_fields = {
            vol.Required(CONF_MARKET_AREA): vol.In(areas),
            vol.Required(
                CONF_DURATION,
                default=str(DEFAULT_DURATION),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=duration_options,
                    mode=SelectSelectorMode.DROPDOWN
                )
            )
        }

        if requires_token:
            schema_fields[vol.Required(CONF_TOKEN)] = vol.Coerce(str)

        return self.async_show_form(
            step_id="source",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlowWithReload:
        """Create the options flow."""
        return EpexSpotOptionsFlow()


class EpexSpotOptionsFlow(OptionsFlowWithReload):
    """Handle the start of the option flow."""

    def __init__(self) -> None:
        """Initialize options flow."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors: Dict[str, str] = {}

        if user_input is not None:

            if CONF_TOKEN in user_input:
                new_token = user_input.get(CONF_TOKEN)
                old_token = self.config_entry.data.get(CONF_TOKEN, "")

                if new_token != old_token:
                    # --- TOKEN VALIDATION ---
                    source_name = self.config_entry.data.get(CONF_SOURCE)
                    market_area = self.config_entry.data.get(CONF_MARKET_AREA)
                    is_valid = await _async_validate_token(
                        self.hass, source_name, market_area, new_token
                    )
                    if not is_valid:
                        errors["base"] = "invalid_auth"

            if not errors:
                if CONF_TOKEN in user_input:
                    new_token = user_input.pop(CONF_TOKEN)
                    current_data = dict(self.config_entry.data)
                    current_data[CONF_TOKEN] = new_token
                    self.hass.config_entries.async_update_entry(
                        self.config_entry, data=current_data
                    )

                return self.async_create_entry(title="", data=user_input)

        # Get backup entries
        current_entries = self.hass.config_entries.async_entries(DOMAIN)
        backup_options = [{"value": "none", "label": "none"}]
        for entry in current_entries:
            if entry.entry_id != self.config_entry.entry_id:
                backup_options.append({
                    "value": entry.entry_id,
                    "label": entry.title
                })

        # Get source parameters
        _, durations, requires_token = getParametersForSource(
            self.config_entry.data.get(CONF_SOURCE)
        )

        duration_options = [
            {"value": str(d), "label": f"{d} min"} for d in durations
        ]

        schema_fields = {}
        if requires_token:
            current_token = self.config_entry.data.get(CONF_TOKEN, "")
            schema_fields[vol.Required(CONF_TOKEN, default=current_token)] = vol.Coerce(str)

        schema_fields.update({
            vol.Required(
                CONF_DURATION,
                default=str(self.config_entry.options.get(
                    CONF_DURATION, DEFAULT_DURATION
                )),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=duration_options,
                    mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Optional(CONF_BACKUP_ENTRY, default="none"): SelectSelector(
                SelectSelectorConfig(
                    options=backup_options,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="backup_entry_id"
                )
            ),
            vol.Optional(
                CONF_SURCHARGE_PERC,
                default=self.config_entry.options.get(
                    CONF_SURCHARGE_PERC, DEFAULT_SURCHARGE_PERC
                ),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_SURCHARGE_ABS,
                default=self.config_entry.options.get(
                    CONF_SURCHARGE_ABS, DEFAULT_SURCHARGE_ABS
                ),
            ): vol.Coerce(float),
            vol.Optional(
                CONF_TAX,
                default=self.config_entry.options.get(CONF_TAX, DEFAULT_TAX),
            ): vol.Coerce(float),
            vol.Optional(CONF_TEMPLATE_IMPORT): TemplateSelector(),
            vol.Optional(CONF_TEMPLATE_EXPORT): TemplateSelector(),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema_fields), self.config_entry.options
            ),
            errors=errors,
            description_placeholders={
                'docs_templates_url': "https://github.com/brambo123/ha_epex_spot/blob/main/docs/templates.md"
            },
        )


def getParametersForSource(
    source_name: str,
) -> Tuple[List[str], List[int], bool]:
    """
    returns sorted market areas, durations and if given source requires a token
    """
    if source_name not in API_REGISTRY:
        raise ValueError(f"Unknown source: {source_name}")

    api_class = API_REGISTRY[source_name]

    areas = sorted(list(api_class.MARKET_AREAS))
    durations = api_class.SUPPORTED_DURATIONS
    requires_token = getattr(api_class, "REQUIRES_TOKEN", False)

    return areas, durations, requires_token
