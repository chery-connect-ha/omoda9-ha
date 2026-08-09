"""Adattamento ai modelli SOLO ELETTRICI, senza toccare il comportamento su Omoda 9.

Il componente nasce su una Omoda 9 PHEV, ma il canale telemetria è lo stesso per tutta la
gamma e le BEV (Omoda E5) mandano un sottoinsieme diverso di campi. L'adattamento c'è, ma
è deliberatamente **timido**: si cambia qualcosa solo quando il backend dichiara
`powerType == 0` in `queryList`. Capability sconosciuta ⇒ tutto come prima.

Questi test bloccano proprio quel confine, perché è il punto in cui una regressione
passerebbe inosservata: basta scrivere `!= 1` invece di `== 0`, o trattare un campo
assente come "benzina finita", per far sparire dei sensori a chi ha la PHEV.
"""
from __future__ import annotations

import pytest

from custom_components.omoda9.const import (
    CLIMA_MAX_DEFAULT,
    CLIMA_MIN_DEFAULT,
    CLIMA_STEP_DEFAULT,
    DATA_CLIMATE_MAX,
    DATA_CLIMATE_MIN,
    DATA_CLIMATE_STEP,
    DATA_POWER_TYPE,
    capabilities_from_item,
)


# ───────────────────────── lettura delle capability da queryList ─────────────────────────
def test_powertype_letto_come_intero():
    """Il backend può mandarlo come stringa o come float: conta il valore, non il tipo."""
    assert capabilities_from_item({"powerType": 0})[DATA_POWER_TYPE] == 0
    assert capabilities_from_item({"powerType": "0"})[DATA_POWER_TYPE] == 0
    assert capabilities_from_item({"powerType": "1.0"})[DATA_POWER_TYPE] == 1


@pytest.mark.parametrize("item", [
    {},                            # campo assente
    {"powerType": None},
    {"powerType": ""},
    {"powerType": "boh"},          # non numerico
])
def test_powertype_assente_o_illeggibile_non_finisce_in_cache(item):
    """Meglio nessuna capability che una capability inventata: chi legge ricade sui default."""
    assert DATA_POWER_TYPE not in capabilities_from_item(item)


def test_range_clima_dichiarato_viene_preso():
    caps = capabilities_from_item(
        {"minTemperature": "18", "maxTemperature": "32", "temperatureStepLength": "0.5"})
    assert caps[DATA_CLIMATE_MIN] == 18.0
    assert caps[DATA_CLIMATE_MAX] == 32.0
    assert caps[DATA_CLIMATE_STEP] == 0.5


@pytest.mark.parametrize("item", [
    {"minTemperature": "30", "maxTemperature": "16"},   # invertiti
    {"minTemperature": "16", "maxTemperature": "16"},   # degenere
    {"minTemperature": "-40", "maxTemperature": "30"},  # fuori scala
    {"minTemperature": "16", "maxTemperature": "99"},   # fuori scala
    {"minTemperature": "x", "maxTemperature": "30"},    # non numerico
    {"maxTemperature": "30"},                           # incompleto
])
def test_range_clima_implausibile_viene_scartato(item):
    """Un range assurdo è un dato sbagliato, non una vettura esotica: si tengono i default."""
    caps = capabilities_from_item(item)
    assert DATA_CLIMATE_MIN not in caps and DATA_CLIMATE_MAX not in caps


def test_step_clima_solo_valori_ammessi():
    assert capabilities_from_item({"temperatureStepLength": "1"})[DATA_CLIMATE_STEP] == 1.0
    assert DATA_CLIMATE_STEP not in capabilities_from_item({"temperatureStepLength": "7"})


def test_item_non_dizionario_non_solleva():
    assert capabilities_from_item(None) == {}          # type: ignore[arg-type]
    assert capabilities_from_item("pippo") == {}       # type: ignore[arg-type]


# ───────────────────────── autonomia: PHEV vs BEV ─────────────────────────
def test_totale_phev_none_se_manca_la_benzina():
    """Il difetto corretto in v1.7.1: un `mileageSurplus` assente per un frame NON deve
    valere zero, altrimenti il totale crolla di ~150 km e ci resta per ore."""
    from custom_components.omoda9.sensor import _range_totale
    assert _range_totale({"pureElectricRange": "60"}) is None
    assert _range_totale({"pureElectricRange": "60", "mileageSurplus": "215"}) == 275.0


def test_totale_bev_e_la_sola_parte_elettrica():
    """Su BEV confermata non c'è serbatoio: il calcolo a due addendi resterebbe None."""
    from custom_components.omoda9.sensor import _range_totale_bev
    assert _range_totale_bev({"pureElectricRange": "310"}) == 310.0
    assert _range_totale_bev({"dynamicPureElectricRange": "287"}) == 287.0


def test_frame_degradato_riconosciuto_con_entrambi_i_nomi():
    """La sentinella «0 km = segnaposto» deve valere anche col nome di campo delle BEV."""
    from custom_components.omoda9.sensor import _frame_batteria_degradato
    assert _frame_batteria_degradato({"pureElectricRange": "0"}) is True
    assert _frame_batteria_degradato({"dynamicPureElectricRange": "0"}) is True
    assert _frame_batteria_degradato({"dynamicPureElectricRange": "287"}) is False
    assert _frame_batteria_degradato({}) is False


# ───────────────────────── fallback multi-nome dei campi ─────────────────────────
class _CoordFinto:
    def __init__(self, rt):
        self.data = {"realtime": rt}


def test_fallback_nomi_vince_il_primo_presente():
    from custom_components.omoda9.sensor import _rt
    assert _rt(_CoordFinto({"pureElectricRange": "60"}), ("pureElectricRange", "alt")) == "60"
    assert _rt(_CoordFinto({"alt": "42"}), ("pureElectricRange", "alt")) == "42"
    assert _rt(_CoordFinto({}), ("pureElectricRange", "alt")) is None


def test_fallback_salta_i_valori_vuoti():
    """Un campo presente ma vuoto non deve "coprire" l'alternativa valorizzata."""
    from custom_components.omoda9.sensor import _rt
    coord = _CoordFinto({"pureElectricRange": "", "alt": "42"})
    assert _rt(coord, ("pureElectricRange", "alt")) == "42"


def test_campo_singolo_resta_una_stringa():
    """La forma storica (un solo nome) non deve cambiare comportamento."""
    from custom_components.omoda9.sensor import _rt
    assert _rt(_CoordFinto({"odometer": "4062"}), "odometer") == "4062"


# ───────────────────────── il confine: si agisce solo su BEV CONFERMATA ─────────────────────────
class _CoordCaps:
    """Il minimo per esercitare `is_pure_electric` / `climate_limits` senza avviare HA."""

    def __init__(self, data: dict):
        self.entry = type("E", (), {"data": data, "options": {}})()

    is_pure_electric = None  # riassegnati sotto dai metodi veri del coordinator


def _coord_con(data: dict):
    from custom_components.omoda9.coordinator import Omoda9Coordinator
    c = _CoordCaps(data)
    c.is_pure_electric = lambda: Omoda9Coordinator.is_pure_electric(c)
    c.climate_limits = lambda: Omoda9Coordinator.climate_limits(c)
    return c


@pytest.mark.parametrize("data,atteso", [
    ({DATA_POWER_TYPE: 0}, True),      # BEV dichiarata
    ({DATA_POWER_TYPE: 1}, False),     # ha un motore termico
    ({DATA_POWER_TYPE: 2}, False),
    ({}, False),                       # capability MAI lette → si assume termico
    ({DATA_POWER_TYPE: None}, False),
    ({DATA_POWER_TYPE: "0"}, False),   # solo l'intero conta: una stringa è un dato sporco
])
def test_is_pure_electric_solo_su_zero_confermato(data, atteso):
    assert _coord_con(data).is_pure_electric() is atteso


def test_limiti_clima_default_quando_il_backend_tace():
    assert _coord_con({}).climate_limits() == (
        CLIMA_MIN_DEFAULT, CLIMA_MAX_DEFAULT, CLIMA_STEP_DEFAULT)


def test_limiti_clima_dalla_vettura_quando_dichiarati():
    dati = {DATA_CLIMATE_MIN: 18.0, DATA_CLIMATE_MAX: 32.0, DATA_CLIMATE_STEP: 0.5}
    assert _coord_con(dati).climate_limits() == (18.0, 32.0, 0.5)


def test_sensori_benzina_spariscono_solo_su_bev_confermata():
    """L'elenco dei sensori realtime non deve cambiare per una capability sconosciuta."""
    from custom_components.omoda9.sensor import _RT_SENSORS, _SENSORI_SOLO_TERMICO

    presenti = {s.suffix for s in _RT_SENSORS}
    # tutti i suffissi dichiarati "solo termico" devono esistere davvero: un refuso li
    # renderebbe una soppressione che non sopprime niente
    assert _SENSORI_SOLO_TERMICO <= presenti

    def elenco(bev: bool):
        return [s.suffix for s in _RT_SENSORS
                if not (bev and s.suffix in _SENSORI_SOLO_TERMICO)]

    assert elenco(False) == [s.suffix for s in _RT_SENSORS]      # PHEV/sconosciuto: invariato
    assert set(elenco(True)) == presenti - _SENSORI_SOLO_TERMICO  # BEV: solo i termici via


def test_sensori_bev_non_esistono_gia_fra_quelli_normali():
    """I campi solo-BEV non devono duplicare un sensore già creato per tutti."""
    from custom_components.omoda9.sensor import _RT_SENSORI_BEV, _RT_SENSORS

    normali = {s.suffix for s in _RT_SENSORS}
    assert not ({s.suffix for s in _RT_SENSORI_BEV} & normali)
