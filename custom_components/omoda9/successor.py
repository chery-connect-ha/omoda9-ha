"""Bridge to the successor integration, `chery_connect`.

Why this exists. The integration is moving to the `chery_connect` domain. If `chery_connect`
ends up installed next to this one (put there by hand, or from another repository), Home Assistant
never sets it up, because it has no config entry: the owner would keep running this code without
being told. The only code certain to run on that instance is this one, so this is where the move
is offered. When `chery_connect` is not installed, which is the normal case because the Marketplace
refuses to change the domain of an installed integration, `handover.py` takes over instead.

What it does, and nothing more: when `chery_connect` is installed, it opens a discovery card for
it and raises a repair notice. It passes the entry id only. Credentials stay where they are: the
successor reads them from this entry on the same instance, after the owner confirms. Nothing
moves without that confirmation.

The module is kept free of anything specific to this line, so the same file can ship on the
`omoda_jaecoo` line with only `DOMAIN` changing.
"""
from __future__ import annotations

import logging

from homeassistant import loader
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery_flow
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# The domain this integration is handing over to. A constant rather than a setting: there is one
# successor, and a typo here would silently disable the whole bridge.
SUCCESSOR_DOMAIN = "chery_connect"

# Key under which the successor records, in its own entry data, which entry it migrated from.
# It is the contract between the two integrations: change it on one side only and every owner
# keeps being offered a migration they have already done.
MIGRATED_FROM_KEY = "migrated_from_entry_id"

MIGRATION_GUIDE_URL = "https://github.com/chery-connect-ha/omoda9-ha/blob/master/docs/migrating-to-chery-connect.md"


def issue_id_for(entry: ConfigEntry) -> str:
    """Repair issue id for one config entry, shared with the successor so it can clear it.

    Args:
        entry: the config entry of this (old) integration the notice is about.
    """
    return f"successor_available_{entry.entry_id}"


def _already_migrated(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Whether a `chery_connect` entry already says it came from this entry.

    Args:
        hass: the running Home Assistant instance.
        entry: the config entry of this (old) integration.
    """
    return any(
        successor.data.get(MIGRATED_FROM_KEY) == entry.entry_id
        for successor in hass.config_entries.async_entries(SUCCESSOR_DOMAIN)
    )


async def async_offer_successor(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Offer the migration to `chery_connect` when it is installed. Never raises.

    The bridge must not be able to break the integration it lives in: any failure is logged and
    the setup carries on as if the successor were absent.

    Args:
        hass: the running Home Assistant instance.
        entry: the config entry being set up.

    Returns:
        True when the card and the notice were offered, False otherwise.
    """
    try:
        await loader.async_get_integration(hass, SUCCESSOR_DOMAIN)
    except loader.IntegrationNotFound:
        return False
    except Exception:  # noqa: BLE001 - a broken successor folder must not take this one down
        _LOGGER.warning("%s: %s is on disk but cannot be loaded; migration not offered", DOMAIN, SUCCESSOR_DOMAIN, exc_info=True)
        return False

    if _already_migrated(hass, entry):
        return False

    try:
        discovery_flow.async_create_flow(
            hass,
            SUCCESSOR_DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data={"source_domain": DOMAIN, "source_entry_id": entry.entry_id},
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id_for(entry),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="successor_available",
            translation_placeholders={"title": entry.title, "url": MIGRATION_GUIDE_URL},
        )
    except Exception:  # noqa: BLE001 - see the docstring: the bridge never breaks the setup
        _LOGGER.warning("%s: could not offer the migration to %s", DOMAIN, SUCCESSOR_DOMAIN, exc_info=True)
        return False

    _LOGGER.info("%s: %s is installed, migration offered for %s", DOMAIN, SUCCESSOR_DOMAIN, entry.title)
    return True
