"""Contatori di energia di ricarica casa/fuori: l'aritmetica dell'integrale.

Questi test guardano il PASSO DI CAMPIONAMENTO, non il cablaggio a Home Assistant:
l'entita' viene costruita senza passare dal costruttore, perche' cio' che puo' essere
sbagliato qui e' il trapezio, il rifiuto dei buchi e l'attribuzione alla zona — non
l'istanziazione, che la suite delle entita' copre gia' altrove.

Tre di questi fallivano sulla forma ingenua del codice, quindi sono test di regressione e
non decorazione:
  * `test_buco_lungo_non_inventa_energia`
  * `test_zona_ignota_non_attribuisce_a_nessuno`
  * `test_stato_carica_float_conta_come_in_ricarica`
"""
from __future__ import annotations

import datetime as dt

import pytest

from custom_components.omoda9 import sensor as S
from custom_components.omoda9.const import CHARGE_ENERGY_MAX_GAP


class _CoordFinto:
    def __init__(self, potenza, stato="1", posizione=None):
        self.data = {"realtime": {"chargingPower": potenza, "chargeState": stato},
                     "position": posizione or {"lat": 1.0, "lon": 2.0}}
        self.poll_enabled = True


def _contatore(home=True):
    """Istanza senza costruttore: qui interessa solo lo stato dell'integratore."""
    e = object.__new__(S.Omoda9ChargedEnergy)
    e._home = home
    e._energia_wh = 0.0
    e._ultimo_ts = None
    e._ultima_potenza = 0.0
    e._era_attivo = False
    return e


def _campiona(e, coord, a_casa, istante, monkeypatch):
    monkeypatch.setattr(S, "in_zona_casa", lambda hass, pos: a_casa)
    monkeypatch.setattr(S.dt_util, "utcnow", lambda: istante)
    e.coordinator = coord
    e.hass = None
    e._campiona()


T0 = dt.datetime(2026, 8, 24, 12, 0, 0, tzinfo=dt.timezone.utc)


def test_stato_carica_float_conta_come_in_ricarica():
    """Il canale realtime manda a volte `'1.0'`: un confronto con la stringa `'1'` teneva
    l'integrale fermo a zero senza dirlo."""
    assert S._in_ricarica("1") is True
    assert S._in_ricarica("1.0") is True
    assert S._in_ricarica(1.0) is True
    assert S._in_ricarica("0") is False
    assert S._in_ricarica(None) is False
    assert S._in_ricarica("chi lo sa") is False


def test_trapezio_su_due_campioni_vicini(monkeypatch):
    """2 kW per 120 s = 0,0667 kWh. Il primo campione arma soltanto: non accumula."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
    assert e.native_value == 0.0
    _campiona(e, _CoordFinto("2.0"), True, T0 + dt.timedelta(seconds=120), monkeypatch)
    assert e.native_value == pytest.approx(2.0 * 120 / 3600, abs=1e-3)


def test_buco_lungo_non_inventa_energia(monkeypatch):
    """Oltre CHARGE_ENERGY_MAX_GAP l'auto ha dormito: non si integra attraverso il buco.

    E' anche il difetto noto dei contatori — su cariche AC lente con polling rado
    l'energia vera cade qui dentro e il contatore sottostima. Il comportamento e'
    deliberato finche' non viene corretto a parte: il test lo fissa perche' nessuno lo
    cambi per sbaglio credendolo un bug di battitura."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
    troppo_tardi = T0 + dt.timedelta(seconds=CHARGE_ENERGY_MAX_GAP + 1)
    _campiona(e, _CoordFinto("2.0"), True, troppo_tardi, monkeypatch)
    assert e.native_value == 0.0


def test_zona_ignota_non_attribuisce_a_nessuno(monkeypatch):
    """Senza fix GPS o senza `zone.home` l'energia non finisce nel contatore sbagliato: non finisce da nessuna
    parte. Meglio perdere un campione che attribuirlo alla zona sbagliata."""
    for casa in (True, False):
        e = _contatore(home=casa)
        _campiona(e, _CoordFinto("2.0"), None, T0, monkeypatch)
        _campiona(e, _CoordFinto("2.0"), None, T0 + dt.timedelta(seconds=120), monkeypatch)
        assert e.native_value == 0.0


def test_i_due_contatori_si_dividono_la_carica(monkeypatch):
    """La stessa carica a casa accumula su `home` e lascia `away` a zero."""
    casa, fuori = _contatore(home=True), _contatore(home=False)
    for e in (casa, fuori):
        _campiona(e, _CoordFinto("2.0"), True, T0, monkeypatch)
        _campiona(e, _CoordFinto("2.0"), True, T0 + dt.timedelta(seconds=120), monkeypatch)
    assert casa.native_value > 0
    assert fuori.native_value == 0.0


def test_potenza_zero_non_accumula(monkeypatch):
    """`chargeState` puo' dire "in ricarica" mentre la potenza e' ancora 0: non e' energia."""
    e = _contatore(home=True)
    _campiona(e, _CoordFinto("0"), True, T0, monkeypatch)
    _campiona(e, _CoordFinto("0"), True, T0 + dt.timedelta(seconds=120), monkeypatch)
    assert e.native_value == 0.0
