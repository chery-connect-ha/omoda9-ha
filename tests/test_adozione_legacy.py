"""Adozione delle entita' della linea `omoda_jaecoo`, con il loro storico.

Chi viene dalla linea del fork non sta aggiornando: per Home Assistant quella e' un'altra
integrazione. Senza adozione si ritrova 110 entita' nuove e vuote mentre le sue, con anni
di storico, restano attaccate a un'integrazione che sta per disinstallare. Lo storico non
si esporta: o viene adottato adesso, o e' perso.

Il meccanismo e' `async_update_entity_platform`, che Home Assistant documenta esattamente
per questo e che NESSUNA delle sue 1401 integrazioni usa. Quindi ogni proprieta' e' fissata
qui: non e' un percorso su cui ci si possa appoggiare all'esperienza di altri.
"""
from __future__ import annotations

import pytest

VIN = "VINFINTO"


@pytest.fixture
def registro(hass):
    from homeassistant.helpers import entity_registry as er
    return er.async_get(hass)


def _vecchia(registro, config_entry_legacy, piattaforma, suffisso, object_id):
    return registro.async_get_or_create(
        piattaforma, "omoda_jaecoo", f"{VIN}_{suffisso}",
        suggested_object_id=object_id, config_entry=config_entry_legacy)


@pytest.fixture
def config_entry_legacy(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    e = MockConfigEntry(domain="omoda_jaecoo", data={}, title="vecchia")
    e.add_to_hass(hass)
    return e


@pytest.fixture
def entry_nostro(hass, config_entry):
    hass.config_entries.async_update_entry(config_entry, data={**config_entry.data, "vin": VIN})
    return config_entry


async def test_un_suffisso_identico_viene_adottato(hass, registro, entry_nostro, config_entry_legacy):
    """Il caso degli 83: il suffisso e' il nome del campo dell'API Chery, uguale sulle due
    linee. L'entita' cambia integrazione e nome, e resta la stessa entita' - che e' il punto,
    perche' e' l'identita' a cui lo storico e' attaccato."""
    from custom_components.omoda9.legacy import adotta
    from custom_components.omoda9.const import DOMAIN

    _vecchia(registro, config_entry_legacy, "binary_sensor", "engineState", "engine")

    r = adotta(hass, entry_nostro)

    assert len(r["adottate"]) == 1
    nuova = registro.async_get("binary_sensor.chery_connect_engine")
    assert nuova is not None, "l'entita' non e' stata rinominata"
    assert nuova.platform == DOMAIN, "l'entita' non e' passata alla nostra integrazione"
    assert nuova.unique_id == f"{VIN}_engineState"


async def test_un_suffisso_diverso_usa_la_tabella(hass, registro, entry_nostro, config_entry_legacy):
    """Il caso dei 13: stessa entita', suffisso scritto nella lingua di chi l'ha aggiunta.
    Senza la tabella queste resterebbero orfane, e sono quelle che l'utente nota."""
    from custom_components.omoda9.legacy import adotta

    _vecchia(registro, config_entry_legacy, "binary_sensor", "rt_battery_low", "battery_low")

    r = adotta(hass, entry_nostro)

    assert len(r["adottate"]) == 1
    nuova = registro.async_get("binary_sensor.chery_connect_low_battery")
    assert nuova is not None
    assert nuova.unique_id == f"{VIN}_rt_batteria_scarica"


async def test_la_gemella_vuota_lascia_il_posto_a_quella_con_lo_storico(
        hass, registro, entry_nostro, config_entry_legacy):
    """Chi configura l'integrazione PRIMA di adottare si ritrova due entita' per la stessa
    cosa: la nostra, nuova e vuota, e la sua, piena. Vince quella piena.

    E' l'unico punto in cui questa funzione cancella qualcosa. Cancella solo roba nostra, e
    solo quando ha il rimpiazzo gia' in mano."""
    from custom_components.omoda9.legacy import adotta

    registro.async_get_or_create(
        "binary_sensor", "omoda9", f"{VIN}_engineState",
        suggested_object_id="chery_connect_engine", config_entry=entry_nostro)
    _vecchia(registro, config_entry_legacy, "binary_sensor", "engineState", "engine")

    r = adotta(hass, entry_nostro)

    assert r["sostituite"] == 1
    nuova = registro.async_get("binary_sensor.chery_connect_engine")
    assert nuova.unique_id == f"{VIN}_engineState"
    # una sola entita' per quella cosa, non due
    tutte = [e for e in registro.entities.values() if e.unique_id == f"{VIN}_engineState"]
    assert len(tutte) == 1


async def test_cio_che_non_si_puo_adottare_viene_dichiarato(hass, registro, entry_nostro, config_entry_legacy):
    """Cinque entita' non sono portabili: due perche' le due linee le hanno fatte di tipo
    diverso, tre perche' sul canonico non esistono. Devono comparire nel rapporto: un numero
    che non torna, scoperto dall'utente dopo, costa la fiducia in tutto il resto."""
    from custom_components.omoda9.legacy import adotta

    _vecchia(registro, config_entry_legacy, "select", "windows_select", "windows")

    r = adotta(hass, entry_nostro)

    assert not r["adottate"]
    assert len(r["non_migrabili"]) == 1
    assert "select" in r["non_migrabili"][0][1] or "cover" in r["non_migrabili"][0][1]
    assert registro.async_get("select.windows") is not None


async def test_dry_run_non_scrive_niente(hass, registro, entry_nostro, config_entry_legacy):
    """Far vedere cosa succederebbe, prima che succeda. Su un'operazione senza precedenti
    in 1401 integrazioni, e' il minimo."""
    from custom_components.omoda9.legacy import adotta

    v = _vecchia(registro, config_entry_legacy, "binary_sensor", "engineState", "engine")

    r = adotta(hass, entry_nostro, dry_run=True)

    assert len(r["adottate"]) == 1
    ancora = registro.async_get(v.entity_id)
    assert ancora is not None and ancora.platform == "omoda_jaecoo", \
        "il dry run ha scritto sul registro"


async def test_le_entita_di_un_altro_veicolo_non_si_toccano(hass, registro, entry_nostro, config_entry_legacy):
    """Due auto sullo stesso Home Assistant: adottare quelle dell'altra sarebbe peggio che
    non adottare niente."""
    from custom_components.omoda9.legacy import adotta

    registro.async_get_or_create(
        "binary_sensor", "omoda_jaecoo", "UNALTROVIN_engineState",
        suggested_object_id="altra_engine", config_entry=config_entry_legacy)

    r = adotta(hass, entry_nostro)

    assert not r["adottate"]
    assert len(r["saltate"]) == 1


async def test_il_servizio_rifiuta_se_la_vecchia_e_ancora_accesa(
        hass, registro, integrazione_avviata, config_entry_legacy):
    """Home Assistant rifiuta di spostare un'entita' gia' montata: "Only entities that
    haven't been loaded can be migrated". Se non lo si dice prima, l'utente vede
    centouno fallimenti di fila e non capisce perche'."""
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.exceptions import HomeAssistantError
    import pytest as _pytest

    from custom_components.omoda9.const import DOMAIN

    _vecchia(registro, config_entry_legacy, "binary_sensor", "engineState", "engine")
    config_entry_legacy.mock_state(hass, ConfigEntryState.LOADED)

    assert hass.services.has_service(DOMAIN, "adopt_legacy_entities"), \
        "il servizio non e' registrato"
    with _pytest.raises(HomeAssistantError, match="ancora attiva"):
        await hass.services.async_call(
            DOMAIN, "adopt_legacy_entities", {"dry_run": True}, blocking=True)

    # e non ha toccato niente
    assert registro.async_get("binary_sensor.engine").platform == "omoda_jaecoo"


# ──────────── recupero dello storico quando la vecchia e' gia' stata cancellata ────────────
# E' l'errore che faranno quasi tutti: "rimuovi la vecchia" e' il primo passo che viene in
# mente, tanto che il documento di migrazione deve scrivere "solo allora" in grassetto.
# A quel punto `adotta` non ha piu' niente da adottare - ma il recorder non e' stato toccato.


def _prese(monkeypatch, serie, cronologie_esistenti=None):
    """Sostituisce le tre prese sul recorder, che nell'ambiente di test non esiste.
    Ritorna le liste su cui si accumulano le chiamate."""
    from custom_components.omoda9 import legacy

    rinominate, cancellate, cronologie = [], [], []

    async def elenco(_hass):
        return set(serie)

    monkeypatch.setattr(legacy, "_serie_esistenti", elenco)
    monkeypatch.setattr(legacy, "_rinomina_statistiche",
                        lambda h, v, n: rinominate.append((v, n)))
    monkeypatch.setattr(legacy, "_cancella_statistiche",
                        lambda h, ids: cancellate.extend(ids))
    monkeypatch.setattr(legacy, "_rinomina_cronologia",
                        lambda h, v, n: cronologie.append((v, n)))

    # La cronologia si interroga e si libera come le statistiche. Se non si dice altro, la
    # vecchia ce l'ha e la nuova no: il caso di chi recupera per la prima volta.
    esistenti = set(serie if cronologie_esistenti is None else cronologie_esistenti)
    liberate = []

    async def ha(_hass, eid):
        return eid in esistenti

    def sposta(_hass, eid):
        liberate.append(eid)
        return f"{eid}_superseded"

    monkeypatch.setattr(legacy, "_ha_cronologia", ha)
    monkeypatch.setattr(legacy, "_sposta_di_lato", sposta)
    return rinominate, cancellate, cronologie, liberate


def _dimenticata(hass, registro, config_entry_legacy, piattaforma, suffisso, object_id):
    v = _vecchia(registro, config_entry_legacy, piattaforma, suffisso, object_id)
    eid = v.entity_id
    registro.async_remove(eid)
    assert registro.async_get(eid) is None
    return eid


async def test_recupera_le_statistiche_di_una_entita_cancellata(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """La vecchia non esiste piu' nel registro, solo in `deleted_entities`. I suoi dati
    esistono ancora, e vanno spostati addosso alla nostra, che il nome giusto ce l'ha."""
    from custom_components.omoda9 import legacy

    vecchio = _dimenticata(hass, registro, config_entry_legacy,
                           "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    rinominate, cancellate, cronologie, liberate = _prese(monkeypatch, [vecchio])

    r = await legacy.recupera_storico(hass, entry_nostro, dry_run=False)

    assert rinominate == [(vecchio, "sensor.chery_connect_odometer")]
    assert cronologie == [(vecchio, "sensor.chery_connect_odometer")]
    assert not cancellate, "non c'era nessuna serie nuova da liberare"


async def test_la_serie_nuova_e_corta_lascia_il_posto_a_quella_lunga(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """Chi ha configurato la nuova prima di accorgersi ha due serie: la sua, di ore, e
    quella vecchia, di anni. Si libera la corta. E' l'unico punto in cui questa funzione
    cancella dei dati, e cancella sempre il lato piu' corto."""
    from custom_components.omoda9 import legacy

    vecchio = _dimenticata(hass, registro, config_entry_legacy,
                           "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    nuovo = "sensor.chery_connect_odometer"
    rinominate, cancellate, _, liberate = _prese(monkeypatch, [vecchio, nuovo])

    await legacy.recupera_storico(hass, entry_nostro, dry_run=False)

    assert cancellate == [nuovo], "la serie corta non e' stata liberata"
    assert rinominate == [(vecchio, nuovo)]


async def test_il_recupero_e_ripetibile(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """Dopo il primo giro la vecchia serie non esiste piu': e' stata rinominata. Un secondo
    giro non deve rifare niente, e soprattutto non deve CANCELLARE la serie appena
    recuperata scambiandola per la gemella corta di turno. Un recupero che si mangia il
    proprio risultato al secondo lancio e' peggio di nessun recupero."""
    from custom_components.omoda9 import legacy

    _dimenticata(hass, registro, config_entry_legacy,
                 "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    rinominate, cancellate, _, liberate = _prese(monkeypatch, ["sensor.chery_connect_odometer"])

    r = await legacy.recupera_storico(hass, entry_nostro, dry_run=False)

    assert not rinominate, "ha rifatto un lavoro gia' fatto"
    assert not cancellate, "ha cancellato la serie che aveva appena recuperato"
    assert not r["statistiche"]


async def test_dry_run_del_recupero_non_scrive(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """Su una funzione che tocca lo storico della gente, far vedere prima e' il minimo."""
    from custom_components.omoda9 import legacy

    vecchio = _dimenticata(hass, registro, config_entry_legacy,
                           "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    rinominate, cancellate, cronologie, liberate = _prese(monkeypatch, [vecchio])

    r = await legacy.recupera_storico(hass, entry_nostro, dry_run=True)

    assert r["statistiche"] == [(vecchio, "sensor.chery_connect_odometer")]
    assert not rinominate and not cancellate and not cronologie, "il dry run ha scritto"


async def test_la_cronologia_libera_il_posto_come_le_statistiche(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """Il difetto del 27 settembre 2026, trovato al primo uso su un'istanza vera.

    Questo ramo non aveva la disciplina di quello delle statistiche: quando il nome di
    destinazione era gia' occupato - cioe' sempre, per chi aveva configurato l'integrazione
    prima di recuperare - il recorder scriveva "Cannot migrate history ... already in use" e
    lasciava tutto com'era. Trenta entita' con le statistiche da luglio e la cronologia da
    quella sera, senza eccezioni e senza un test rosso."""
    from custom_components.omoda9 import legacy

    vecchio = _dimenticata(hass, registro, config_entry_legacy,
                           "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    nuovo = "sensor.chery_connect_odometer"
    # entrambe hanno cronologia: la vecchia lunga, la nuova di poche ore
    _r, _c, cronologie, liberate = _prese(monkeypatch, [vecchio],
                                          cronologie_esistenti=[vecchio, nuovo])

    await legacy.recupera_storico(hass, entry_nostro, dry_run=False)

    assert liberate == [nuovo], "la cronologia corta non e' stata spostata di lato"
    assert cronologie == [(vecchio, nuovo)], "la cronologia non e' stata spostata"


async def test_il_secondo_lancio_non_purga_la_cronologia_appena_recuperata(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    """La guardia che conta davvero su questo ramo.

    Dopo il primo giro la cronologia sta sul nome NUOVO e il vecchio non ha piu' niente.
    Senza la condizione sul vecchio, un secondo lancio vedrebbe il nuovo occupato, lo
    purgherebbe per fare posto, e poi rinominerebbe un'entita' che non ha piu' dati: il
    recupero si mangerebbe il proprio risultato, in silenzio."""
    from custom_components.omoda9 import legacy

    _dimenticata(hass, registro, config_entry_legacy,
                 "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    nuovo = "sensor.chery_connect_odometer"
    # la vecchia non ha piu' niente, la nuova porta lo storico recuperato
    _r, _c, cronologie, liberate = _prese(monkeypatch, [nuovo],
                                          cronologie_esistenti=[nuovo])

    r = await legacy.recupera_storico(hass, entry_nostro, dry_run=False)

    assert not liberate, "ha spostato via la cronologia che aveva appena recuperato"
    assert not cronologie, "ha rifatto un lavoro gia' fatto"
    assert not r["cronologia"]


async def test_il_dry_run_non_purga_e_non_rinomina_la_cronologia(
        hass, registro, entry_nostro, config_entry_legacy, monkeypatch):
    from custom_components.omoda9 import legacy

    vecchio = _dimenticata(hass, registro, config_entry_legacy,
                           "sensor", "rt_odometro", "omoda_jaecoo_odometer")
    nuovo = "sensor.chery_connect_odometer"
    _r, _c, cronologie, liberate = _prese(monkeypatch, [vecchio],
                                          cronologie_esistenti=[vecchio, nuovo])

    r = await legacy.recupera_storico(hass, entry_nostro, dry_run=True)

    assert not liberate and not cronologie, "il dry run ha toccato la cronologia"
    assert r["cronologia"] == [(vecchio, nuovo)], "il dry run non ha riportato cosa farebbe"


def test_il_nome_di_parcheggio_non_collide_con_niente(hass):
    """Lo spostamento di lato inventa un nome, e un nome inventato male e' il modo in cui
    questa funzione potrebbe mangiarsi dei dati al giro dopo. Deve stare fuori da cio' che
    l'integrazione produce, altrimenti un secondo giro lo scambierebbe per un candidato."""
    from custom_components.omoda9 import legacy
    from custom_components.omoda9.legacy import CANON_ENTITY_ID

    visti = []
    legacy._rinomina_cronologia = lambda h, v, n: visti.append((v, n))
    parcheggio = legacy._sposta_di_lato(hass, "sensor.chery_connect_odometer")

    assert parcheggio == "sensor.chery_connect_odometer_superseded"
    assert visti == [("sensor.chery_connect_odometer", parcheggio)]
    assert parcheggio not in set(CANON_ENTITY_ID.values()), \
        "il nome di parcheggio e' un entity_id che l'integrazione produce"
