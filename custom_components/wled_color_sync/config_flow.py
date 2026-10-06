"""Config flow for WLED Media Color Sync."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_BRIGHTNESS_BOOST,
    CONF_FPS,
    CONF_HOST,
    CONF_NAME,
    CONF_NUM_LEDS,
    CONF_PALETTE_SIZE,
    CONF_PORT,
    CONF_PROTOCOL,
    CONF_SATURATION_BOOST,
    CONF_SOURCE_ENTITY,
    CONF_STOP_WHEN_IDLE,
    CONF_TRANSITION,
    DEFAULT_BRIGHTNESS_BOOST,
    DEFAULT_FPS,
    DEFAULT_NUM_LEDS,
    DEFAULT_PALETTE_SIZE,
    DEFAULT_PROTOCOL,
    DEFAULT_SATURATION_BOOST,
    DEFAULT_STOP_WHEN_IDLE,
    DEFAULT_TRANSITION,
    DOMAIN,
)
from .wled_api import async_get_info

PROTOCOL_OPTIONS = [
    selector.SelectOptionDict(value="ddp", label="DDP (port 4048, recommended)"),
    selector.SelectOptionDict(value="drgb", label="DRGB / DNRGB (port 21324)"),
    selector.SelectOptionDict(value="drgbw", label="DRGBW (port 21324, RGBW max 367 LEDs)"),
    selector.SelectOptionDict(value="warls", label="WARLS (port 21324, max 255 LEDs)"),
]

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): selector.TextSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(),
        vol.Optional(CONF_SOURCE_ENTITY): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["media_player", "image", "camera"])
        ),
        vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=PROTOCOL_OPTIONS,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Optional(CONF_PORT, default=0): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=65535, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_NUM_LEDS, default=DEFAULT_NUM_LEDS): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=4096, mode=selector.NumberSelectorMode.BOX)
        ),
    }
)


class WledColorSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WLED Media Color Sync."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().removeprefix("http://").rstrip("/")
            user_input[CONF_HOST] = host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            info = await async_get_info(self.hass, host)
            if info is None and not user_input.get(CONF_NUM_LEDS):
                errors["base"] = "cannot_connect"
            else:
                name = user_input.pop(CONF_NAME, "") or (info or {}).get("name") or host
                user_input[CONF_PORT] = int(user_input.get(CONF_PORT) or 0)
                user_input[CONF_NUM_LEDS] = int(user_input.get(CONF_NUM_LEDS) or 0)
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(STEP_USER_DATA_SCHEMA, user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return WledColorSyncOptionsFlow()


class WledColorSyncOptionsFlow(OptionsFlow):
    """Handle options flow for WLED Media Color Sync."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_PORT] = int(user_input.get(CONF_PORT) or 0)
            user_input[CONF_NUM_LEDS] = int(user_input.get(CONF_NUM_LEDS) or 0)
            user_input[CONF_PALETTE_SIZE] = int(user_input[CONF_PALETTE_SIZE])
            user_input[CONF_FPS] = int(user_input[CONF_FPS])
            user_input.setdefault(CONF_SOURCE_ENTITY, None)
            return self.async_create_entry(title="", data=user_input)

        current_config = {**self.config_entry.data, **self.config_entry.options}
        options_schema = vol.Schema(
            {
                vol.Optional(CONF_SOURCE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=["media_player", "image", "camera"])
                ),
                vol.Required(CONF_PROTOCOL, default=DEFAULT_PROTOCOL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=PROTOCOL_OPTIONS,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_PORT, default=0): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=65535, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Optional(CONF_NUM_LEDS, default=DEFAULT_NUM_LEDS): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=0, max=4096, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_PALETTE_SIZE, default=DEFAULT_PALETTE_SIZE
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=12, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_SATURATION_BOOST, default=DEFAULT_SATURATION_BOOST
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=3.0, step=0.05, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(
                    CONF_BRIGHTNESS_BOOST, default=DEFAULT_BRIGHTNESS_BOOST
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.5, max=3.0, step=0.05, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Required(CONF_FPS, default=DEFAULT_FPS): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=60, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="fps"
                    )
                ),
                vol.Required(CONF_TRANSITION, default=DEFAULT_TRANSITION): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.0, max=10.0, step=0.1, mode=selector.NumberSelectorMode.BOX, unit_of_measurement="s"
                    )
                ),
                vol.Required(
                    CONF_STOP_WHEN_IDLE, default=DEFAULT_STOP_WHEN_IDLE
                ): selector.BooleanSelector(),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(options_schema, current_config),
        )
