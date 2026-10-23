"""Rear window heating: a reported "on" expires, because the car never reports the "off".

`rWinHeatingState` only arrives inside the confirmation of a command that touches the rear
window (`1135`, or the `110B` "Heat everything" preset): the spontaneous `5A02` telemetry
never carries it. When the car's own 15-minute timer switches the heater off nobody tells us,
and the switch used to stay on until the next rear-window command — 48.6 hours in Home
Assistant, on 21-23/10/2026, after a "Heat everything" whose other heaters the car had
reported off within a quarter of an hour.

The other comfort switches must NOT get the same treatment: their fields are in the
telemetry, which reports them going off, and an expiry there would turn off a seat heater
that is really on.
"""
from __future__ import annotations

import time
from datetime import timedelta

import fixtures as FX
import pytest

from homeassistant.core import State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    mock_restore_cache,
)

from custom_components.omoda9 import coordinator as coord_mod
from custom_components.omoda9 import switch as switch_mod
from custom_components.omoda9.const import DOMAIN, REAR_DEFROST_MAX_S

REAR = "switch.chery_connect_rear_window_heating"
WINDSHIELD = "switch.chery_connect_windshield_defrost"


class _Msg:
    def __init__(self, payload: dict) -> None:
        import json
        self.payload = json.dumps(payload).encode()
        self.topic = "app/1/test/account/msgCenter/msg"


async def _deliver(hass, entry, envelope: dict) -> None:
    hass.data[DOMAIN][entry.entry_id]._on_car_message(None, None, _Msg(envelope))
    await hass.async_block_till_done()


def _rear_ack(value: str) -> dict:
    """Confirmation of the rear defrost command, as the car sends it (synthetic seq)."""
    return FX.envelope("1135", {"resultTime": "1721390001000", "hasAsy": "0",
                                "rWinHeatingState": value, "result": "1", "seq": "X-1"})


def _telemetry_without_rear(**overrides) -> dict:
    """A spontaneous 5A02 the way the car really sends it: no `rWinHeatingState`."""
    env = FX.telemetry_5a02(**overrides)
    env["content"]["data"].pop("rWinHeatingState", None)
    return env


class _Clock:
    """Moves the clock the integration reads (coordinator stamps, switch ages), leaving the
    rest of the process — Home Assistant itself, the event loop — alone."""

    def __init__(self) -> None:
        self.offset = 0.0

    def time(self) -> float:
        return time.time() + self.offset

    def monotonic(self) -> float:
        return time.monotonic() + self.offset


@pytest.fixture
def clock(monkeypatch):
    c = _Clock()
    monkeypatch.setattr(switch_mod, "time", c)
    monkeypatch.setattr(coord_mod, "time", c)
    return c


async def _advance(hass, clock: _Clock, seconds: float) -> None:
    clock.offset += seconds
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=clock.offset))
    await hass.async_block_till_done()


async def test_rear_heating_goes_off_by_itself(hass, integrazione_avviata, clock):
    """The field incident: on from a confirmation, then hours of telemetry without it."""
    await _deliver(hass, integrazione_avviata, _rear_ack("1"))
    assert hass.states.get(REAR).state == "on"

    await _advance(hass, clock, REAR_DEFROST_MAX_S - 30)
    assert hass.states.get(REAR).state == "on", "still within the car's own timer"

    # the timer alone has to flip it: the car is asleep and sends nothing
    await _advance(hass, clock, 60)
    assert hass.states.get(REAR).state == "off", (
        "past the car's 15-minute timer the heater is off, whatever the last ack said")

    # and telemetry that does not mention the rear window must not bring it back
    await _deliver(hass, integrazione_avviata, _telemetry_without_rear())
    assert hass.states.get(REAR).state == "off"


async def test_heat_everything_confirmation_expires_too(hass, integrazione_avviata, clock):
    """The 21/10/2026 case came from the preset confirmation, not from the rear command."""
    await _deliver(hass, integrazione_avviata, FX.envelope("110B", {
        "result": "1", "seq": "X-2", "frontHVACState": "1", "rWinHeatingState": "1"}))
    assert hass.states.get(REAR).state == "on"

    await _advance(hass, clock, 48 * 3600)
    assert hass.states.get(REAR).state == "off"


async def test_a_newer_confirmation_restarts_the_count(hass, integrazione_avviata, clock):
    await _deliver(hass, integrazione_avviata, _rear_ack("1"))
    await _advance(hass, clock, 10 * 60)
    await _deliver(hass, integrazione_avviata, _rear_ack("1"))      # switched on again

    await _advance(hass, clock, 10 * 60)
    assert hass.states.get(REAR).state == "on", (
        "20 minutes after the first ack but only 10 after the second: still on")

    await _advance(hass, clock, REAR_DEFROST_MAX_S)
    assert hass.states.get(REAR).state == "off"


async def test_an_off_confirmation_still_reads_off(hass, integrazione_avviata, clock):
    await _deliver(hass, integrazione_avviata, _rear_ack("1"))
    await _deliver(hass, integrazione_avviata, _rear_ack("0"))
    assert hass.states.get(REAR).state == "off"


async def test_other_comfort_switches_do_not_expire(hass, integrazione_avviata, clock):
    """Their fields come back in the telemetry: the last value holds, however old."""
    await _deliver(hass, integrazione_avviata, _telemetry_without_rear(frontWindshieldHeat="1"))
    assert hass.states.get(WINDSHIELD).state == "on"

    await _advance(hass, clock, 2 * 3600)
    await _deliver(hass, integrazione_avviata, FX.position_1301())
    assert hass.states.get(WINDSHIELD).state == "on"


async def test_restart_keeps_the_age(hass, config_entry, cloud, monkeypatch):
    """Restored "on" has to expire as well, or a restart re-creates the stuck switch."""
    from test_macro_comfort import _avvia

    expired = dt_util.utcnow() - timedelta(seconds=REAR_DEFROST_MAX_S + 60)
    mock_restore_cache(hass, (State(REAR, "on", last_changed=expired, last_updated=expired),))

    await _avvia(hass, config_entry, monkeypatch)

    assert hass.states.get(REAR).state == "off", (
        "the heater was switched on long before the restart: the car has closed it")

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_restart_in_the_middle_resumes_with_the_remaining_time(hass, config_entry,
                                                                     cloud, monkeypatch):
    from test_macro_comfort import _avvia

    clock = _Clock()
    monkeypatch.setattr(switch_mod, "time", clock)
    monkeypatch.setattr(coord_mod, "time", clock)
    recent = dt_util.utcnow() - timedelta(seconds=60)
    mock_restore_cache(hass, (State(REAR, "on", last_changed=recent, last_updated=recent),))

    await _avvia(hass, config_entry, monkeypatch)
    assert hass.states.get(REAR).state == "on", "on one minute ago: still running"

    await _advance(hass, clock, REAR_DEFROST_MAX_S)
    assert hass.states.get(REAR).state == "off", "and it still has an end"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
