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
    PROTOCOLS,
)
from .wled_api import async_get_info

SOURCE_SELECTOR = selector.EntitySelector(
    selector.EntitySelectorConfig(domain=["media_player", "image", "camera"])
)
PROTOCOL_SELECTOR = selector.SelectSelector(
    selector.SelectSelectorConfig(
        options=PROTOCOLS,
        translation_key="protocol",
        mode=selector.SelectSelectorMode.DROPDOWN,
    )
)


def _box(min_v: float, max_v: float, step: float, unit: str | None = None) -> selector.NumberSelector:
    return selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=min_v,
            max=max_v,
            step=step,
            mode=selector.NumberSelectorMode.BOX,
            unit_of_measurement=unit,
        )
    )


def _device_schema(defaults: dict[str, Any], include_host: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if include_host:
        fields[vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, ""))] = str
        fields[vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, ""))] = str
    src = defaults.get(CONF_SOURCE_ENTITY)
    fields[
        vol.Optional(CONF_SOURCE_ENTITY, description={"suggested_value": src} if src else None)
    ] = SOURCE_SELECTOR
    fields[vol.Required(CONF_PROTOCOL, default=defaults.get(CONF_PROTOCOL, DEFAULT_PROTOCOL))] = (
        PROTOCOL_SELECTOR
    )
    fields[vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, 0))] = _box(0, 65535, 1)
    fields[vol.Optional(CONF_NUM_LEDS, default=defaults.get(CONF_NUM_LEDS, DEFAULT_NUM_LEDS))] = (
        _box(0, 4096, 1)
    )
    return vol.Schema(fields)


class WledColorSyncConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip().removeprefix("http://").rstrip("/")
            user_input[CONF_HOST] = host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            info = await async_get_info(self.hass, host)
            if info is None and not user_input.get(CONF_NUM_LEDS):
                # Can't auto-detect LED count without the JSON API
                errors["base"] = "cannot_connect"
            else:
                name = user_input.pop(CONF_NAME, "") or (info or {}).get("name") or host
                user_input[CONF_PORT] = int(user_input.get(CONF_PORT) or 0)
                user_input[CONF_NUM_LEDS] = int(user_input.get(CONF_NUM_LEDS) or 0)
                return self.async_create_entry(title=name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_device_schema(user_input or {}, include_host=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WledColorSyncOptionsFlow()


class WledColorSyncOptionsFlow(OptionsFlow):
    """Options: source, protocol, LEDs and color tuning."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            user_input[CONF_PORT] = int(user_input.get(CONF_PORT) or 0)
            user_input[CONF_NUM_LEDS] = int(user_input.get(CONF_NUM_LEDS) or 0)
            user_input[CONF_PALETTE_SIZE] = int(user_input[CONF_PALETTE_SIZE])
            user_input[CONF_FPS] = int(user_input[CONF_FPS])
            # Explicitly clear the source if removed in the form
            user_input.setdefault(CONF_SOURCE_ENTITY, None)
            return self.async_create_entry(data=user_input)

        cur = {**self.config_entry.data, **self.config_entry.options}
        schema = _device_schema(cur, include_host=False).extend(
            {
                vol.Required(
                    CONF_PALETTE_SIZE, default=cur.get(CONF_PALETTE_SIZE, DEFAULT_PALETTE_SIZE)
                ): _box(1, 12, 1),
                vol.Required(
                    CONF_SATURATION_BOOST,
                    default=cur.get(CONF_SATURATION_BOOST, DEFAULT_SATURATION_BOOST),
                ): _box(0.5, 3.0, 0.05),
                vol.Required(
                    CONF_BRIGHTNESS_BOOST,
                    default=cur.get(CONF_BRIGHTNESS_BOOST, DEFAULT_BRIGHTNESS_BOOST),
                ): _box(0.5, 3.0, 0.05),
                vol.Required(CONF_FPS, default=cur.get(CONF_FPS, DEFAULT_FPS)): _box(
                    1, 60, 1, "fps"
                ),
                vol.Required(
                    CONF_TRANSITION, default=cur.get(CONF_TRANSITION, DEFAULT_TRANSITION)
                ): _box(0, 10, 0.1, "s"),
                vol.Required(
                    CONF_STOP_WHEN_IDLE,
                    default=cur.get(CONF_STOP_WHEN_IDLE, DEFAULT_STOP_WHEN_IDLE),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
