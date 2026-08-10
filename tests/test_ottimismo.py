"""Stato ottimistico degli attuatori: quando decade e quando no.

Un comando ATTUA subito sull'auto, ma la verità torna via MQTT e solo ad auto sveglia. Nel
frattempo l'entità mostra lo stato richiesto. La domanda è quando smettere di mostrarlo, e la
risposta sbagliata costa cara in tutti e due i versi:

* troppo presto — era il difetto: bastava un messaggio QUALSIASI a far decadere l'ottimismo,
  comprese le conferme di comando (`110F`) e i push di posizione (`1301`), che non portano
  nemmeno un campo di stato. L'entità ricadeva sull'ultimo valore noto, cioè quello di PRIMA
  del comando, e mostrava il contrario di ciò che aveva appena fatto;
* troppo tardi — se si aspetta solo il proprio campo e quel campo non arriva più (auto che si
  riaddormenta, preset riuscito a metà, modello che non lo pubblica) l'entità resta sul valore
  comandato per sempre, in silenzio. Per questo c'è comunque un tetto temporale.

⚠️ Questi test coprono l'intervento più invasivo del lotto (18 switch, 3 cover, serratura,
clima): prima di scriverli, rimettere `entity.py` com'era lasciava la suite completamente
verde, ed è così che è passata inosservata la regressione della ricarica programmata.
"""
from __future__ import annotations

import time

import fixtures as FX
import pytest

from custom_components.omoda9 import coordinator as coord_mod
from custom_components.omoda9 import entity as entity_mod
from custom_components.omoda9.const import DOMAIN

SEDILE = "switch.omoda9_ventilazione_sedile_guida"
SERRATURA = "lock.omoda9_serratura"
RIC_PROG = "switch.omoda9_ricarica_programmata"


class _Msg:
    def __init__(self, payload: dict) -> None:
        import json
        self.payload = json.dumps(payload).encode()
        self.topic = "app/1/test/account/msgCenter/msg"


async def _consegna(hass, coordinator, envelope: dict) -> None:
    coordinator._on_car_message(None, None, _Msg(envelope))
    await hass.async_block_till_done()


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


@pytest.fixture
def comandi(monkeypatch):
    inviati: list[str] = []

    async def _finto(self, key, params=None):
        inviati.append(key)
        return "inviato (test)"

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_send_command", _finto)
    return inviati


async def test_una_conferma_senza_campi_non_annulla_lottimismo(hass, integrazione_avviata,
                                                               comandi):
    """Conferma del comando sedile (`110F`): result/seq e NIENTE stato → non decide nulla.

    Misurato sul diario dell'auto: gli 8 ack `110F` osservati portano soltanto `hasAsy`, che
    è un meta-campo e viene scartato. Prima bastavano a far tornare l'interruttore su OFF,
    con il sedile acceso, perché `fields` conservava ancora il valore precedente al comando."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(dSeatVentilateState="0"))

    await hass.services.async_call("switch", "turn_on", {"entity_id": SEDILE}, blocking=True)
    assert hass.states.get(SEDILE).state == "on"

    await _consegna(hass, coord, FX.envelope("110F", {
        "result": "2", "resultTime": "1721390002000", "seq": "X-1", "hasAsy": "1"}))

    assert hass.states.get(SEDILE).state == "on", (
        "una conferma vuota di stato non è la verità sul sedile: l'ottimismo resta")


async def test_il_proprio_campo_annulla_lottimismo(hass, integrazione_avviata, comandi):
    """...ma quando l'auto parla DI QUEL campo, vince lei — anche se la smentisce."""
    coord = _coordinator(hass, integrazione_avviata)
    await hass.services.async_call("switch", "turn_on", {"entity_id": SEDILE}, blocking=True)
    assert hass.states.get(SEDILE).state == "on"

    await _consegna(hass, coord, FX.telemetry_5a02(dSeatVentilateState="0"))

    assert hass.states.get(SEDILE).state == "off", (
        "il campo è arrivato e dice spento: l'entità deve seguire l'auto, non l'intenzione")


async def test_un_push_di_posizione_non_sblocca_la_serratura(hass, integrazione_avviata,
                                                             comandi):
    """La serratura non deve tornare indietro per un push di posizione.

    Succedeva in una sequenza normalissima: si bloccano le porte ad auto dormiente, entro il
    minuto il ciclo di poll manda `localizza`, l'auto risponde con un `1301` che contiene solo
    lat/lon — e la serratura tornava a mostrarsi sbloccata, perché `doorLock` in `fields` era
    ancora quello di ore prima."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(doorLock="1"))     # sbloccata
    assert hass.states.get(SERRATURA).state == "unlocked"

    await hass.services.async_call("lock", "lock", {"entity_id": SERRATURA}, blocking=True)
    assert hass.states.get(SERRATURA).state == "locked"

    await _consegna(hass, coord, FX.position_1301())

    assert hass.states.get(SERRATURA).state == "locked", (
        "un push di posizione non dice niente sulla serratura")


async def test_la_ricarica_programmata_segue_il_piano_dellauto(hass, integrazione_avviata,
                                                               comandi):
    """La ricarica programmata HA uno stato reale: `chargeAppointPlans`.

    È l'entità in cui è passata inosservata la regressione: senza dichiarare il proprio campo,
    l'ottimismo sarebbe durato fino al tetto dei 15 minuti anche dopo che l'auto aveva già
    comunicato il piano — per esempio perché il piano è stato rifiutato, o cambiato dall'app
    ufficiale."""
    coord = _coordinator(hass, integrazione_avviata)
    await hass.services.async_call("switch", "turn_on", {"entity_id": RIC_PROG}, blocking=True)
    assert hass.states.get(RIC_PROG).state == "on"

    await _consegna(hass, coord, FX.telemetry_5a02(
        chargeAppointPlans="[{'switchStatus': '0', 'startTime': '465'}]"))

    assert hass.states.get(RIC_PROG).state == "off", (
        "l'auto ha detto che il piano è spento: l'interruttore deve seguirla")


async def test_lottimismo_ha_comunque_una_scadenza(hass, integrazione_avviata, comandi,
                                                   monkeypatch):
    """Se il proprio campo non arriva MAI, l'ottimismo decade lo stesso.

    Senza questo tetto si scambierebbe un difetto con uno peggiore: un'entità che mostra per
    sempre, e in silenzio, un valore che nessuno ha mai confermato. Succede davvero — auto che
    si riaddormenta subito, preset riuscito a metà, campo che quel modello non pubblica."""
    monkeypatch.setattr(entity_mod, "OPT_MAX_S", 0)      # tetto immediato
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(dSeatVentilateState="0"))

    await hass.services.async_call("switch", "turn_on", {"entity_id": SEDILE}, blocking=True)
    assert hass.states.get(SEDILE).state == "on"

    # un messaggio che NON parla del sedile: da solo non annullerebbe nulla, ma il tetto sì
    await _consegna(hass, coord, FX.position_1301())

    assert hass.states.get(SEDILE).state == "off", (
        "scaduto il tetto l'entità torna sull'ultimo valore che l'auto ha davvero detto")


async def test_lantifurto_si_rilegge_dopo_il_comando(hass, integrazione_avviata, comandi,
                                                     monkeypatch):
    """L'antifurto non ha telemetria: dopo un comando si richiede lo stato vero al backend.

    Senza questa rilettura l'unica fonte, oltre all'ottimismo, sarebbe il valore letto
    all'avvio di Home Assistant: su una funzione di sicurezza, scaduto il tetto, l'interruttore
    ricadrebbe su un dato di stamattina. La rilettura aggiorna quel ripiego — **senza**
    scavalcare ciò che l'utente ha appena chiesto, perché il backend risponde subito mentre
    l'auto conferma dopo 8-38 secondi, e non sappiamo se quella risposta descriva il veicolo o
    l'intenzione appena registrata."""
    letture: list[int] = []

    async def _finta_lettura(self):
        letture.append(1)
        return 0                      # il backend dice: antifurto SPENTO

    monkeypatch.setattr(coord_mod.Omoda9Coordinator, "async_query_theft", _finta_lettura)

    await hass.services.async_call("switch", "turn_on",
                                   {"entity_id": "switch.omoda9_antifurto"}, blocking=True)
    await hass.async_block_till_done()

    assert len(letture) >= 1, "dopo il comando va richiesto lo stato reale"
    entita = next(e for e in hass.data["entity_components"]["switch"].entities
                  if e.entity_id == "switch.omoda9_antifurto")
    assert entita._real is False, "il ripiego va aggiornato con ciò che dice il backend"
    # ...ma NON deve prendere il posto di ciò che l'utente ha appena chiesto: il backend
    # potrebbe rispondere prima che l'auto abbia eseguito (la conferma vera arriva fra 8 e 38
    # secondi) e l'interruttore tornerebbe indietro un istante dopo la pressione.
    assert hass.states.get("switch.omoda9_antifurto").state == "on"


async def test_la_scheda_del_clima_non_torna_off_su_una_conferma_vuota(hass,
                                                                       integrazione_avviata,
                                                                       comandi):
    """La card clima ha una copia a mano della stessa regola, e va tenuta ferma qui.

    Le conferme di `airControl` osservate non portano `frontHVACState`: prima la card tornava
    su OFF con il clima acceso, e l'utente ripremeva — che è come nascono i comandi
    accavallati che la coda cerca di evitare."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))

    await hass.services.async_call("climate", "turn_on",
                                   {"entity_id": "climate.omoda9_clima"}, blocking=True)
    assert hass.states.get("climate.omoda9_clima").state == "heat_cool"

    await _consegna(hass, coord, FX.envelope("1104", {
        "result": "3", "resultTime": "1721390002000", "seq": "X-1"}))
    assert hass.states.get("climate.omoda9_clima").state == "heat_cool", (
        "una conferma senza il campo del clima non dice niente sul clima")

    await _consegna(hass, coord, FX.telemetry_5a02(frontHVACState="0"))
    assert hass.states.get("climate.omoda9_clima").state == "off", (
        "...ma quando il campo arriva davvero, vince l'auto")


async def test_il_baule_non_si_riapre_su_un_push_di_posizione(hass, integrazione_avviata,
                                                              comandi):
    """Stessa regola sulle tre aperture motorizzate (baule, finestrini, tetto)."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(trunkDoor="1"))      # baule aperto
    assert hass.states.get("cover.omoda9_baule").state == "open"

    await hass.services.async_call("cover", "close_cover",
                                   {"entity_id": "cover.omoda9_baule"}, blocking=True)
    assert hass.states.get("cover.omoda9_baule").state == "closed"

    await _consegna(hass, coord, FX.position_1301())
    assert hass.states.get("cover.omoda9_baule").state == "closed", (
        "un push di posizione non dice niente sul baule")

    # ...e la metà complementare, senza la quale il test passerebbe anche se la cover non
    # dichiarasse affatto i propri campi: quando il campo arriva davvero, vince l'auto.
    await _consegna(hass, coord, FX.telemetry_5a02(trunkDoor="1"))
    assert hass.states.get("cover.omoda9_baule").state == "open", (
        "il campo del baule è arrivato: l'ottimismo deve cedere")


async def test_un_messaggio_anteriore_al_comando_non_annulla_lottimismo(hass,
                                                                        integrazione_avviata,
                                                                        comandi):
    """L'ottimismo si annulla per il MIO campo, ma solo se il messaggio è POSTERIORE.

    È la controparte del marcatore della macro: senza il confronto con l'ancora presa al
    momento del comando, il messaggio già presente in `data` verrebbe riletto a ogni notifica
    del coordinator — comprese quelle che non vengono dall'auto — e annullerebbe l'ottimismo
    usando un valore anteriore al comando stesso."""
    coord = _coordinator(hass, integrazione_avviata)
    await _consegna(hass, coord, FX.telemetry_5a02(dSeatVentilateState="0"))

    await hass.services.async_call("switch", "turn_on", {"entity_id": SEDILE}, blocking=True)
    assert hass.states.get(SEDILE).state == "on"

    # nessun messaggio nuovo: solo un aggiornamento nostro (esito comando)
    coord._update({"cmd_status": "Comando inviato (test)"})
    await hass.async_block_till_done()

    assert hass.states.get(SEDILE).state == "on", (
        "il messaggio è anteriore al comando: non può smentirlo")
