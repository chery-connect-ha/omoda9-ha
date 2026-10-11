"""Sunroof vent / tilt position, exposed as a button like the window ventilation.

The car accepts `skylightControl` with `controlType` "2" for the tilt position (the
official app's `controlTiltUp`). It gets a button of its own, `Vent sunroof`, the same way
`Vent windows` does: it maps on neither open nor close, and the existing close of the
sunroof cover brings the roof back down.

These tests check the wiring only. Whether the car actually tilts is a hardware question
that no test here can answer.
"""
from __future__ import annotations

import pytest
from homeassistant.components.cover import CoverEntityFeature

from custom_components.omoda9 import coordinator as coord_mod
from custom_components.omoda9.const import COMMANDS_AS_RICH_ENTITY

VENT_SUNROOF = "button.chery_connect_vent_sunroof"
VENT_WINDOWS = "button.chery_connect_vent_windows"
SUNROOF = "cover.chery_connect_sunroof"


@pytest.fixture
def sent(monkeypatch):
    keys: list[str] = []

    async def _fake(self, key, params=None):
        keys.append(key)
        return "sent (test)"

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _fake)
    return keys


def test_vent_command_body(core):
    """Same endpoint as open/close, only `controlType` differs."""
    catalogue = dict(core["commands"].COMMANDS)
    assert catalogue["tetto_ventila"]["endpoint"] == "skylightControl"
    assert catalogue["tetto_ventila"]["body"] == {"controlType": "2", "skylightType": "1"}
    # open and close are untouched
    assert catalogue["tetto_apri"]["body"] == {"controlType": "1", "skylightType": "1"}
    assert catalogue["tetto_chiudi"]["body"] == {"controlType": "0", "skylightType": "1"}


def test_vent_command_is_a_button_like_the_windows():
    assert "tetto_ventila" not in COMMANDS_AS_RICH_ENTITY
    assert "finestrini_ventila" not in COMMANDS_AS_RICH_ENTITY


async def test_vent_button_exists_next_to_the_window_one(hass, integrazione_avviata):
    assert hass.states.get(VENT_SUNROOF) is not None
    assert hass.states.get(VENT_WINDOWS) is not None


async def test_pressing_the_button_sends_the_vent_command(hass, integrazione_avviata, sent):
    await hass.services.async_call("button", "press", {"entity_id": VENT_SUNROOF},
                                   blocking=True)
    assert sent == ["tetto_ventila"]


async def test_sunroof_cover_keeps_only_open_and_close(hass, integrazione_avviata, sent):
    features = hass.states.get(SUNROOF).attributes["supported_features"]
    assert features == CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    await hass.services.async_call("cover", "close_cover", {"entity_id": SUNROOF},
                                   blocking=True)
    assert sent == ["tetto_chiudi"], "closing from the vent position is the ordinary close"
