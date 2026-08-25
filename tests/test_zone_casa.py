"""Le due domande sulla zona, provate direttamente e non aggirate.

Rilievo di @Caslinovich nella lettura di #33: `car_zone` era l'unica superficie condivisa
nuova **senza un test diretto** — tutti i test dei contatori la sostituivano con un
monkeypatch, quindi il confronto con `zone.home`, il ripiego su lat/lon e il ramo
"nessuna zona" non erano coperti. Ed era la funzione di cui aveva chiesto la lettura.

Qui si prova la differenza che conta, e che era il difetto: `async_active_zone` restituisce
la zona **piu' piccola** che contiene il punto, quindi un garage disegnato dentro casa
vince su `zone.home`. Per una presenza e' giusto cosi'; per l'energia no.
"""
from __future__ import annotations

import pytest

from custom_components.omoda9.entity import car_zone, in_zona_casa

CASA = {"lat": 45.0, "lon": 9.0}


@pytest.fixture
async def zone_casa(hass):
    """Solo `zone.home`, sulle coordinate di CASA."""
    hass.config.latitude, hass.config.longitude = CASA["lat"], CASA["lon"]
    await hass.async_block_till_done()
    return hass


@pytest.fixture
async def zone_casa_e_garage(zone_casa):
    """`zone.home` con dentro un `zone.garage` da 20 m sullo stesso punto."""
    from homeassistant.setup import async_setup_component

    await async_setup_component(zone_casa, "zone", {"zone": [{
        "name": "Garage", "latitude": CASA["lat"], "longitude": CASA["lon"], "radius": 20,
    }]})
    await zone_casa.async_block_till_done()
    return zone_casa


# ───────────────────────── senza fix GPS ─────────────────────────

@pytest.mark.parametrize("pos", [None, {}, {"lat": None, "lon": 9.0}, {"lat": "boh", "lon": "x"}])
async def test_senza_posizione_usabile_entrambe_si_astengono(zone_casa, pos):
    """`None` e non un valore inventato: chi chiama deve poter distinguere "non lo so"
    da "fuori", altrimenti l'energia finisce nel contatore sbagliato a ogni buco GPS."""
    assert car_zone(zone_casa, pos) is None
    assert in_zona_casa(zone_casa, pos) is None


# ───────────────────────── con la sola zone.home ─────────────────────────

async def test_dentro_casa_le_due_concordano(zone_casa):
    assert car_zone(zone_casa, CASA) == "home"
    assert in_zona_casa(zone_casa, CASA) is True


async def test_lontano_da_casa_le_due_concordano(zone_casa):
    lontano = {"lat": 46.5, "lon": 11.5}
    assert car_zone(zone_casa, lontano) == "away"
    assert in_zona_casa(zone_casa, lontano) is False


async def test_accetta_anche_latitude_longitude(zone_casa):
    """Il canale realtime nomina i campi in due modi; entrambi devono funzionare."""
    assert in_zona_casa(zone_casa, {"latitude": CASA["lat"], "longitude": CASA["lon"]}) is True


# ───────────────────────── il difetto: una zona dentro casa ─────────────────────────

async def test_un_garage_dentro_casa_separa_le_due_risposte(zone_casa_e_garage):
    """IL test di questo file, ed e' il difetto che la lettura di #33 ha trovato.

    `async_active_zone` restituisce la zona piu' piccola, quindi per il device_tracker
    l'auto e' "nel garage" e non "a casa" — corretto per una presenza. Se i contatori di
    energia usassero la stessa risposta, una ricarica domestica finirebbe nel contatore
    "fuori" per il solo fatto che l'utente ha disegnato una zona sopra la propria wallbox.
    """
    assert car_zone(zone_casa_e_garage, CASA) == "away"       # semantica device_tracker
    assert in_zona_casa(zone_casa_e_garage, CASA) is True     # contenimento: e' a casa
