"""Text: campo dove inserire il codice OTP ricevuto via email (recupero sessione)."""
from __future__ import annotations

from homeassistant.components.text import ENTITY_ID_FORMAT, TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import Omoda9Entity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([Omoda9OtpCode(hass.data[DOMAIN][entry.entry_id])])


class Omoda9OtpCode(Omoda9Entity, TextEntity):
    # NB: niente `pattern` (come il bridge): uno stato vuoto iniziale NON deve far
    # fallire la validazione TextEntity (romperebbe l'update del coordinator).
    _attr_icon = "mdi:numeric"
    _attr_mode = "text"
    _attr_native_min = 0
    _attr_native_max = 10
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Codice OTP", "otp_code",
                         entity_id_format=ENTITY_ID_FORMAT)

    @property
    def native_value(self) -> str:
        return self.coordinator.otp_code or ""

    async def async_set_value(self, value: str) -> None:
        self.coordinator.otp_code = value.strip()
        self.async_write_ha_state()
