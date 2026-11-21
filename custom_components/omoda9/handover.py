"""Hand a vehicle over to `chery_connect` before its code is installed.

Why it exists. The integration moves to the `chery_connect` domain in 2.0, inside this same
repository. The Marketplace of Home Assistant refuses to install a version whose domain differs
from the installed one, and refuses to uninstall an integration while it has a config entry: its
only way out is deleting the entry, which deletes the entities and the device with it. So the move
cannot start from the new code. It has to start here, from the code that is already running.

What it does, once the owner confirms from the repair notice:

1. it stops this entry, so its entities are no longer loaded and can change integration;
2. it creates the `chery_connect` entry with the same login, PIN and options. Home Assistant keeps
   an entry whose integration is not installed yet: it shows it as not loaded and waits;
3. it copies (never moves) the session token, the mutual-TLS certificates and the task id under
   the names `chery_connect` reads;
4. it moves the entities, with unique id, entity id and history, then the device with its id.
   The device goes last: taking this entry off it would delete this entry's entities still on it;
5. it deletes this entry, now empty. From then on the Marketplace lets the owner remove this
   integration and install 2.0, which finds its entry ready and moves nothing.

Nothing here raises on a single entity or file: a move that stops half-way leaves an installation
in a state nobody can describe, and this runs on instances none of us can see.
"""
from __future__ import annotations

import inspect
import logging
import os
import shutil
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import CONF_VIN, DOMAIN

_LOGGER = logging.getLogger(__name__)

# The domain the vehicle is handed over to. A constant: there is one successor.
SUCCESSOR_DOMAIN = "chery_connect"

# Keys written into the new entry's data. They are the contract with `chery_connect`: its first
# setup reads them to know the entry came from here and that nothing is left to move.
MIGRATED_FROM_KEY = "migrated_from_entry_id"
SOURCE_DOMAIN_KEY = "migrated_from_domain"
MIGRATION_DONE_KEY = "migration_done"

# Repair issues: the offer, one per entry, and the next steps once it has been accepted.
OFFER_ISSUE_PREFIX = "handover_offer_"
DONE_ISSUE_PREFIX = "handover_done_"

GUIDE_URL = "https://github.com/chery-connect-ha/omoda9-ha/blob/master/docs/migrating-to-chery-connect.md"


def offer_issue_id(entry_id: str) -> str:
    """Repair issue id of the offer for one config entry.

    Args:
        entry_id: the config entry of this integration the offer is about.
    """
    return f"{OFFER_ISSUE_PREFIX}{entry_id}"


def async_offer_handover(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Raise the fixable notice that leads to the handover. Never raises.

    Args:
        hass: the running Home Assistant instance.
        entry: the config entry being set up.
    """
    try:
        ir.async_create_issue(
            hass,
            DOMAIN,
            offer_issue_id(entry.entry_id),
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="handover_offer",
            translation_placeholders={"title": entry.title, "url": GUIDE_URL},
            data={"entry_id": entry.entry_id},
        )
    except Exception:  # noqa: BLE001 - the notice must never break a working setup
        _LOGGER.warning("%s: could not offer the move to %s", DOMAIN, SUCCESSOR_DOMAIN, exc_info=True)


def _new_entry(source: ConfigEntry) -> ConfigEntry:
    """The `chery_connect` entry built from this one.

    The constructor of `ConfigEntry` gained required arguments over the Home Assistant versions
    `hacs.json` accepts, so only the ones this version knows are passed.

    Args:
        source: the config entry of this integration being handed over.
    """
    data = {**source.data, MIGRATED_FROM_KEY: source.entry_id, SOURCE_DOMAIN_KEY: DOMAIN, MIGRATION_DONE_KEY: True}
    arguments: dict[str, Any] = {
        "domain": SUCCESSOR_DOMAIN,
        "title": source.title,
        "data": data,
        "options": dict(source.options),
        "source": "user",
        "version": 1,
        "minor_version": 1,
        "unique_id": source.unique_id,
        "discovery_keys": {},
        "subentries_data": None,
    }
    accepted = inspect.signature(ConfigEntry.__init__).parameters
    return ConfigEntry(**{name: value for name, value in arguments.items() if name in accepted})


def copy_vehicle_files(config_dir: str, vin: str) -> list[str]:
    """Copy the per-vehicle files next to the names `chery_connect` reads. Runs in the executor.

    Copied rather than moved, and never over a file that already exists, so nothing here can make
    a state worse than it was.

    Args:
        config_dir: the Home Assistant configuration directory.
        vin: the vehicle identification number the files are named after.

    Returns:
        The names of the files and directories that were copied.
    """
    pairs = [
        (f"{DOMAIN}_{vin}_token.json", f"{SUCCESSOR_DOMAIN}_{vin}_token.json"),
        (f"{DOMAIN}_{vin}_taskid.txt", f"{SUCCESSOR_DOMAIN}_{vin}_taskid.txt"),
        (f"{DOMAIN}_{vin}_certs", f"{SUCCESSOR_DOMAIN}_{vin}_certs"),
    ]
    copied: list[str] = []
    for source_name, target_name in pairs:
        source = os.path.join(config_dir, source_name)
        target = os.path.join(config_dir, target_name)
        if not os.path.exists(source) or os.path.exists(target):
            continue
        try:
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            copied.append(target_name)
        except OSError as err:
            _LOGGER.warning("%s: could not copy %s: %s", DOMAIN, source_name, err)
    return copied


def _move_entities(hass: HomeAssistant, source: ConfigEntry, target: ConfigEntry, device_id: str | None) -> tuple[int, list[str]]:
    """Move every entity of this entry to the new one, keeping unique id, entity id and history.

    Args:
        hass: the running Home Assistant instance.
        source: the config entry of this integration.
        target: the new `chery_connect` entry.
        device_id: the device the entities stay on, or None when there is none.

    Returns:
        How many entities moved, and one line per entity that did not, with the reason.
    """
    registry = er.async_get(hass)
    moved = 0
    failed: list[str] = []
    for old in er.async_entries_for_config_entry(registry, source.entry_id):
        try:
            # Unloading leaves an `unavailable` state behind, and Home Assistant refuses to move an
            # entity that has one. The entry is unloaded, so nothing writes that state any more.
            hass.states.async_remove(old.entity_id)
            registry.async_update_entity_platform(
                old.entity_id, SUCCESSOR_DOMAIN, new_config_entry_id=target.entry_id, new_device_id=old.device_id or device_id
            )
            moved += 1
        except Exception as err:  # noqa: BLE001 - one entity must not stop the rest
            failed.append(f"{old.entity_id}: {type(err).__name__}: {err}")
    return moved, failed


def _move_device(hass: HomeAssistant, source: ConfigEntry, target: ConfigEntry, vin: str) -> str | None:
    """Hand the device over to the new entry, keeping its id, and return that id.

    Only after the entities: removing a config entry from a device makes Home Assistant delete that
    entry's entities still attached to it.

    Args:
        hass: the running Home Assistant instance.
        source: the config entry of this integration.
        target: the new `chery_connect` entry.
        vin: the vehicle identification number, part of the device identifier.
    """
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, source.entry_id):
        if (DOMAIN, vin) in device.identifiers:
            registry.async_update_device(device.id, add_config_entry_id=target.entry_id, new_identifiers={(SUCCESSOR_DOMAIN, vin)})
            registry.async_update_device(device.id, remove_config_entry_id=source.entry_id)
            return device.id
    return None


def _device_id(hass: HomeAssistant, source: ConfigEntry, vin: str) -> str | None:
    """The id of this entry's device for the vehicle, or None when it has none.

    Args:
        hass: the running Home Assistant instance.
        source: the config entry of this integration.
        vin: the vehicle identification number, part of the device identifier.
    """
    for device in dr.async_entries_for_config_entry(dr.async_get(hass), source.entry_id):
        if (DOMAIN, vin) in device.identifiers:
            return device.id
    return None


async def async_hand_over(hass: HomeAssistant, source: ConfigEntry) -> dict[str, Any]:
    """Run the whole handover for one entry. Called by the repair flow after the confirmation.

    Args:
        hass: the running Home Assistant instance.
        source: the config entry of this integration being handed over.

    Returns:
        A report: `moved` (entities), `failed` (one line each), `copied` (file names).
    """
    vin = source.data.get(CONF_VIN) or ""
    await hass.config_entries.async_unload(source.entry_id)

    target = _new_entry(source)
    await hass.config_entries.async_add(target)

    copied = await hass.async_add_executor_job(copy_vehicle_files, hass.config.config_dir, vin)
    moved, failed = _move_entities(hass, source, target, _device_id(hass, source, vin))
    _move_device(hass, source, target, vin)

    ir.async_delete_issue(hass, DOMAIN, offer_issue_id(source.entry_id))
    await hass.config_entries.async_remove(source.entry_id)

    ir.async_create_issue(
        hass,
        DOMAIN,
        f"{DONE_ISSUE_PREFIX}{target.entry_id}",
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="handover_done",
        translation_placeholders={"moved": str(moved), "not_moved": str(len(failed)), "url": GUIDE_URL},
    )
    _LOGGER.warning("%s: handed over to %s: %d entities, %d not moved, files copied: %s",
                    DOMAIN, SUCCESSOR_DOMAIN, moved, len(failed), ", ".join(copied) or "none")
    for line in failed:
        _LOGGER.warning("%s: not moved - %s", DOMAIN, line)
    return {"moved": moved, "failed": failed, "copied": copied}
