"""La migrazione degli entity_id: quello che succede a chi e' GIA' installato.

Il codice da solo non basta, ed e' il punto che si dimentica piu' facilmente. Home
Assistant ritrova un'entita' dal suo `unique_id` e riusa l'`entity_id` che ha in registro:
l'entity_id calcolato dal codice vale solo alla PRIMA registrazione. Senza la migrazione,
chi e' gia' installato terrebbe `sensor.omoda9_batteria` per sempre e solo le installazioni
nuove avrebbero i nomi inglesi.

Questi test girano sulla funzione di migrazione con un registro preparato a mano, perche'
e' l'unico modo di simulare "un'installazione che esiste da prima".
"""
from __future__ import annotations

import pytest


async def _migra(hass, entry):
    from custom_components.omoda9 import _async_migrate_entity_ids
    await _async_migrate_entity_ids(hass, entry)


@pytest.fixture
def registro(hass):
    from homeassistant.helpers import entity_registry as er
    return er.async_get(hass)


async def test_una_entita_vecchia_viene_rinominata(hass, config_entry, registro):
    """Il caso normale: c'era `sensor.omoda9_batteria`, diventa
    `sensor.chery_connect_battery`, e l'unique_id NON si tocca - e' l'identita', e
    cambiarla trasformerebbe un rename in una entita' nuova e vuota."""
    voce = registro.async_get_or_create(
        "sensor", "omoda9", "VINFINTO_batteria",
        suggested_object_id="omoda9_batteria", config_entry=config_entry)
    assert voce.entity_id == "sensor.omoda9_batteria"

    await _migra(hass, config_entry)

    dopo = registro.async_get("sensor.chery_connect_battery")
    assert dopo is not None, "l'entita' non e' stata rinominata"
    assert dopo.unique_id == "VINFINTO_batteria", "l'unique_id non deve muoversi"
    assert registro.async_get("sensor.omoda9_batteria") is None


async def test_non_sovrascrive_un_nome_gia_occupato(hass, config_entry, registro):
    """L'unico modo in cui questa migrazione perde dati, e il motivo per cui qui si salta.

    Se il nome di destinazione esiste gia', il recorder scrive "Cannot migrate history ...
    already in use" nel log e lascia lo storico indietro. Nessuna eccezione e nessun test
    rosso: se ne accorgerebbe fra mesi chi apre un grafico. Quindi la vecchia resta dov'e'
    e il fatto viene dichiarato, invece di rinominare e perdere lo storico in silenzio."""
    registro.async_get_or_create(
        "sensor", "omoda9", "VINFINTO_batteria",
        suggested_object_id="omoda9_batteria", config_entry=config_entry)
    # qualcun altro occupa gia' il posto di arrivo
    registro.async_get_or_create(
        "sensor", "altra_integrazione", "occupante",
        suggested_object_id="chery_connect_battery")

    await _migra(hass, config_entry)

    assert registro.async_get("sensor.omoda9_batteria") is not None, \
        "la vecchia doveva restare dov'era invece di perdere lo storico"
    assert registro.async_get("sensor.chery_connect_battery").unique_id == "occupante"


async def test_una_entita_gia_inglese_non_viene_toccata(hass, config_entry, registro):
    """La migrazione deve poter girare a ogni avvio senza fare niente: e' quello che
    succede dal secondo riavvio in poi, per sempre."""
    voce = registro.async_get_or_create(
        "sensor", "omoda9", "VINFINTO_batteria",
        suggested_object_id="chery_connect_battery", config_entry=config_entry)
    prima = voce.entity_id

    await _migra(hass, config_entry)
    await _migra(hass, config_entry)

    assert registro.async_get(prima) is not None
    assert registro.async_get(prima).unique_id == "VINFINTO_batteria"


async def test_una_entita_fuori_tabella_resta_com_e(hass, config_entry, registro):
    """Chi non e' in ENGLISH_KEYS non si muove. Vale per un'entita' aggiunta dopo la
    tabella da qualcuno che non sa che la tabella esiste."""
    registro.async_get_or_create(
        "sensor", "omoda9", "VINFINTO_sconosciuta",
        suggested_object_id="omoda9_cosa_sconosciuta", config_entry=config_entry)

    await _migra(hass, config_entry)

    assert registro.async_get("sensor.omoda9_cosa_sconosciuta") is not None


async def test_avvisa_l_utente_solo_se_ha_rinominato_qualcosa(hass, config_entry, registro):
    """L'elenco in un file non lo apre nessuno, e la domanda che l'utente si fa e' "quali
    sono le MIE?". L'avviso di riparazione e' il posto dove Home Assistant risponde.

    E non deve comparire a vuoto: chi installa da zero non ha niente da sistemare, e un
    avviso che compare quando non c'e' nulla da fare insegna a ignorare anche quelli veri."""
    from homeassistant.helpers import issue_registry as ir

    from custom_components.omoda9.const import DOMAIN

    reg_issue = ir.async_get(hass)
    issue_id = f"entity_ids_rinominati_{config_entry.entry_id}"

    # installazione nuova: nessuna entita' col vecchio nome -> nessun avviso
    await _migra(hass, config_entry)
    assert reg_issue.async_get_issue(DOMAIN, issue_id) is None

    # installazione che viene da prima -> avviso, col numero giusto
    registro.async_get_or_create(
        "sensor", "omoda9", "VINFINTO_batteria",
        suggested_object_id="omoda9_batteria", config_entry=config_entry)
    await _migra(hass, config_entry)

    avviso = reg_issue.async_get_issue(DOMAIN, issue_id)
    assert avviso is not None, "l'utente non viene avvisato del rename"
    assert avviso.translation_placeholders["count"] == "1"
    assert not avviso.is_fixable, "non c'e' niente che possiamo riparare al posto suo"
