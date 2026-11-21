"""Lock: serratura porte (stato campo doorLock + comandi blocca/sblocca).

Fonde in un'unica entità nativa ciò che prima erano due cose separate: il sensore
"Serratura" (sola lettura) e i due pulsanti Blocca/Sblocca. Il tap su blocca/sblocca
ATTUA sull'auto (= consenso esplicito dell'utente), come i vecchi pulsanti.
"""
from __future__ import annotations

from homeassistant.components.lock import ENTITY_ID_FORMAT, LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .entity import Omoda9Entity, Omoda9OptimisticMixin, field_on


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([Omoda9Lock(hass.data[DOMAIN][entry.entry_id])])


class Omoda9Lock(Omoda9OptimisticMixin, Omoda9Entity, LockEntity, RestoreEntity):
    """Serratura auto: 0=Bloccata, 1=Sbloccata (campo doorLock).

    Lo stato reale arriva via MQTT solo ad auto sveglia → dopo un comando si mostra
    subito lo stato target (ottimistico, vedi Omoda9OptimisticMixin) e al riavvio di
    HA si ripristina l'ultimo stato noto."""

    _attr_icon = "mdi:car-door-lock"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Serratura", "lock", entity_id_format=ENTITY_ID_FORMAT)
        self._opt_keys = ("doorLock",)   # l'unico campo che dice davvero com'è la serratura
        self._restored: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("locked", "unlocked"):
            self._restored = last.state == "locked"

    def _live_locked(self) -> bool | None:
        # doorLock: 0 = Bloccata, !=0 = Sbloccata → locked = NOT field_on (allineato
        # a binary/switch/cover, "0.0" incluso). field_on None = campo assente.
        on = field_on(self.coordinator.data.get("fields", {}).get("doorLock"))
        return None if on is None else not on

    @property
    def is_locked(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        live = self._live_locked()
        return live if live is not None else self._restored

    async def async_lock(self, **kwargs) -> None:
        await self._run_command("blocca", True)

    async def async_unlock(self, **kwargs) -> None:
        await self._run_command("sblocca", False)
