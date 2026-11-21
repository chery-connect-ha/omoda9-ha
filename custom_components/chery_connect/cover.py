"""Cover: baule, finestrini, tetto (stato campi 5A02 + comandi apri/chiudi).

Fonde gli stati di sola lettura (baule trunkDoor, finestrini, tetto sunroofState) con i
relativi pulsanti apri/chiudi in entità "tapparella" native, con stato + azione in
un'unica card. NB: i 4 finestrini restano anche come binary_sensor singoli (dettaglio
"quale finestrino"); il cover "Finestrini" è il comando aggregato. La ventilazione
finestrini resta un pulsante a sé (non mappabile su apri/chiudi). Ogni apri/chiudi
ATTUA sull'auto (= consenso esplicito dell'utente).
"""
from __future__ import annotations

from homeassistant.components.cover import (
    ENTITY_ID_FORMAT,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import Omoda9Entity, Omoda9OptimisticMixin, field_on


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    add([
        Omoda9Cover(coord, "Omoda9 Baule", "baule", ["trunkDoor"],
                    "baule_apri", "baule_chiudi", CoverDeviceClass.DOOR, "mdi:car-back"),
        Omoda9Cover(coord, "Omoda9 Finestrini", "finestrini",
                    ["frontLeftWindowState", "frontRightWindowState",
                     "backLeftWindowState", "backRightWindowState"],
                    "finestrini_apri", "finestrini_chiudi", CoverDeviceClass.WINDOW, "mdi:car-door"),
        Omoda9Cover(coord, "Omoda9 Tetto", "tetto", ["sunroofState"],
                    "tetto_apri", "tetto_chiudi", CoverDeviceClass.SHADE, "mdi:car-select"),
    ])


class Omoda9Cover(Omoda9OptimisticMixin, Omoda9Entity, CoverEntity, RestoreEntity):
    """Apertura motorizzata: APERTA se almeno uno dei campi associati è != 0.

    Lo stato reale arriva via MQTT solo ad auto sveglia → dopo un comando si mostra
    subito lo stato target (ottimistico) e al riavvio di HA si ripristina l'ultimo noto."""

    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, coord, name, suffix, keys, open_cmd, close_cmd, dclass, icon) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._keys = keys
        self._opt_keys = tuple(keys)   # chiudono l'ottimismo solo i campi di QUESTA cover
        self._open_cmd = open_cmd
        self._close_cmd = close_cmd
        self._attr_device_class = dclass
        self._attr_icon = icon
        self._restored: bool | None = None  # True = chiuso

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("open", "closed"):
            self._restored = last.state == "closed"

    def _live_closed(self) -> bool | None:
        fields = self.coordinator.data.get("fields", {})
        # field_on per ogni campo: None=assente, True=aperto. Allinea "0.0" col resto.
        states = [field_on(fields.get(k)) for k in self._keys]
        if all(s is None for s in states):
            return None  # nessun campo noto → emerge restored/unknown
        return not any(states)  # almeno uno aperto → cover aperta

    @property
    def is_closed(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value  # True = chiuso
        live = self._live_closed()
        return live if live is not None else self._restored

    async def async_open_cover(self, **kwargs) -> None:
        await self._run_command(self._open_cmd, False)  # non chiuso = aperto

    async def async_close_cover(self, **kwargs) -> None:
        await self._run_command(self._close_cmd, True)
