"""Command queue: a busy refusal is retried, and the rear window gets a longer pause.

The field case, 23/10/2026: "rear window off" then "rear window on", tapped two seconds apart.
The queue held the second one back for COMMAND_SETTLE_S (15 s), but the car took 36 s to
confirm the first: the second went out to a busy car, came back A00082 and was lost — with a
push to the phone saying the command had failed.

A00082 means the command was NOT executed, so sending it again is safe; and the rear window's
confirmation is measured at 35-37 s, so its pause has to be longer than the common one.
"""
from __future__ import annotations

import asyncio
import time

import pytest

from custom_components.omoda9 import coordinator as coord_mod
from custom_components.omoda9.const import DOMAIN
from custom_components.omoda9.core import commands as CMD

BUSY = "Sbrina lunotto: HTTP 200 A00082 — auto occupata ⏳ (un altro comando è in corso)"
OK = "Sbrina lunotto: HTTP 200 A00079 — comando accettato ✅"


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


@pytest.fixture
def car(monkeypatch):
    """A scripted car: each send pops the next outcome ("busy", "ok", or a code)."""
    script: list[str] = []
    sent: list[str] = []

    def _send(ctx, key, emit=None, params=None, avvisa=None):
        sent.append(key)
        outcome = script.pop(0) if script else "ok"
        if outcome == "ok":
            emit(OK)
            return OK
        code = "A00082" if outcome == "busy" else outcome
        emit(BUSY if code == "A00082" else f"Sbrina lunotto: HTTP 200 {code} — rifiutato")
        raise CMD.CommandError(f"rifiutato {code}", code=code)

    monkeypatch.setattr(CMD, "send", _send)
    monkeypatch.setattr(coord_mod, "COMMAND_BUSY_WAIT_S", 0.2)
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 0.2)
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_SLOW_S", {})
    return script, sent


@pytest.fixture
def published(monkeypatch):
    """Every outcome text the coordinator publishes on «Esito comando»."""
    seen: list[str] = []
    real = coord_mod.Omoda9Coordinator._update

    def _spy(self, patch):
        if "cmd_status" in patch:
            seen.append(str(patch["cmd_status"]))
        return real(self, patch)

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "_update", _spy)
    return seen


async def _drain_queue(coord) -> None:
    """Let the background pause release the slot before the test ends."""
    for _ in range(50):
        if not coord._cmd_gate.locked():
            return
        await asyncio.sleep(0.05)


async def test_busy_is_retried_and_never_reported_as_failure(hass, integrazione_avviata,
                                                             car, published):
    script, sent = car
    script.extend(["busy", "ok"])
    coord = _coordinator(hass, integrazione_avviata)

    await coord.async_send_command("defrost_lunotto")

    assert sent == ["defrost_lunotto", "defrost_lunotto"], "refused as busy → sent again"
    assert not any("A00082" in s or "HTTP 200 A00082" in s for s in published), (
        "a refusal that is about to be retried must not read as a failure: the 'command "
        f"failed' blueprint would push it to the phone. Published: {published}")
    assert any("riprovo" in s for s in published), "the user can see that we are retrying"
    await _drain_queue(coord)


async def test_the_last_busy_refusal_is_reported(hass, integrazione_avviata, car, published):
    script, sent = car
    script.extend(["busy", "busy", "busy"])
    coord = _coordinator(hass, integrazione_avviata)

    with pytest.raises(CMD.CommandError) as err:
        await coord.async_send_command("defrost_lunotto")

    assert err.value.code == "A00082"
    assert len(sent) == 1 + coord_mod.COMMAND_BUSY_RETRIES, "bounded: no endless retrying"
    assert "A00082" in published[-1], (
        "after the last retry the refusal is the outcome, and the user has to be told")
    assert not coord._cmd_gate.locked(), "a failed command gives the queue back"


async def test_other_refusals_are_not_retried(hass, integrazione_avviata, car):
    script, sent = car
    script.append("A00084")                      # no permission: retrying cannot help
    coord = _coordinator(hass, integrazione_avviata)

    with pytest.raises(CMD.CommandError):
        await coord.async_send_command("defrost_lunotto")

    assert sent == ["defrost_lunotto"]


async def test_the_retry_goes_out_as_soon_as_the_car_confirms(hass, integrazione_avviata,
                                                              car, monkeypatch):
    """The car is free again when it confirms what kept it busy: no need to wait longer."""
    script, sent = car
    script.extend(["busy", "ok"])
    monkeypatch.setattr(coord_mod, "COMMAND_BUSY_WAIT_S", 30)
    coord = _coordinator(hass, integrazione_avviata)

    async def _confirm_soon():
        await asyncio.sleep(0.3)
        coord._confirm_n += 1                    # what a confirmation push does

    confirmer = asyncio.create_task(_confirm_soon())
    t0 = time.monotonic()
    await coord.async_send_command("defrost_lunotto")
    await confirmer

    assert len(sent) == 2
    assert time.monotonic() - t0 < 5, "retried on the confirmation, not after 30 s"
    await _drain_queue(coord)


async def test_the_rear_window_holds_the_queue_longer(hass, integrazione_avviata, car,
                                                      monkeypatch):
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_SLOW_S", {"defrost_lunotto": 1.5})
    coord = _coordinator(hass, integrazione_avviata)

    await coord.async_send_command("volante_caldo")
    await asyncio.sleep(0.6)
    assert not coord._cmd_gate.locked(), "an ordinary command: the common pause"

    await coord.async_send_command("defrost_lunotto")
    await asyncio.sleep(0.6)
    assert coord._cmd_gate.locked(), (
        "the rear window confirms in 35-37 s: the next command must not go out at 15")
    await _drain_queue(coord)
    await asyncio.sleep(1.2)
    assert not coord._cmd_gate.locked()
