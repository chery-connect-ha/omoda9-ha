"""Handing a vehicle over to `chery_connect` from the old code.

Why each property is pinned. The Marketplace refuses to change the domain of an installed
integration and refuses to uninstall one that still has a config entry; its only way out deletes
the entities and the device. So this handover is the only path for an owner of this integration,
and it runs once, on instances none of us can see. Each silent failure gets its own test: an
entity left behind is simply missing, a new device id breaks every device automation, an entry
left in place keeps the Marketplace refusing, a missing token sends a new code by text message.
"""
from __future__ import annotations

import pytest
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

import fixtures as FX

OLD = "omoda9"
NEW = "chery_connect"


@pytest.fixture
def handover():
    """The module under test, imported late so the package path is already pinned by conftest."""
    from custom_components.omoda9 import handover as module
    return module


async def _confirm(hass, entry_id: str):
    """Run the repair flow the owner opens from the notice: first display, then Submit.

    Returns:
        The result of the first display and the result of the confirmation.
    """
    from custom_components.omoda9.repairs import async_create_fix_flow

    from custom_components.omoda9.handover import offer_issue_id

    flow = await async_create_fix_flow(hass, offer_issue_id(entry_id), {"entry_id": entry_id})
    flow.hass = hass
    shown = await flow.async_step_init(None)
    done = await flow.async_step_init({})
    await hass.async_block_till_done()
    return shown, done


async def test_the_offer_is_raised_on_a_running_vehicle(hass, integrazione_avviata, handover):
    """Without the notice nobody finds the move: the Marketplace says nothing about it."""
    issue = ir.async_get(hass).async_get_issue(OLD, handover.offer_issue_id(integrazione_avviata.entry_id))
    assert issue is not None and issue.is_fixable


async def test_the_vehicle_is_handed_over_whole(hass, integrazione_avviata, handover):
    """Every entity keeps unique id and entity id and lands on the same device, which keeps its id."""
    entities, devices = er.async_get(hass), dr.async_get(hass)
    source = integrazione_avviata
    before = {e.entity_id: e.unique_id for e in er.async_entries_for_config_entry(entities, source.entry_id)}
    device = next(d for d in dr.async_entries_for_config_entry(devices, source.entry_id) if (OLD, FX.VIN) in d.identifiers)
    assert len(before) > 100, "prerequisite: the real platforms were set up"

    shown, done = await _confirm(hass, source.entry_id)

    assert shown["type"] == "form" and done["type"] == "create_entry"
    [target] = hass.config_entries.async_entries(NEW)
    after = {e.entity_id: e for e in er.async_entries_for_config_entry(entities, target.entry_id)}
    assert set(after) == set(before), "an entity was left behind or renamed"
    assert all(e.platform == NEW and e.unique_id == before[e.entity_id] for e in after.values())
    assert all(e.device_id == device.id for e in after.values() if e.device_id), "a new device id breaks device automations"
    moved_device = devices.async_get(device.id)
    assert moved_device.config_entries == {target.entry_id}
    assert (NEW, FX.VIN) in moved_device.identifiers


async def test_the_old_entry_is_gone_so_the_marketplace_lets_it_go(hass, integrazione_avviata, handover):
    """The Marketplace refuses to uninstall while any entry of the domain exists, even disabled."""
    await _confirm(hass, integrazione_avviata.entry_id)

    assert hass.config_entries.async_entries(OLD) == []


async def test_the_new_entry_carries_the_login_and_says_it_is_done(hass, integrazione_avviata, handover):
    """Same login and PIN, so no new code; and 2.0 must know there is nothing left to move."""
    from custom_components.omoda9.const import CONF_EMAIL, CONF_PIN, CONF_VIN

    hass.config_entries.async_update_entry(integrazione_avviata, options={"poll_normal": 30})
    await hass.async_block_till_done()
    source_id = integrazione_avviata.entry_id

    await _confirm(hass, source_id)

    [target] = hass.config_entries.async_entries(NEW)
    assert target.data[CONF_EMAIL] == FX.EMAIL and target.data[CONF_PIN] == FX.PIN and target.data[CONF_VIN] == FX.VIN
    assert target.data[handover.MIGRATED_FROM_KEY] == source_id
    assert target.data[handover.SOURCE_DOMAIN_KEY] == OLD
    assert target.data[handover.MIGRATION_DONE_KEY] is True
    assert target.options == {"poll_normal": 30}
    assert target.unique_id == FX.VIN


async def test_an_entity_the_owner_disabled_stays_disabled(hass, integrazione_avviata, handover):
    """The handover must not turn back on what the owner turned off."""
    entities = er.async_get(hass)
    some = er.async_entries_for_config_entry(entities, integrazione_avviata.entry_id)[0]
    entities.async_update_entity(some.entity_id, disabled_by=er.RegistryEntryDisabler.USER)

    await _confirm(hass, integrazione_avviata.entry_id)

    assert entities.async_get(some.entity_id).disabled_by == er.RegistryEntryDisabler.USER


async def test_the_owner_is_told_the_next_steps(hass, integrazione_avviata, handover):
    """The car stops updating until 2.0 is installed: the notice is how the owner finds out why."""
    source_id = integrazione_avviata.entry_id

    await _confirm(hass, source_id)

    [target] = hass.config_entries.async_entries(NEW)
    issues = ir.async_get(hass)
    assert issues.async_get_issue(OLD, f"{handover.DONE_ISSUE_PREFIX}{target.entry_id}") is not None
    assert issues.async_get_issue(OLD, handover.offer_issue_id(source_id)) is None, "the offer is answered"


async def test_the_session_files_are_copied_so_no_new_code_is_sent(hass, integrazione_avviata, handover):
    """Copied, under the names chery_connect reads; the originals stay."""
    import os

    config_dir = hass.config.config_dir
    token = os.path.join(config_dir, f"{OLD}_{FX.VIN}_token.json")
    with open(token, "w", encoding="utf-8") as handle:
        handle.write("{}")

    await _confirm(hass, integrazione_avviata.entry_id)

    assert os.path.exists(os.path.join(config_dir, f"{NEW}_{FX.VIN}_token.json"))
    assert os.path.exists(token), "the original must stay"


def test_a_file_already_there_is_never_overwritten(tmp_path, handover):
    """A file of chery_connect is never older than the one it would be replaced with."""
    (tmp_path / f"{OLD}_{FX.VIN}_taskid.txt").write_text("theirs")
    (tmp_path / f"{NEW}_{FX.VIN}_taskid.txt").write_text("ours")
    certs = tmp_path / f"{OLD}_{FX.VIN}_certs"
    certs.mkdir()
    (certs / "ca.pem").write_text("synthetic")

    copied = handover.copy_vehicle_files(str(tmp_path), FX.VIN)

    assert (tmp_path / f"{NEW}_{FX.VIN}_taskid.txt").read_text() == "ours"
    assert (tmp_path / f"{NEW}_{FX.VIN}_certs" / "ca.pem").exists()
    assert copied == [f"{NEW}_{FX.VIN}_certs"]


async def test_the_flow_stops_when_the_entry_is_gone(hass, handover):
    """A notice left over from an entry that no longer exists must not do anything."""
    from custom_components.omoda9.repairs import async_create_fix_flow

    flow = await async_create_fix_flow(hass, handover.offer_issue_id("missing"), {"entry_id": "missing"})
    flow.hass = hass

    result = await flow.async_step_init(None)

    assert result["type"] == "abort" and result["reason"] == "entry_not_found"


async def test_the_pin_notice_still_opens_the_pin_flow(hass):
    """The repair factory now serves two notices; the old one must still reach its own flow."""
    from custom_components.omoda9.repairs import Omoda9PinRepairFlow, async_create_fix_flow

    flow = await async_create_fix_flow(hass, "pin_wrong", {"entry_id": "x"})

    assert isinstance(flow, Omoda9PinRepairFlow)
