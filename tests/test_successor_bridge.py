"""The bridge that offers the move to `chery_connect`.

Why these tests matter more than the size of the module suggests. After the domain change HACS
leaves this integration on disk and loaded, and nothing else on the instance knows the owner has
to move. If the bridge stays silent, the owner stays on old code without being told; if it
raises, it takes down a working integration. Both failures are invisible from the outside, so
each one is fixed here.
"""
from __future__ import annotations

import pytest

SUCCESSOR = "chery_connect"


@pytest.fixture
def bridge():
    """The module under test, imported late so the package path is already pinned by conftest."""
    from custom_components.omoda9 import successor
    return successor


@pytest.fixture
def created_flows(monkeypatch, bridge):
    """Captures the discovery flows the bridge asks for, instead of starting them.

    Each item is a tuple (domain, context, data), as passed to `async_create_flow`.
    """
    calls: list[tuple] = []

    def fake_create_flow(hass, domain, context, data, **_kwargs):
        calls.append((domain, context, data))

    monkeypatch.setattr(bridge.discovery_flow, "async_create_flow", fake_create_flow)
    return calls


def _successor_installed(monkeypatch, bridge, *, error: Exception | None = None):
    """Makes the loader answer as if `chery_connect` were on disk.

    Args:
        monkeypatch: pytest fixture used to replace the loader call.
        bridge: the module under test.
        error: when given, the loader raises it for the successor domain instead of answering.
    """
    real = bridge.loader.async_get_integration

    async def fake_get_integration(hass, domain):
        if domain != SUCCESSOR:
            return await real(hass, domain)
        if error is not None:
            raise error
        return object()

    monkeypatch.setattr(bridge.loader, "async_get_integration", fake_get_integration)


def _issue(hass, bridge, entry):
    from homeassistant.helpers import issue_registry as ir
    return ir.async_get(hass).async_get_issue(bridge.DOMAIN, bridge.issue_id_for(entry))


async def test_without_the_successor_nothing_is_offered(hass, config_entry, bridge, created_flows):
    """The normal case today: no card, no notice, no noise for anyone not migrating yet."""
    assert await bridge.async_offer_successor(hass, config_entry) is False
    assert created_flows == []
    assert _issue(hass, bridge, config_entry) is None


async def test_with_the_successor_the_card_and_the_notice_appear(hass, config_entry, bridge, created_flows, monkeypatch):
    """The case the bridge exists for. Only the entry id travels: no credential leaves the entry."""
    from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY

    _successor_installed(monkeypatch, bridge)

    assert await bridge.async_offer_successor(hass, config_entry) is True
    assert created_flows == [(SUCCESSOR, {"source": SOURCE_INTEGRATION_DISCOVERY}, {"source_domain": bridge.DOMAIN, "source_entry_id": config_entry.entry_id})]
    issue = _issue(hass, bridge, config_entry)
    assert issue is not None
    assert issue.translation_key == "successor_available"


async def test_an_entry_already_migrated_is_left_alone(hass, config_entry, bridge, created_flows, monkeypatch):
    """Once the successor records where it came from, asking again would be a false alarm."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    _successor_installed(monkeypatch, bridge)
    MockConfigEntry(domain=SUCCESSOR, data={bridge.MIGRATED_FROM_KEY: config_entry.entry_id}).add_to_hass(hass)

    assert await bridge.async_offer_successor(hass, config_entry) is False
    assert created_flows == []


async def test_a_broken_successor_does_not_break_this_integration(hass, config_entry, bridge, created_flows, monkeypatch):
    """A half-copied successor folder must cost the owner a log line, not a working car."""
    _successor_installed(monkeypatch, bridge, error=RuntimeError("manifest unreadable"))

    assert await bridge.async_offer_successor(hass, config_entry) is False
    assert created_flows == []


async def test_a_failing_discovery_does_not_break_this_integration(hass, config_entry, bridge, monkeypatch):
    """Same guarantee one step later: the flow machinery itself refusing."""
    _successor_installed(monkeypatch, bridge)

    def refusing_create_flow(*_args, **_kwargs):
        raise RuntimeError("flow manager unavailable")

    monkeypatch.setattr(bridge.discovery_flow, "async_create_flow", refusing_create_flow)

    assert await bridge.async_offer_successor(hass, config_entry) is False


def test_the_notice_is_translated_in_every_language(bridge):
    """A notice without its text shows the raw key in Settings: the owner sees nothing useful."""
    import json
    import pathlib

    package = pathlib.Path(bridge.__file__).parent
    for path in [package / "strings.json", *sorted((package / "translations").glob("*.json"))]:
        issues = json.loads(path.read_text(encoding="utf-8"))["issues"]
        assert "successor_available" in issues, f"missing in {path.name}"
        assert "{url}" in issues["successor_available"]["description"], f"guide link missing in {path.name}"
