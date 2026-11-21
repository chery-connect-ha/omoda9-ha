"""La chiave di traduzione si dichiara, e il passaggio all'inglese non perde niente.

Due meccanismi, uno sopra l'altro.

Il primo, dal 27 settembre 2026: `Omoda9Entity` RICAVAVA la chiave dall'`object_id`, cioe'
dallo stesso nome italiano da cui si costruisce l'entity_id. Chiave e indirizzo erano una
stringa sola, e per tre settimane questo ha fatto credere che tradurre le chiavi
obbligasse a cambiare il dominio dell'integrazione.

Il secondo: `naming.ENGLISH_KEYS` porta le 110 chiavi storiche ai nomi inglesi, e con loro
l'entity_id. I test qui sotto tengono aperta la separazione e sorvegliano l'unica proprieta'
della tabella che, se violata, fa perdere lo storico a qualcuno SENZA dirlo.
"""
from __future__ import annotations

import collections


def _coord(hass, entry):
    from custom_components.omoda9.const import DOMAIN
    return hass.data[DOMAIN][entry.entry_id]


def test_una_chiave_fuori_tabella_resta_com_e(hass, integrazione_avviata):
    """Il ripiego storico deve restare: un'entita' nuova, aggiunta domani da qualcuno che
    non sa che la tabella esiste, deve funzionare come ha sempre funzionato."""
    from custom_components.omoda9.entity import Omoda9Entity
    from custom_components.omoda9.naming import ENGLISH_KEYS

    coord = _coord(hass, integrazione_avviata)
    assert "cosa_nuova" not in ENGLISH_KEYS

    derivata = Omoda9Entity(coord, "Cosa nuova", "x1")
    assert derivata.translation_key == "cosa_nuova"

    dichiarata = Omoda9Entity(coord, "Cosa nuova", "x2", translation_key="brand_new_thing")
    assert dichiarata.translation_key == "brand_new_thing"


def test_una_chiave_in_tabella_porta_con_se_l_entity_id(hass, integrazione_avviata):
    """La conversione e' di due cose insieme, non di una. Se l'entity_id restasse indietro
    avremmo la chiave inglese e l'indirizzo italiano: il peggiore dei due mondi."""
    from custom_components.omoda9.entity import Omoda9Entity
    from custom_components.omoda9.naming import ENGLISH_KEYS, ID_PREFIX

    coord = _coord(hass, integrazione_avviata)
    assert ENGLISH_KEYS["batteria_scarica"] == "low_battery"

    e = Omoda9Entity(coord, "Batteria scarica", "bs1",
                     object_id="omoda9_batteria_scarica", entity_id_format="binary_sensor.{}")
    assert e.translation_key == "low_battery"
    assert e.entity_id == f"binary_sensor.{ID_PREFIX}_low_battery"


def test_la_tabella_non_produce_due_volte_lo_stesso_entity_id(hass, integrazione_avviata):
    """L'unico modo in cui questa migrazione perde dati, ed e' silenzioso.

    Il recorder sposta storico e statistiche quando un entity_id viene rinominato, MA se il
    nome di destinazione e' gia' occupato scrive "Cannot migrate history ... already in use"
    nel log e lascia lo storico indietro. Nessuna eccezione, nessun test rosso, nessun
    utente avvisato: se ne accorgerebbe fra mesi chi apre un grafico.

    Due nomi inglesi uguali su PIATTAFORME diverse vanno bene e ci sono: "Cool everything" e
    "Heat everything" stanno su un button e su uno switch. Il tipo di entita' li separa, sia
    nell'entity_id sia nelle chiavi di traduzione. Il controllo e' per piattaforma.
    """
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    ids = [e.entity_id for e in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id)]
    doppi = [i for i, n in collections.Counter(ids).items() if n > 1]
    assert not doppi, f"entity_id duplicati, lo storico di questi si perderebbe: {doppi}"

    chiavi = collections.Counter(
        (e.entity_id.split(".")[0], e.translation_key)
        for e in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id))
    doppie = [k for k, n in chiavi.items() if n > 1]
    assert not doppie, f"chiavi duplicate sulla stessa piattaforma: {doppie}"


def test_nessun_entity_id_e_rimasto_in_italiano(hass, integrazione_avviata):
    """La conversione o e' completa o e' peggio di niente: con meta' delle entita' inglesi e
    meta' italiane, una issue aperta da due utenti parla di due cose con nomi diversi."""
    from homeassistant.helpers import entity_registry as er

    from custom_components.omoda9.const import DOMAIN
    from custom_components.omoda9.naming import ID_PREFIX

    reg = er.async_get(hass)
    rimasti = [
        e.entity_id
        for e in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id)
        if e.entity_id.split(".", 1)[1].startswith(f"{DOMAIN}_")
    ]
    assert not rimasti, f"entity_id ancora col vecchio prefisso: {rimasti}"

    senza_prefisso = [
        e.entity_id
        for e in er.async_entries_for_config_entry(reg, integrazione_avviata.entry_id)
        if not e.entity_id.split(".", 1)[1].startswith(f"{ID_PREFIX}_")
    ]
    assert not senza_prefisso, f"entity_id senza il prefisso nuovo: {senza_prefisso}"
