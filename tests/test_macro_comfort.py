"""Macro comfort «Raffredda/Riscalda tutto» e coda comandi.

Questi due test bloccano il difetto misurato in campo fra il 21 e il 31 luglio 2026 sui
cicli reali della macro: fra la pressione del tasto e la conferma dell'auto passavano
45-50 secondi, con l'interruttore già acceso e nulla di visibile. L'utente ripremeva, il
secondo ciclo si accavallava al primo e l'auto rifiutava con A00082 «veicolo occupato».

Le due cause sono indipendenti e vanno tenute ferme separatamente:

* la macro svegliava l'auto **anche quando era già desta**, pagando 35 secondi d'attesa
  per nulla (`test_macro_*`);
* la pausa che dovrebbe impedire a due comandi di accavallarsi si sbloccava al primo
  messaggio qualsiasi — e un'auto sveglia manda telemetria ogni pochi secondi, quindi la
  pausa durava mezzo secondo proprio quando serviva (`test_pausa_di_coda_*`).
"""
from __future__ import annotations

import asyncio
import time
from datetime import timedelta

import fixtures as FX
import pytest

from homeassistant.core import State
from homeassistant.util import dt as dt_util

from custom_components.omoda9 import coordinator as coord_mod
from custom_components.omoda9 import switch as switch_mod
from custom_components.omoda9.const import DOMAIN, MACRO_PRESET_S

MACRO = "switch.omoda9_raffredda_tutto"


class _Msg:
    """Il minimo che `_on_car_message` si aspetta da un messaggio paho."""

    def __init__(self, payload: dict) -> None:
        import json
        self.payload = json.dumps(payload).encode()
        self.topic = "app/1/test/account/msgCenter/msg"


async def _consegna(hass, coordinator, envelope: dict) -> None:
    coordinator._on_car_message(None, None, _Msg(envelope))
    await hass.async_block_till_done()


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


def _entita(hass, entity_id: str):
    """L'OGGETTO entità, non il suo stato: serve per guardare la scadenza interna."""
    componente = hass.data["entity_components"]["switch"]
    return next(e for e in componente.entities if e.entity_id == entity_id)


async def _avvia(hass, config_entry, monkeypatch) -> None:
    """Avvia l'integrazione come la fixture `integrazione_avviata`.

    Serve a parte perché il ripristino di stato va preparato PRIMA dell'avvio, e una
    fixture gira sempre prima del corpo del test."""
    from custom_components.omoda9.coordinator import Omoda9Coordinator

    monkeypatch.setattr(Omoda9Coordinator, "_provision_certs",
                        lambda self: (True, "cert finti (test)"))
    monkeypatch.setattr(Omoda9Coordinator, "_connect_car", lambda self: None)
    monkeypatch.setattr(Omoda9Coordinator, "async_start_keepalive", lambda self: None)
    monkeypatch.setattr(Omoda9Coordinator, "async_start_telemetry_poll", lambda self: None)
    monkeypatch.setattr(Omoda9Coordinator, "async_start_drive_watch", lambda self: None)

    async def _niente_backfill(self) -> None:
        return None

    monkeypatch.setattr(Omoda9Coordinator, "async_ensure_vehicle_identity", _niente_backfill)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def comandi_inviati(monkeypatch):
    """Registra i comandi invece di mandarli all'auto, e azzera le attese della macro
    (nei test interessa la SEQUENZA, non i secondi)."""
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0)
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT_AWAKE", 0)
    inviati: list[str] = []

    async def _finto(self, key, params=None):
        inviati.append(key)
        return "inviato (test)"

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _finto)
    return inviati


async def test_macro_non_sveglia_un_auto_gia_sveglia(hass, integrazione_avviata,
                                                     comandi_inviati):
    """Auto che sta pubblicando → niente `localizza`: il bus comfort è già alimentato.

    Il `localizza` in più non era gratis: occupava uno slot della coda comandi e il
    comando vero partiva 35 secondi dopo, finestra in cui una seconda pressione mandava
    tutto in collisione."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02())   # ← l'auto parla: è sveglia
    assert coord.auto_sveglia is True

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO},
                                   blocking=True)

    assert comandi_inviati == ["clima_raffredda_on"], (
        "ad auto desta la macro deve mandare SOLO il comando comfort")


async def test_macro_sveglia_un_auto_che_dorme(hass, integrazione_avviata,
                                               comandi_inviati):
    """Auto silenziosa → la sveglia resta obbligatoria, e prima del comando.

    È l'altra metà del fix: risparmiare i 35 secondi non deve trasformarsi nel saltare la
    sveglia a un'auto che dorme, dove i moduli comfort andrebbero tutti in timeout."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0                            # ← nessun messaggio: dorme

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO},
                                   blocking=True)

    assert comandi_inviati == ["localizza", "clima_raffredda_on"]


async def test_ultima_pressione_vince(hass, integrazione_avviata, comandi_inviati,
                                      monkeypatch):
    """Due pressioni opposte ravvicinate: all'auto arriva SOLO l'ultima.

    È il difetto riprodotto dal vivo il 2026-08-10 con l'auto ferma. L'attesa che precede
    l'invio dura 35 s se l'auto dorme e 5 s se è desta, e la scelta si fa al momento della
    pressione: la PRIMA pressione sveglia l'auto e con ciò spinge la SECONDA sul ramo corto,
    che quindi sorpassa. Misurato: «spegni» premuto alle 16:54:38,8 partito alle 16:55:15,8,
    «accendi» premuto alle 16:54:48,8 partito alle 16:54:54,2 → l'auto ha raffreddato e poi
    si è spenta, e l'interruttore è rimasto acceso.

    ⚠️ Le attese vanno rimesse DOPO la fixture, che le azzera entrambe: a zero i due cicli
    non si sovrappongono mai e il test passerebbe anche col difetto presente."""
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0.4)     # auto dormiente: attesa lunga
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT_AWAKE", 0.05)   # auto desta: attesa corta
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0                            # ← l'auto dorme: ramo lungo

    spegni = asyncio.create_task(
        hass.services.async_call("switch", "turn_off", {"entity_id": MACRO}, blocking=True))
    await asyncio.sleep(0.05)                           # il `localizza` è partito
    coord._last_msg_ts = time.time()                    # ← la sveglia è riuscita: auto desta
    assert coord.auto_sveglia is True

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    await spegni

    assert comandi_inviati == ["localizza", "clima_raffredda_on"], (
        "lo spegnimento premuto per primo ma sorpassato NON deve raggiungere l'auto")
    assert hass.states.get(MACRO).state == "on"


async def test_attesa_annunciata_mentre_sveglia_lauto(hass, integrazione_avviata,
                                                      comandi_inviati, monkeypatch):
    """Durante la sveglia l'utente deve vedere che sta succedendo qualcosa.

    Il silenzio di quei ~35 secondi è l'innesco del difetto qui sopra: l'utente ripreme
    perché nulla si muove. Il testo finisce nello stato di `sensor.omoda9_esito_comando`,
    che Home Assistant tronca a 255 caratteri → deve starci con margine."""
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0.05)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0                            # ← l'auto dorme

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    await hass.async_block_till_done()

    avviso = coord.data.get("cmd_status") or ""
    assert "Waking the car" in avviso and "Sveglio l'auto" in avviso, (
        "durante l'attesa di sveglia va pubblicata una riga bilingue su «Esito comando»")
    assert len(avviso) <= 203, "lo stato di HA si tronca: il testo deve restare corto"


async def test_spegnimento_fallito_lascia_acceso(hass, integrazione_avviata, monkeypatch):
    """Se il comando di spegnimento non parte, l'interruttore NON deve dire «spento».

    L'auto sta ancora lavorando: mettere l'interruttore su OFF (com'era prima) faceva
    sparire anche la scadenza, già disarmata a inizio ciclo, e nessuno avrebbe più riportato
    la macro a OFF."""
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0)
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT_AWAKE", 0)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()                    # auto desta: nessuna sveglia di mezzo

    inviati: list[str] = []

    async def _finto(self, key, params=None):
        inviati.append(key)
        if key.endswith("_off"):
            raise RuntimeError("backend irraggiungibile (test)")
        return "inviato (test)"

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _finto)

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    assert hass.states.get(MACRO).state == "on"

    with pytest.raises(Exception):
        await hass.services.async_call("switch", "turn_off", {"entity_id": MACRO},
                                       blocking=True)

    assert inviati == ["clima_raffredda_on", "clima_raffredda_off"]
    assert hass.states.get(MACRO).state == "on", (
        "spegnimento non riuscito: l'auto continua il preset, l'interruttore deve dirlo")
    macro = _entita(hass, MACRO)
    assert macro._resto_scadenza() is not None, "la scadenza va ripristinata, non persa"


async def test_ripristino_riarma_la_scadenza(hass, config_entry, cloud, monkeypatch):
    """Riavvio con la macro accesa: l'interruttore riprende, ma con la scadenza residua.

    Prima la scadenza viveva solo in memoria e il ripristino non la riarmava → dopo un
    riavvio di HA (o un aggiornamento HACS) l'interruttore restava acceso a tempo
    indeterminato. Verificato dal vivo il 2026-08-10: entry ricaricata alle 16:57 con la
    macro accesa, alle 17:16 era ancora accesa mentre l'auto aveva chiuso il preset."""
    from pytest_homeassistant_custom_component.common import mock_restore_cache

    acceso_da = dt_util.utcnow() - timedelta(seconds=MACRO_PRESET_S - 120)   # restano 2 min
    finito = dt_util.utcnow() - timedelta(seconds=MACRO_PRESET_S + 60)       # già scaduto
    mock_restore_cache(hass, (
        State(MACRO, "on", last_changed=acceso_da, last_updated=acceso_da),
        State("switch.omoda9_riscalda_tutto", "on", last_changed=finito, last_updated=finito),
    ))

    await _avvia(hass, config_entry, monkeypatch)

    assert hass.states.get(MACRO).state == "on", "preset ancora in corso: si riprende acceso"
    resto = _entita(hass, MACRO)._resto_scadenza()
    assert resto is not None and 60 < resto <= 120, (
        f"la scadenza va riarmata sul tempo RESIDUO, non da capo (resto={resto})")
    assert hass.states.get("switch.omoda9_riscalda_tutto").state == "off", (
        "preset finito mentre HA era spento: non si riprende acceso")

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_pausa_di_coda_ignora_la_telemetria(hass, integrazione_avviata,
                                                  monkeypatch):
    """La pausa fra due comandi finisce sulla CONFERMA, non su un messaggio qualsiasi.

    Era il difetto: `last_seen` avanza a ogni push, e un'auto sveglia ne manda uno ogni
    pochi secondi → la pausa scadeva subito e il comando successivo partiva a vettura
    ancora occupata (A00082)."""
    coord = _coordinator(hass, integrazione_avviata)
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 30)   # ampio: non deve mai scadere qui

    pausa = asyncio.create_task(coord._settle_after_command())
    await asyncio.sleep(0.2)

    await _consegna(hass, coord, FX.telemetry_5a02(dumpEnergy="61"))
    await asyncio.sleep(0.8)
    assert not pausa.done(), "la telemetria non è una conferma: la pausa deve proseguire"

    await _consegna(hass, coord, FX.cmd_confirm(result="1"))
    await asyncio.sleep(0.8)
    assert pausa.done(), "arrivata la conferma, il comando successivo può partire"
    await pausa


async def test_pausa_di_coda_ha_comunque_un_tetto(hass, integrazione_avviata,
                                                  monkeypatch):
    """Se la conferma non arriva MAI (auto che si riaddormenta, push perso) la pausa
    deve scadere da sola: un comando in coda non può restare appeso per sempre."""
    coord = _coordinator(hass, integrazione_avviata)
    monkeypatch.setattr(coord_mod, "COMMAND_SETTLE_S", 1)

    await asyncio.wait_for(coord._settle_after_command(), timeout=5)
