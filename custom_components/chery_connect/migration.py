"""Move a vehicle from an older integration (`omoda9`, `omoda_jaecoo`) to this one.

Why it exists. In 2.0 the integration took its final domain, `chery_connect`. For Home Assistant
that is a different integration: without this module every owner would get a second, empty set of
entities, a second device, and a second client talking to the same car with the same certificate,
while the history stayed attached to an integration they are about to delete.

How the owner gets here. The old code (1.14.0-beta.15 and later on `omoda9`, 1.8.1 on
`omoda_jaecoo`) notices this integration and opens a discovery card for it; anyone who missed that
finds the same offer under "Add integration". Either way the owner confirms once, and the config
flow creates an entry that remembers where it came from. The move itself happens here, at the
first setup of that entry, because that is the only moment when the new entry exists and none of
its entities has been loaded yet.

What moves, in order:

1. the old entry is disabled, so the two integrations never talk to the car at the same time;
2. the per-vehicle files (session token, mutual-TLS certificates, task id) are copied, never
   moved: the old integration must still be able to start if the owner turns it back on;
3. the entities move with their unique id, entity id and history;
4. the device moves with its id, so automations that use the device keep working. Last, because
   taking the old entry off a device deletes that entry's entities still attached to it.

Nothing here raises on a single entity or file: a move that stops half-way leaves an installation
in a state nobody can describe, and this runs on instances none of us can see.
"""
from __future__ import annotations

import logging
import os
import shutil

from homeassistant.config_entries import ConfigEntry, ConfigEntryDisabler
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from .const import CONF_VIN, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Domains this integration takes vehicles over from, in the order they are offered.
SOURCE_DOMAINS: tuple[str, ...] = ("omoda9", "omoda_jaecoo")

# Keys written into the new entry's data. MIGRATED_FROM_KEY is shared with the bridge in the old
# integrations (`successor.py` there): change it on one side only and every owner keeps being
# offered a move they have already made.
MIGRATED_FROM_KEY = "migrated_from_entry_id"
SOURCE_DOMAIN_KEY = "migrated_from_domain"
MIGRATION_DONE_KEY = "migration_done"

# Config entry keys that changed name between the lines, old -> new. Everything else is common
# ancestry and keeps its name; keys that only one line has are carried along and ignored.
_RENAMED_DATA_KEYS: dict[str, dict[str, str]] = {
    "omoda_jaecoo": {"area": "area_code"},
}

# Session token file name per source, with `{vin}` to fill. The `omoda_jaecoo` line never renamed
# its token file when it forked, so both lines write the same name.
_TOKEN_FILE: dict[str, str] = {
    "omoda9": "omoda9_{vin}_token.json",
    "omoda_jaecoo": "omoda9_{vin}_token.json",
}


def entries_to_migrate(hass: HomeAssistant) -> list[ConfigEntry]:
    """Config entries of the older integrations that no entry of ours has taken over yet.

    Args:
        hass: the running Home Assistant instance.
    """
    taken = {entry.data.get(MIGRATED_FROM_KEY) for entry in hass.config_entries.async_entries(DOMAIN)}
    return [
        entry
        for source_domain in SOURCE_DOMAINS
        for entry in hass.config_entries.async_entries(source_domain)
        if entry.entry_id not in taken
    ]


def imported_data(source_entry: ConfigEntry) -> dict:
    """The data of a new entry built from an old one: same credentials, plus where it came from.

    Args:
        source_entry: the config entry of the older integration being taken over.
    """
    renamed = _RENAMED_DATA_KEYS.get(source_entry.domain, {})
    data = {renamed.get(key, key): value for key, value in source_entry.data.items()}
    data[MIGRATED_FROM_KEY] = source_entry.entry_id
    data[SOURCE_DOMAIN_KEY] = source_entry.domain
    return data


def copy_vehicle_files(config_dir: str, source_domain: str, vin: str) -> list[str]:
    """Copy the per-vehicle files of the old integration next to ours. Runs in the executor.

    Copied rather than moved, and never over a file that already exists: the old integration must
    still start if the owner re-enables it, and a file of ours is never older than theirs.

    Args:
        config_dir: the Home Assistant configuration directory.
        source_domain: the domain of the integration being taken over.
        vin: the vehicle identification number both integrations name their files after.

    Returns:
        The names of the files and directories that were copied.
    """
    pairs = [
        (_TOKEN_FILE.get(source_domain, f"{source_domain}_{{vin}}_token.json").format(vin=vin), f"{DOMAIN}_{vin}_token.json"),
        (f"{source_domain}_{vin}_taskid.txt", f"{DOMAIN}_{vin}_taskid.txt"),
        (f"{source_domain}_{vin}_certs", f"{DOMAIN}_{vin}_certs"),
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


def _old_device(hass: HomeAssistant, source_entry: ConfigEntry, vin: str) -> dr.DeviceEntry | None:
    """The device of the old integration for this vehicle, or None when it has none.

    Args:
        hass: the running Home Assistant instance.
        source_entry: the config entry being taken over.
        vin: the vehicle identification number, part of the device identifier.
    """
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, source_entry.entry_id):
        if (source_entry.domain, vin) in device.identifiers:
            return device
    return None


def _move_device(hass: HomeAssistant, entry: ConfigEntry, source_entry: ConfigEntry, device: dr.DeviceEntry, vin: str) -> None:
    """Hand the old device over to the new entry, keeping its id.

    Keeping the id is the point: device triggers, conditions and actions in automations refer to a
    device by id, and a new device would break every one of them without a word.

    ⚠️ Only AFTER the entities have moved. Removing a config entry from a device makes Home
    Assistant delete that entry's entities attached to it: done first, it would delete exactly the
    entities this module exists to keep.

    Args:
        hass: the running Home Assistant instance.
        entry: the new config entry.
        source_entry: the config entry being taken over.
        device: the old device, from `_old_device`.
        vin: the vehicle identification number, part of the device identifier.
    """
    registry = dr.async_get(hass)
    registry.async_update_device(
        device.id,
        add_config_entry_id=entry.entry_id,
        new_identifiers={(DOMAIN, vin)},
        disabled_by=None if device.disabled_by == dr.DeviceEntryDisabler.CONFIG_ENTRY else device.disabled_by,
    )
    registry.async_update_device(device.id, remove_config_entry_id=source_entry.entry_id)


def _move_entities(hass: HomeAssistant, entry: ConfigEntry, source_entry: ConfigEntry, device_id: str | None) -> dict:
    """Move the old entities to this integration, keeping unique id, entity id and history.

    For `omoda9` the unique ids are identical on both sides, so the entity changes integration and
    nothing else. For `omoda_jaecoo` the suffixes and names differ, and the mapping already written
    and field-tested for #78 does the work.

    Args:
        hass: the running Home Assistant instance.
        entry: the new config entry.
        source_entry: the config entry being taken over.
        device_id: the moved device the entities belong to, or None when there was none to move.
    """
    from .legacy import LEGACY_DOMAIN, adotta

    registry = er.async_get(hass)
    if source_entry.domain == LEGACY_DOMAIN:
        report = adotta(hass, entry, device_id=device_id)
    else:
        report = {"adottate": [], "saltate": [], "non_migrabili": [], "sostituite": 0}
        for old in er.async_entries_for_config_entry(registry, source_entry.entry_id):
            try:
                registry.async_update_entity_platform(old.entity_id, DOMAIN, new_config_entry_id=entry.entry_id, new_device_id=device_id)
                report["adottate"].append((old.entity_id, old.entity_id))
            except Exception as err:  # noqa: BLE001 - one entity must not stop the rest
                report["saltate"].append((old.entity_id, f"{type(err).__name__}: {err}"))

    # Disabling the old entry disabled its entities too, flagged as "by the config entry". That
    # reason no longer holds once they belong to us; an entity the owner disabled stays disabled.
    # Home Assistant 2026.2 already clears the flag when an entity moves to an enabled entry; this
    # is for the older versions `hacs.json` still accepts, and costs nothing where it is redundant.
    for moved in er.async_entries_for_config_entry(registry, entry.entry_id):
        if moved.disabled_by == er.RegistryEntryDisabler.CONFIG_ENTRY:
            registry.async_update_entity(moved.entity_id, disabled_by=None)
    return report


async def async_complete_migration(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Finish the move this entry was created for, once, before any of its entities is loaded.

    Args:
        hass: the running Home Assistant instance.
        entry: the config entry being set up.

    Returns:
        True when a move was carried out now, False when there was nothing to do.
    """
    source_id = entry.data.get(MIGRATED_FROM_KEY)
    if not source_id or entry.data.get(MIGRATION_DONE_KEY):
        return False
    source_domain = entry.data.get(SOURCE_DOMAIN_KEY) or ""
    vin = entry.data.get(CONF_VIN) or ""

    source_entry = hass.config_entries.async_get_entry(source_id)
    if source_entry is not None and source_entry.disabled_by is None:
        # Normally done by the config flow already; repeated here because an entry can also come
        # from a flow that was interrupted after creating it.
        await hass.config_entries.async_set_disabled_by(source_id, ConfigEntryDisabler.USER)

    copied = await hass.async_add_executor_job(copy_vehicle_files, hass.config.config_dir, source_domain, vin)

    report = {"adottate": [], "saltate": [], "non_migrabili": [], "sostituite": 0}
    if source_entry is not None:
        device = _old_device(hass, source_entry, vin)
        report = _move_entities(hass, entry, source_entry, device.id if device else None)
        if device is not None:
            _move_device(hass, entry, source_entry, device, vin)

    hass.config_entries.async_update_entry(entry, data={**entry.data, MIGRATION_DONE_KEY: True})

    ir.async_delete_issue(hass, source_domain, f"successor_available_{source_id}")
    ir.async_create_issue(
        hass,
        DOMAIN,
        f"remove_old_integration_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="remove_old_integration",
        translation_placeholders={
            "domain": source_domain,
            "moved": str(len(report["adottate"])),
            "not_moved": str(len(report["non_migrabili"]) + len(report["saltate"])),
        },
    )
    _LOGGER.warning(
        "%s: moved from %s: %d entities, %d not movable, %d skipped, files copied: %s",
        DOMAIN, source_domain, len(report["adottate"]), len(report["non_migrabili"]), len(report["saltate"]), ", ".join(copied) or "none",
    )
    for old, reason in report["non_migrabili"] + report["saltate"]:
        _LOGGER.warning("%s: %s not moved - %s", DOMAIN, old, reason)
    return True
