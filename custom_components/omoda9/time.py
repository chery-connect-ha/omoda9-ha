"""Time: orari di configurazione locali (non comandi diretti all'auto).

Come i number di configurazione, queste entità NON inviano nulla all'auto da sole:
memorizzano una preferenza usata dagli altri controlli al momento dell'invio.
  - Ricarica programmata · orario di inizio: l'ora (HH:MM) da cui far partire la
    ricarica. Lo switch "Ricarica programmata" compone il piano `chargeAppointControl`
    usando questo valore.

Perché un'entità `time` e non un number 0–23: l'auto accetta l'orario in MINUTI dalla
mezzanotte → con un selettore orario si può scegliere anche i minuti, non solo l'ora intera.
Il riferimento è la mezzanotte LOCALE: misurato il 2026-08-10 rileggendo nell'app il piano
scritto da qui con `startTime = 0` (mostra 00:00; se il filo fosse UTC mostrerebbe 02:00).

È RestoreEntity → al riavvio di HA ripristina l'ultimo orario impostato e lo riscrive
sul coordinator (da cui lo switch lo legge come `charge_start_minutes`).
"""
from __future__ import annotations

from datetime import time

from homeassistant.components.time import ENTITY_ID_FORMAT, TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import Omoda9Entity

# (nome, suffix, attributo-minuti sul coordinator, default HH, default MM, icona)
TIMES = [
    ("Omoda9 Ricarica · orario di inizio", "ricarica_orario_inizio",
     "charge_start_minutes", 8, 0, "mdi:clock-start"),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    add([Omoda9ConfigTime(coord, *spec) for spec in TIMES])


class Omoda9ConfigTime(Omoda9Entity, TimeEntity, RestoreEntity):
    """Selettore orario di configurazione locale: pubblica i minuti-da-mezzanotte sul coordinator."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coord, name, suffix, attr, def_h, def_m, icon) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._attr = attr
        self._attr_icon = icon
        self._value = time(hour=def_h, minute=def_m)
        setattr(coord, attr, def_h * 60 + def_m)   # default subito disponibile allo switch

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state not in (None, "", "unknown", "unavailable"):
            try:
                hh, mm, *_ = (int(p) for p in last.state.split(":"))
                self._value = time(hour=hh, minute=mm)
            except (ValueError, TypeError):
                pass
        self._push()

    def _push(self) -> None:
        setattr(self.coordinator, self._attr, self._value.hour * 60 + self._value.minute)

    @property
    def native_value(self) -> time:
        return self._value

    async def async_set_value(self, value: time) -> None:
        # i secondi non servono (l'auto ragiona in minuti) → li azzeriamo
        self._value = value.replace(second=0, microsecond=0)
        self._push()
        self.async_write_ha_state()
