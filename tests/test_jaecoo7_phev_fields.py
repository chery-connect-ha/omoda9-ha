"""Two realtime fields that mean something else on a Jaecoo 7 PHEV than their name suggests.

Why these are pinned. Both were reported by two owners each, with numbers that check out against
the car's own display (#3, #64), and both are silent errors: a sensor that shows 81 L in a 66 L
tank, or a "range" of 9488 km, does not crash anything and is simply believed.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def sensor_module():
    """The sensor platform module, imported late so the package path is already pinned by conftest."""
    from custom_components.chery_connect import sensor
    return sensor


def _spec(sensor_module, suffix):
    return next(spec for spec in sensor_module._RT_SENSORS if spec.suffix == suffix)


@pytest.mark.parametrize("model", ["Jaecoo 7", "JAECOO 7", "Jaecoo 7 Shs", "  jaecoo 7 phev "])
def test_fuel_left_is_a_percentage_on_a_jaecoo_7(sensor_module, model):
    """100 on a full 66 L tank: the field is a percentage there, whatever the spelling of the model."""
    from homeassistant.const import PERCENTAGE

    assert sensor_module._unit_for_model(_spec(sensor_module, "carburante_residuo"), model) == PERCENTAGE


@pytest.mark.parametrize("model", ["Omoda 9", "Omoda 5Ev", "Jaecoo 5", None, ""])
def test_fuel_left_stays_in_litres_everywhere_else(sensor_module, model):
    """Fail open: a model nobody has measured keeps the unit it always had, including an unread identity."""
    assert sensor_module._unit_for_model(_spec(sensor_module, "carburante_residuo"), model) == "L"


def test_electric_mileage_reads_electric_range(sensor_module):
    """`electricRange` is the cumulative electric distance, a counter, never the remaining range."""
    from homeassistant.components.sensor import SensorDeviceClass

    spec = _spec(sensor_module, "km_elettrici")
    assert spec.field == "electricRange"
    assert spec.device_class == SensorDeviceClass.DISTANCE
    assert spec.unit == "km"
    assert "electricRange" not in _spec(sensor_module, "range_elettrico").field, "the remaining range must not read the cumulative field"


def test_electric_mileage_is_not_created_on_a_battery_electric_car(sensor_module):
    """On a BEV the hybrid split it exists for is meaningless, like `hybrid_mileage` next to it."""
    assert "km_elettrici" in sensor_module._SENSORI_SOLO_TERMICO
