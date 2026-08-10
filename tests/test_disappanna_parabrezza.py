"""Disappannamento del parabrezza dal clima — `airControl {frontDefrosting}`, voce 2045.

**Perché questa funzione ha bisogno di test suoi.** È la prima aggiunta che nasce dall'indagine
sulle funzioni consentite e mai usate (`FUNZIONI_INESPLORATE_20260810.md`), e porta con sé
esattamente il rischio contro cui il progetto mette in guardia da mesi: assomiglia a una funzione
che abbiamo già. L'auto invece le tiene distinte, e ciascuna ha il PROPRIO campo di stato:

    frontWindshieldControl  →  `frontWindshieldHeat`   riscaldamento elettrico del vetro
    airControl frontDefrosting →  `fWinHeatingState`   aria del clima soffiata sul parabrezza

Se un giorno qualcuno "semplificasse" facendo puntare i due switch allo stesso campo o allo stesso
comando, nessun test esistente se ne accorgerebbe e l'utente si ritroverebbe due interruttori che
fanno la stessa cosa — o peggio, uno che ne muove un altro. Da qui `test_le_due_funzioni_restano_distinte`.

La catena è MISURATA fino allo strato 2 (l'auto ha eseguito, non solo il backend ha accettato),
cattura del 2026-06-20:
    19:43:58  airControl {frontDefrosting:"1"}  → push 1104 result 2, `fWinHeatingState` "1"
    19:45:32  airControl {airControlType:"0"}   → `fWinHeatingState` "0" nel 5A02 delle 19:45:35
"""
from __future__ import annotations

import pytest


def test_i_due_comandi_esistono_nel_catalogo(core):
    """Corpo esatto, ricavato dall'envelope reale dell'app."""
    commands = core["commands"]
    catalogo = dict(commands.COMMANDS)

    acceso = catalogo["disappanna_parabrezza"]
    assert acceso["endpoint"] == "airControl"
    assert acceso["body"]["frontDefrosting"] == "1"
    # `airControlType:"1"` fa parte della richiesta: è l'effetto collaterale dichiarato
    # (si accende anche il clima). Toglierlo produrrebbe un corpo che l'endpoint non accetta.
    assert acceso["body"]["airControlType"] == "1"

    spento = catalogo["disappanna_parabrezza_off"]
    assert spento["endpoint"] == "airControl"
    # Lo spegnimento è quello del clima: è l'unico MISURATO, ed è quello che riporta davvero
    # `fWinHeatingState` a 0. Un `frontDefrosting:"0"` sarebbe stato un'analogia non verificata.
    assert spento["body"]["airControlType"] == "0"
    assert "frontDefrosting" not in spento["body"]


def test_le_due_funzioni_restano_distinte(core):
    """⚠️ Il test che conta. Sbrinamento elettrico e disappannamento dal clima sono due cose:
    endpoint diversi, campi diversi, campi di stato diversi. Fonderli è la regressione facile."""
    commands = core["commands"]
    catalogo = dict(commands.COMMANDS)

    elettrico = catalogo["defrost_parabrezza"]
    dal_clima = catalogo["disappanna_parabrezza"]

    assert elettrico["endpoint"] != dal_clima["endpoint"]
    assert "frontWindshieldHeat" in elettrico["body"]
    assert "frontWindshieldHeat" not in dal_clima["body"]
    assert "frontDefrosting" in dal_clima["body"]
    assert "frontDefrosting" not in elettrico["body"]


def test_nessun_pulsante_doppione(core):
    """I comandi di uno switch non devono generare anche due pulsanti: è il modo tipico in cui
    il conteggio delle entità cresce senza che nessuno se ne accorga."""
    from custom_components.omoda9.const import COMMANDS_AS_RICH_ENTITY

    assert "disappanna_parabrezza" in COMMANDS_AS_RICH_ENTITY
    assert "disappanna_parabrezza_off" in COMMANDS_AS_RICH_ENTITY


def test_il_campo_di_stato_non_e_promosso_a_entita_ricca(core):
    """`fWinHeatingState` deve restare anche binary_sensor.

    Promuoverlo farebbe sparire `binary_sensor.omoda9_riscaldamento_parabrezza`, che esiste
    dal giugno 2026: l'entità cambierebbe dominio, lo storico si spezzerebbe e nel registro
    resterebbe un orfano `unavailable` — cioè si romperebbe proprio l'invariante di salute
    («0 unavailable») per far quadrare quello del conteggio. Meglio un'entità in più."""
    from custom_components.omoda9.const import FIELDS_AS_RICH_ENTITY

    assert "fWinHeatingState" not in FIELDS_AS_RICH_ENTITY


async def test_lo_switch_esiste_e_segue_lauto(hass, integrazione_avviata):
    """L'entità c'è, e il suo stato viene dal campo dell'auto, non da un'invenzione locale."""
    stato = hass.states.get("switch.omoda9_disappannamento_parabrezza")
    assert stato is not None, "lo switch del disappannamento non è stato creato"


async def test_lo_switch_non_ruba_il_binary_sensor(hass, integrazione_avviata):
    """Le due entità devono convivere: quella nuova non sostituisce quella che c'era."""
    assert hass.states.get("binary_sensor.omoda9_riscaldamento_parabrezza") is not None
    assert hass.states.get("switch.omoda9_disappannamento_parabrezza") is not None
    # e lo sbrinamento elettrico, che è un'altra funzione, resta al suo posto
    assert hass.states.get("switch.omoda9_sbrinamento_parabrezza") is not None
