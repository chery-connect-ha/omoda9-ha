"""Climate: clima avanzato Omoda 9 (preclimatizzazione con temperatura impostabile).

Sostituisce il vecchio interruttore clima a 21° fisso: ora si imposta la temperatura
desiderata (16–30 °C) e l'auto la applica (riscalda o raffredda fino al setpoint).
Usa il comando `airControl` (lo stesso, verificato dal vivo, che faceva partire il
clima fisso), variando `temperature` e la durata `times` (da number.omoda9_clima_durata).

Modello HA: un'unica climate entity con modi OFF / HEAT_COOL (= l'auto porta l'abitacolo
al setpoint scaldando o raffreddando) + un solo cursore di temperatura. Lo stato
acceso/spento arriva dalla telemetria `frontHVACState`; dopo un comando si mostra subito
lo stato target (ottimistico) finché non arriva un nuovo dato dall'auto.

I sedili riscaldati/ventilati e gli sbrinamenti restano interruttori separati (switch.py):
così accendere il clima NON tocca lo stato dei sedili.
"""
from __future__ import annotations

import time

from homeassistant.components.climate import (
    ENTITY_ID_FORMAT,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (CAMPO_CLIMA, CLIMA_MAX_DEFAULT, CLIMA_MIN_DEFAULT, CLIMA_STEP_DEFAULT,
                    DOMAIN, OPT_MAX_S)
from .entity import Omoda9Entity, field_on

# Ripiego OMODA. Il range VERO della vettura, quando il backend lo dichiara in queryList,
# arriva da `coordinator.climate_limits()` (una Jaecoo/PHEV può avere estremi diversi).
MIN_TEMP = CLIMA_MIN_DEFAULT
MAX_TEMP = CLIMA_MAX_DEFAULT
DEFAULT_TEMP = 21.0


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    add([Omoda9Climate(coord)])


class Omoda9Climate(Omoda9Entity, ClimateEntity, RestoreEntity):
    """Clima dell'auto: ON (HEAT_COOL) al setpoint scelto / OFF, via airControl."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT_COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    # Valori di ripiego a livello di classe: le istanze li rimpiazzano con quelli dichiarati
    # dal backend per la vettura (vedi __init__), quando li dichiara.
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = CLIMA_STEP_DEFAULT
    _attr_icon = "mdi:air-conditioner"
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coord) -> None:
        # entity_id FORZATO a climate.omoda9_clima (come le altre entità del componente,
        # altrimenti HA lo deriva "sporco" col nome device: climate.omoda_9_omoda9_clima).
        # unique_id distinto dal vecchio switch (suffix "climate") → entità nuova, non rename.
        super().__init__(coord, "Omoda9 Clima", "climate", entity_id_format=ENTITY_ID_FORMAT)
        lo, hi, step = coord.climate_limits()
        self._attr_min_temp = lo
        self._attr_max_temp = hi
        self._attr_target_temperature_step = step
        self._target = min(hi, max(lo, DEFAULT_TEMP))
        self._opt_on: bool | None = None
        self._opt_anchor = None
        self._opt_at: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            t = last.attributes.get(ATTR_TEMPERATURE)
            try:
                if t is not None:
                    self._target = min(self._attr_max_temp, max(self._attr_min_temp, float(t)))
            except (TypeError, ValueError):
                pass

    # ── stato ──
    def _live_on(self) -> bool | None:
        return field_on(self.coordinator.data.get("fields", {}).get(CAMPO_CLIMA))

    @property
    def target_temperature(self) -> float:
        return self._target

    @property
    def hvac_mode(self) -> HVACMode:
        on = self._opt_on
        if on is None:
            on = self._live_on()
        return HVACMode.HEAT_COOL if on else HVACMode.OFF

    def _handle_coordinator_update(self) -> None:
        # L'ottimismo si annulla quando arriva la verità sul CAMPO del clima, non a un
        # messaggio qualsiasi: le conferme di `airControl` osservate non portano alcun campo
        # di stato, e annullando su quelle la card tornava OFF con il clima acceso — dopodiché
        # l'utente ripremeva, che è come nascono i comandi accavallati. Stessa regola del
        # mixin degli altri attuatori (`entity.Omoda9OptimisticMixin`), riscritta qui perché
        # questa entità non lo eredita; il tetto temporale evita che, se il campo non
        # arrivasse mai, la card resti per sempre su un valore mai confermato.
        if self._opt_on is not None and (
                (self.coordinator.data.get("last_seen") != self._opt_anchor
                 and CAMPO_CLIMA in (self.coordinator.data.get("msg_fields") or {}))
                or (self._opt_at is not None
                    and (time.monotonic() - self._opt_at) > OPT_MAX_S)):
            self._opt_on = None
            self._opt_anchor = None
            self._opt_at = None
        super()._handle_coordinator_update()

    def _set_optimistic(self, on: bool) -> None:
        self._opt_on = on
        self._opt_anchor = self.coordinator.data.get("last_seen")
        self._opt_at = time.monotonic()
        self.async_write_ha_state()

    # ── comandi ──
    def _params(self) -> dict:
        dur = int(getattr(self.coordinator, "clima_duration", 15) or 15)
        return {"temperature": f"{self._target:.1f}", "times": str(dur)}

    async def _send(self, key: str, on: bool) -> None:
        self._set_optimistic(on)
        # `finally` e non solo `except`: la cancellazione del task (`CancelledError`, che
        # deriva da `BaseException`) lasciava la card bloccata sullo stato ottimistico.
        # Stesso rimedio di `entity._run_command` e della coda comandi del coordinator.
        inviato = False
        try:
            await self.coordinator.async_send_command(key, self._params())
            inviato = True
        except Exception as err:  # noqa: BLE001
            raise HomeAssistantError(f"Comando clima non riuscito: {err}") from err
        finally:
            if not inviato:
                self._opt_on = None
                self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send("clima_off", False)
        else:
            await self._send("clima_on", True)

    async def async_turn_on(self) -> None:
        await self._send("clima_on", True)

    async def async_turn_off(self) -> None:
        await self._send("clima_off", False)

    async def async_set_temperature(self, **kwargs) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        self._target = min(self._attr_max_temp, max(self._attr_min_temp, float(temp)))
        # se il clima è già acceso, riapplica subito il nuovo setpoint; altrimenti
        # memorizza soltanto (verrà usato alla prossima accensione).
        if self.hvac_mode != HVACMode.OFF:
            await self._send("clima_on", True)
        else:
            self.async_write_ha_state()
