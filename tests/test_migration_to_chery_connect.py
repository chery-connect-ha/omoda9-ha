"""Moving a vehicle from `omoda9` or `omoda_jaecoo` to `chery_connect`.

Why each property is pinned. This runs once per installation, on instances none of us can see,
and every failure in it is silent: an entity left on the old integration is simply missing, a new
device id quietly breaks every device automation, an entity left disabled looks like a car that
stopped reporting. The owner notices days later and cannot tell what happened. So each of those
outcomes has its own test, and the flow that leads here has its own as well.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow

import fixtures as FX

OLD = "omoda9"
JAECOO = "omoda_jaecoo"


@pytest.fixture
def migration():
    """The module under test, imported late so the package path is already pinned by conftest."""
    from custom_components.chery_connect import migration as module
    return module


@pytest.fixture
def registries(hass):
    """The entity and device registries of the test instance, as a tuple (entities, devices)."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    return er.async_get(hass), dr.async_get(hass)


def _old_entry(hass, domain: str = OLD, **data):
    """An installed entry of an older integration, with synthetic credentials.

    Args:
        hass: the test Home Assistant instance.
        domain: the older integration it belongs to.
        data: extra config entry data, merged over the default synthetic credentials.
    """
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=domain, title=f"Omoda 9 ({FX.VIN})", unique_id=FX.VIN,
                            data={"vin": FX.VIN, "email": FX.EMAIL, "pin": FX.PIN, **data}, options={"poll_normal": 30})
    entry.add_to_hass(hass)
    return entry


def _old_vehicle(registries, entry, domain: str = OLD):
    """A device and two entities of the old integration, as 1.14 leaves them in the registry.

    Returns:
        The old device and a dict of the registry entries keyed by a short name.
    """
    entities, devices = registries
    device = devices.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(domain, FX.VIN)}, name="Omoda 9")
    battery = entities.async_get_or_create("sensor", domain, f"{FX.VIN}_battery", suggested_object_id="chery_connect_battery",
                                           config_entry=entry, device_id=device.id)
    hidden = entities.async_get_or_create("sensor", domain, f"{FX.VIN}_speed", suggested_object_id="chery_connect_speed",
                                          config_entry=entry, device_id=device.id)
    return device, {"battery": battery, "hidden": hidden}


def _new_entry(hass, migration, source):
    """The entry the config flow creates for `source`, without going through the flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.chery_connect.const import DOMAIN

    entry = MockConfigEntry(domain=DOMAIN, title=source.title, unique_id=FX.VIN, data=migration.imported_data(source))
    entry.add_to_hass(hass)
    return entry


async def test_an_omoda9_vehicle_moves_whole(hass, migration, registries):
    """The common case: same unique ids, same entity ids. The entity changes integration and nothing
    else, the device keeps its id, and the old entry stops talking to the car."""
    from custom_components.chery_connect.const import DOMAIN

    entities, devices = registries
    source = _old_entry(hass)
    device, old = _old_vehicle(registries, source)
    entry = _new_entry(hass, migration, source)

    assert await migration.async_complete_migration(hass, entry) is True

    assert source.disabled_by is not None, "two integrations would talk to the same car"
    battery = entities.async_get(old["battery"].entity_id)
    assert battery.platform == DOMAIN
    assert battery.config_entry_id == entry.entry_id
    assert battery.unique_id == f"{FX.VIN}_battery"
    assert battery.entity_id == "sensor.chery_connect_battery", "the entity id is what dashboards and history hang on"
    assert battery.device_id == device.id, "a new device id breaks every device automation"
    moved_device = devices.async_get(device.id)
    assert (DOMAIN, FX.VIN) in moved_device.identifiers
    assert entry.entry_id in moved_device.config_entries
    assert source.entry_id not in moved_device.config_entries


async def test_moved_entities_come_back_enabled(hass, migration, registries):
    """Disabling the old entry disables its entities 'by the config entry'. Left like that, the
    owner would see a car that stopped reporting; an entity THEY disabled stays disabled."""
    from homeassistant.helpers import entity_registry as er

    entities, _devices = registries
    source = _old_entry(hass)
    _device, old = _old_vehicle(registries, source)
    entities.async_update_entity(old["hidden"].entity_id, disabled_by=er.RegistryEntryDisabler.USER)
    await hass.config_entries.async_set_disabled_by(source.entry_id, config_entries.ConfigEntryDisabler.USER)
    await hass.async_block_till_done()
    assert entities.async_get(old["battery"].entity_id).disabled_by == er.RegistryEntryDisabler.CONFIG_ENTRY, "prerequisite"

    await migration.async_complete_migration(hass, _new_entry(hass, migration, source))

    assert entities.async_get(old["battery"].entity_id).disabled_by is None
    assert entities.async_get(old["hidden"].entity_id).disabled_by == er.RegistryEntryDisabler.USER


async def test_the_move_happens_once(hass, migration, registries):
    """Every later restart sets the same entry up again: it must not try to move anything twice."""
    source = _old_entry(hass)
    _old_vehicle(registries, source)
    entry = _new_entry(hass, migration, source)

    assert await migration.async_complete_migration(hass, entry) is True
    assert await migration.async_complete_migration(hass, entry) is False
    assert migration.entries_to_migrate(hass) == [], "the old entry must not be offered again"


async def test_the_owner_is_told_what_is_left(hass, migration, registries):
    """The old folder stays on disk and HACS will not remove it: the notice is how anyone finds out."""
    from homeassistant.helpers import issue_registry as ir

    from custom_components.chery_connect.const import DOMAIN

    source = _old_entry(hass)
    _old_vehicle(registries, source)
    entry = _new_entry(hass, migration, source)
    ir.async_create_issue(hass, OLD, f"successor_available_{source.entry_id}", is_fixable=False,
                          severity=ir.IssueSeverity.WARNING, translation_key="successor_available")

    await migration.async_complete_migration(hass, entry)

    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"remove_old_integration_{entry.entry_id}") is not None
    assert issues.async_get_issue(OLD, f"successor_available_{source.entry_id}") is None, "the bridge's notice is answered"


async def test_an_omoda_jaecoo_vehicle_moves_with_its_device(hass, migration, registries):
    """The other line: names differ and the mapping of #78 renames them, and the device still keeps its id."""
    entities, devices = registries
    source = _old_entry(hass, JAECOO, area="44")
    device = devices.async_get_or_create(config_entry_id=source.entry_id, identifiers={(JAECOO, FX.VIN)}, name="Jaecoo 7")
    engine = entities.async_get_or_create("binary_sensor", JAECOO, f"{FX.VIN}_engineState", suggested_object_id="engine",
                                          config_entry=source, device_id=device.id)
    entry = _new_entry(hass, migration, source)
    await hass.config_entries.async_set_disabled_by(source.entry_id, config_entries.ConfigEntryDisabler.USER)
    await hass.async_block_till_done()

    await migration.async_complete_migration(hass, entry)

    moved = entities.async_get("binary_sensor.chery_connect_engine")
    assert moved is not None, "the entity was not renamed to the canonical name"
    assert moved.device_id == device.id
    assert moved.disabled_by is None
    assert entities.async_get(engine.entity_id) is None or engine.entity_id == moved.entity_id


def test_imported_data_keeps_the_login_and_says_where_it_came_from(hass, migration):
    """The login is reused so the owner is not sent a new code; one key changed name on the fork."""
    source = _old_entry(hass, JAECOO, area="44")
    data = migration.imported_data(source)

    assert data["email"] == FX.EMAIL and data["pin"] == FX.PIN and data["vin"] == FX.VIN
    assert data["area_code"] == "44" and "area" not in data
    assert data[migration.MIGRATED_FROM_KEY] == source.entry_id
    assert data[migration.SOURCE_DOMAIN_KEY] == JAECOO


@pytest.mark.parametrize("source_domain", [OLD, JAECOO])
def test_vehicle_files_are_copied_not_moved(tmp_path, migration, source_domain):
    """Copied, so the old integration can still start if re-enabled; never over a file of ours."""
    (tmp_path / f"omoda9_{FX.VIN}_token.json").write_text("{}")
    certs = tmp_path / f"{source_domain}_{FX.VIN}_certs"
    certs.mkdir()
    (certs / "ca.pem").write_text("synthetic")
    (tmp_path / f"chery_connect_{FX.VIN}_taskid.txt").write_text("ours")
    (tmp_path / f"{source_domain}_{FX.VIN}_taskid.txt").write_text("theirs")

    copied = migration.copy_vehicle_files(str(tmp_path), source_domain, FX.VIN)

    assert (tmp_path / f"chery_connect_{FX.VIN}_token.json").exists()
    assert (tmp_path / f"chery_connect_{FX.VIN}_certs" / "ca.pem").exists()
    assert (tmp_path / f"omoda9_{FX.VIN}_token.json").exists(), "the original must stay"
    assert (tmp_path / f"chery_connect_{FX.VIN}_taskid.txt").read_text() == "ours"
    assert f"chery_connect_{FX.VIN}_taskid.txt" not in copied


# ── The flow that leads here ──────────────────────────────────────────────────────────────────

@pytest.fixture
def no_setup():
    """Stops the created entry from starting the real integration (MQTT, timers, the car)."""
    with patch("custom_components.chery_connect.async_setup_entry", AsyncMock(return_value=True)):
        yield


async def test_the_bridge_card_leads_to_one_confirmation(hass, migration, no_setup):
    """From the card the old integration opens: one confirmation, no code, the old entry disabled first."""
    from custom_components.chery_connect.const import DOMAIN

    source = _old_entry(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={"source_domain": OLD, "source_entry_id": source.entry_id})
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "migrate_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"][migration.MIGRATED_FROM_KEY] == source.entry_id
    assert result["data"]["pin"] == FX.PIN
    assert result["options"] == {"poll_normal": 30}
    assert source.disabled_by is not None


async def test_add_integration_offers_the_move_first(hass, no_setup):
    """Whoever missed the card ends up in "Add integration": the move must be on offer there."""
    from custom_components.chery_connect.const import DOMAIN

    _old_entry(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["menu_options"][0] == "migrate_existing"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "migrate_existing"})
    assert result["step_id"] == "migrate_confirm"


async def test_without_an_old_integration_the_menu_is_unchanged(hass, no_setup):
    """A new owner sees the three ways to sign in, and nothing about a move they have no use for."""
    from custom_components.chery_connect.const import DOMAIN

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert "migrate_existing" not in result["menu_options"]


async def test_a_vehicle_already_here_is_not_moved_again(hass, config_entry, no_setup):
    """Same VIN already configured in Chery Connect: the card must not create a second entry."""
    from custom_components.chery_connect.const import DOMAIN

    source = _old_entry(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
        data={"source_domain": OLD, "source_entry_id": source.entry_id})

    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert source.disabled_by is None, "an aborted move must leave the old integration running"
