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


async def test_telemetria_spegne_la_macro(hass, integrazione_avviata, comandi_inviati,
                                          monkeypatch):
    """L'auto dice «clima spento» → l'interruttore la segue, anche fuori dalla scadenza.

    È l'altra metà del sintomo del 2026-08-10: alle 16:55:17,8 l'auto ha pubblicato clima e
    ventilazioni tutti a zero, i binary_sensor sedile si sono corretti, e la macro no — per
    costruzione, perché rifiutava di guardare la telemetria. Restava accesa fino alla
    scadenza in memoria, cioè per un quarto d'ora, annunciando un preset finito."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 0)   # niente finestra: si crede subito
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()                       # auto desta: nessuna sveglia

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    assert hass.states.get(MACRO).state == "on"

    await _consegna(hass, coord, FX.telemetry_5a02(
        frontHVACState="0", dSeatVentilateState="0", pSeatVentilateState="0"))

    assert hass.states.get(MACRO).state == "off", (
        "l'auto ha chiuso il preset: l'interruttore deve spegnersi senza aspettare i 15 min")
    assert _entita(hass, MACRO)._resto_scadenza() is None, "e la scadenza va disarmata"


async def test_telemetria_non_accende_la_macro(hass, integrazione_avviata,
                                               comandi_inviati):
    """Il clima acceso da altri NON deve accendere la macro: la correzione è a senso unico.

    `frontHVACState=1` non distingue «preset macro» da «clima acceso dalla card, dall'app
    ufficiale o dal guidatore». Accendere da qui farebbe comparire un «Raffredda tutto» che
    nessuno ha chiesto — e con esso una scadenza che spegnerebbe il clima altrui."""
    coord = _coordinator(hass, integrazione_avviata)
    assert hass.states.get(MACRO).state == "off"

    await _consegna(hass, coord, FX.telemetry_5a02(
        frontHVACState="1", dSeatVentilateState="3", pSeatVentilateState="3"))

    assert hass.states.get(MACRO).state == "off"


async def test_grazia_dopo_linvio(hass, integrazione_avviata, comandi_inviati,
                                  monkeypatch):
    """Subito dopo l'invio la telemetria NON viene creduta: l'auto non ha ancora agito.

    Fra il nostro comando e la sua esecuzione l'auto continua a pubblicare lo stato di
    prima — un 5A02 già in volo, o la risposta alla sveglia — con il clima a zero. Senza
    finestra di grazia l'interruttore si spegnerebbe un secondo dopo essere stato acceso,
    cioè si sostituirebbe un difetto con uno più visibile."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 300)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))

    assert hass.states.get(MACRO).state == "on", (
        "entro la finestra di grazia la telemetria stantia non deve spegnere la macro")


async def test_un_solo_sedile_spento_non_spegne_la_macro(hass, integrazione_avviata,
                                                         comandi_inviati, monkeypatch):
    """Un campo del preset a zero, senza notizie del clima: il preset non è finito.

    Il criterio è ancorato al clima, che è il cuore di entrambe le macro e compare in ogni
    conferma. Senza quell'ancora basterebbe un messaggio con il solo sedile a zero — il
    guidatore che lo spegne dal cruscotto — per spegnere l'interruttore mentre l'abitacolo
    continua a raffreddare: cioè per sostituire il difetto con il suo opposto.

    ⚠️ Il messaggio NON deve contenere `frontHVACState`: con il clima presente e acceso il
    caso passerebbe anche senza ancora, e il test non proverebbe nulla."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 0)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    await _consegna(hass, coord, FX.envelope("5A02", {"dSeatVentilateState": "0",
                                                      "time": "1721390002000"}))
    assert hass.states.get(MACRO).state == "on", (
        "un sedile spento non è il preset finito: manca la notizia sul clima")

    # ...e con il clima ancora acceso vale lo stesso, per la strada opposta.
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="1",
                                                   dSeatVentilateState="0"))
    assert hass.states.get(MACRO).state == "on"


async def test_riavvio_con_preset_gia_chiuso_dallauto(hass, config_entry, cloud,
                                                      monkeypatch):
    """Dopo un riavvio la correzione si applica SUBITO, senza finestra di grazia.

    È il caso che il riarmo della scadenza da solo non copre: HA riparte, l'interruttore
    si ripristina acceso con dieci minuti ancora da correre, ma l'auto nel frattempo ha già
    chiuso tutto. Nella nuova esecuzione non c'è alcun invio da proteggere, quindi il primo
    messaggio che dice «clima spento» vale."""
    from pytest_homeassistant_custom_component.common import mock_restore_cache

    acceso_da = dt_util.utcnow() - timedelta(seconds=60)
    mock_restore_cache(hass, (State(MACRO, "on", last_changed=acceso_da,
                                    last_updated=acceso_da),))
    await _avvia(hass, config_entry, monkeypatch)
    assert hass.states.get(MACRO).state == "on"

    coord = _coordinator(hass, config_entry)
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))

    assert hass.states.get(MACRO).state == "off"

    await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()


async def test_la_coda_si_libera_anche_se_il_task_viene_annullato(hass,
                                                                  integrazione_avviata,
                                                                  monkeypatch):
    """Comando annullato a metà: lo slot della coda deve tornare libero.

    `asyncio.CancelledError` deriva da `BaseException` e non passava dal `except Exception`
    che rilasciava lo slot: il lucchetto restava chiuso PER SEMPRE e da lì in poi ogni
    comando — compresi quelli del poll — falliva dopo 30 s con «L'auto è ancora impegnata»,
    fino al riavvio di Home Assistant. Basta un'automazione in `mode: restart` che si
    ri-attivi mentre l'invio è in volo."""
    coord = _coordinator(hass, integrazione_avviata)

    def _lento(key, params=None):
        time.sleep(2)
        return "inviato (test)"

    monkeypatch.setattr(coord, "_send_command", _lento)

    task = asyncio.create_task(coord.async_send_command("localizza"))
    await asyncio.sleep(0.2)
    assert coord._cmd_gate.locked(), "premessa del test: lo slot è occupato"
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert not coord._cmd_gate.locked(), (
        "annullamento del task: lo slot va restituito, o l'integrazione resta inerte")


async def test_una_sola_sveglia_condivisa(hass, integrazione_avviata, monkeypatch):
    """Due richieste di sveglia in contemporanea → UN solo `localizza`.

    La macro comfort e il ciclo di poll svegliano l'auto per due motivi diversi e senza
    sapere l'uno dell'altro. Nel diario diagnostico ci sono 13 coppie di `localizza` a meno
    di 60 secondi, 6 delle quali finite in A00082: il secondo non aggiunge nulla (l'auto o si
    è svegliata col primo, o non si sveglia) e occupa uno slot della coda più la pausa che lo
    segue, proprio mentre il comando vero aspetta di partire."""
    coord = _coordinator(hass, integrazione_avviata)
    inviati: list[str] = []

    async def _finto(self, key, params=None):
        inviati.append(key)
        await asyncio.sleep(0.2)          # l'invio dura: le due richieste si sovrappongono
        return "inviato (test)"

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _finto)

    await asyncio.gather(coord.async_assicura_sveglia(), coord.async_assicura_sveglia())
    assert inviati == ["localizza"], "due richieste contemporanee = una sola sveglia"

    # ...ma una richiesta successiva, a sveglia conclusa, deve poter svegliare di nuovo:
    # coalescere non vuol dire svegliare una volta sola per sempre.
    await coord.async_assicura_sveglia()
    assert inviati == ["localizza", "localizza"]


async def test_la_sveglia_condivisa_non_propaga_lerrore(hass, integrazione_avviata,
                                                        monkeypatch):
    """Sveglia fallita (tipicamente A00082) → chi la aspettava prosegue lo stesso.

    È il comportamento che macro e poll avevano già ciascuno per conto suo, e va conservato:
    la sveglia è un mezzo, non il fine. Se propagasse, un `localizza` rifiutato farebbe
    fallire la macro invece di farla proseguire con i suoi 35 secondi d'attesa."""
    coord = _coordinator(hass, integrazione_avviata)

    async def _finto(self, key, params=None):
        raise RuntimeError("A00082 veicolo occupato (test)")

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _finto)
    await coord.async_assicura_sveglia()     # non deve sollevare


async def test_un_messaggio_vecchio_non_spegne_una_macro_appena_accesa(
        hass, integrazione_avviata, comandi_inviati, monkeypatch):
    """Il caso che il difetto del 10/08 avrebbe prodotto AL CONTRARIO, ed è più frequente.

    L'auto pubblica il suo stato (clima spento, ovviamente: è ferma). L'utente preme
    «Raffredda tutto». Nessun messaggio nuovo arriva, ma le entità vengono notificate lo
    stesso, perché l'invio scrive i suoi passaggi in «Esito comando» e quello è un
    aggiornamento del coordinator. Se il messaggio vecchio non è stato consumato PRIMA —
    mentre la macro era ancora spenta — viene letto adesso come se fosse appena arrivato e
    spegne l'interruttore un istante dopo che l'utente l'ha acceso, con il comando già in
    viaggio verso l'auto. È il difetto del 10/08 rovesciato, e non richiede due pressioni:
    ne basta una."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 0)   # nessuna finestra a coprire l'errore
    coord = _coordinator(hass, integrazione_avviata)

    # L'auto parla (clima spento: è ferma) e resta desta, così la macro non passa dalla
    # sveglia e fra la pressione e l'invio non c'è nessun aggiornamento del coordinator:
    # il messaggio vecchio va consumato PRIMA, mentre la macro è ancora spenta.
    macro = _entita(hass, MACRO)
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))
    # L'invariante, asserita direttamente perché è quella che regge tutto il resto: un
    # messaggio è «già visto» anche se è arrivato mentre la macro era spenta. Verificarla
    # solo attraverso lo stato finale renderebbe il test dipendente da quali notifiche
    # capitano dopo la pressione, che è proprio ciò che non si deve dare per scontato.
    assert macro._msg_visto == coord.data["last_seen"], (
        "il messaggio va consumato anche a macro spenta, altrimenti alla prima accensione "
        "viene riletto come se fosse appena arrivato")

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    # Un aggiornamento del coordinator che NON viene dall'auto: nella realtà lo produce
    # l'invio stesso, che scrive i suoi passaggi in «Esito comando». Le entità vengono
    # notificate, ma nessun messaggio nuovo è arrivato.
    coord._update({"cmd_status": "Comando inviato (test)"})
    await hass.async_block_till_done()

    assert comandi_inviati == ["clima_raffredda_on"]
    assert hass.states.get(MACRO).state == "on", (
        "un messaggio anteriore alla pressione non può spegnere ciò che l'utente ha appena acceso")


async def test_la_conferma_di_un_comando_precedente_non_spegne(hass, integrazione_avviata,
                                                                comandi_inviati, monkeypatch):
    """Una conferma dell'auto NON viene creduta subito, e la ragione è una sequenza reale.

    Sembrerebbe ovvio fidarsi delle conferme: sono la risposta a un comando che l'auto ha già
    ricevuto, quindi non possono essere anteriori all'esecuzione. È vero per il comando che le
    ha generate, ma noi non sappiamo QUALE comando sia — l'auto rimanda indietro il `seq` che
    le abbiamo spedito, ma nessuno ha ancora misurato che sia lo stesso, quindi non si può
    correlare. Qui l'ack che arriva è quello di uno spegnimento partito prima, e porta tutti i
    campi a zero: crederci vorrebbe dire spegnere l'interruttore mentre l'auto sta raffreddando
    per via dell'accensione appena inviata — cioè rifare il difetto del 10/08 al contrario.

    Il caso che così si perde (l'auto conferma «tutto spento» e poi si riaddormenta senza dire
    altro) resta coperto dalla scadenza, come prima."""
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = time.time()

    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    assert hass.states.get(MACRO).state == "on"

    # ack di un comando PRECEDENTE (uno spegnimento), in ritardo: preset tutto a zero
    await _consegna(hass, coord, FX.envelope("110C", {
        "result": "2", "resultTime": "1721390002000", "seq": "X-1",
        "frontHVACState": "0", "dSeatVentilateState": "0", "pSeatVentilateState": "0",
        "lSeatVentilateState2": "0", "rSeatVentilateState2": "0"}))

    assert hass.states.get(MACRO).state == "on", (
        "non sappiamo di quale comando sia quella conferma: non può spegnere ciò che abbiamo "
        "appena acceso")


async def test_lo_stato_cumulativo_non_basta_a_spegnere(hass, integrazione_avviata,
                                                        comandi_inviati, monkeypatch):
    """Si guarda il messaggio, non lo storico: `fields` è cumulativo e mescola le epoche.

    Qui l'auto manda un messaggio che NON parla del clima (solo la spina di ricarica), mentre
    in `fields` resta un `frontHVACState=0` di prima. Leggendo lo stato accumulato la macro si
    spegnerebbe su un messaggio che non ha detto niente sul clima."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 0)
    coord = _coordinator(hass, integrazione_avviata)

    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))   # entra nei `fields`
    coord._last_msg_ts = time.time()
    await hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True)
    assert hass.states.get(MACRO).state == "on"

    await _consegna(hass, coord, FX.envelope("5A02", {"chargeGunState": "1",
                                                      "time": "1721390003000"}))
    assert coord.data["fields"].get("frontHVACState") == "0", "premessa: lo storico dice spento"
    assert hass.states.get(MACRO).state == "on", (
        "questo messaggio non parla del clima: non può dire che il preset è finito")


async def test_la_telemetria_della_sveglia_non_spegne_la_macro(hass, integrazione_avviata,
                                                               comandi_inviati, monkeypatch):
    """Durante i 35 secondi di sveglia l'auto pubblica lo stato di PRIMA: non conta.

    È la sequenza normale, non un caso di scuola: la macro sveglia l'auto proprio perché
    dormiva, l'auto si desta e la prima cosa che fa è raccontare com'è messa adesso — cioè
    col clima spento, visto che il nostro comando non è ancora partito. Quel messaggio è
    posteriore alla pressione ma anteriore al comando, quindi non dice niente sul preset."""
    monkeypatch.setattr(switch_mod, "MACRO_GRAZIA_S", 0)   # solo la guardia del ciclo in volo
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 0.4)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0                               # l'auto dorme → ramo lungo

    accendi = asyncio.create_task(
        hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True))
    await asyncio.sleep(0.05)
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))   # si sveglia e parla
    assert hass.states.get(MACRO).state == "on", (
        "la telemetria arrivata mentre il comando è ancora in coda parla di prima")
    await accendi
    assert comandi_inviati == ["localizza", "clima_raffredda_on"]


async def test_un_ciclo_annullato_non_ceca_la_macro(hass, integrazione_avviata,
                                                    comandi_inviati, monkeypatch):
    """Ciclo annullato durante l'attesa: si torna com'era, e la correzione resta viva.

    Fra la pressione e l'invio ci sono fino a 35 secondi, ed è la finestra più larga del
    componente: un'automazione in `mode: restart` che si ri-attivi lì dentro annulla il task.
    `CancelledError` deriva da `BaseException` e non passa da `except Exception` — senza un
    `finally` lasciava l'interruttore acceso, senza scadenza (già disarmata a inizio ciclo) e
    con la correzione dalla telemetria disattivata: tutte e tre le uscite spente insieme, cioè
    di nuovo «acceso a tempo indeterminato»."""
    monkeypatch.setattr(switch_mod, "MACRO_WAKE_WAIT", 5)
    coord = _coordinator(hass, integrazione_avviata)
    coord._last_msg_ts = 0.0                       # l'auto dorme → attesa lunga
    macro = _entita(hass, MACRO)

    ciclo = asyncio.create_task(
        hass.services.async_call("switch", "turn_on", {"entity_id": MACRO}, blocking=True))
    await asyncio.sleep(0.05)
    assert macro._invio_in_corso is True, "premessa: il ciclo è in volo"

    ciclo.cancel()
    with pytest.raises(asyncio.CancelledError):
        await ciclo
    await hass.async_block_till_done()

    assert macro._invio_in_corso is False, (
        "ciclo annullato: la macro deve tornare a farsi correggere dalla telemetria")
    assert hass.states.get(MACRO).state == "off", (
        "il comando non è mai partito: l'interruttore torna com'era")
    assert comandi_inviati == ["localizza"], "nessun comando comfort è stato spedito"
