"""L'unità dell'autonomia è una proprietà del VEICOLO, non una costante del codice.

Il centralino manda alcune grandezze in due unità come campi fratelli: `mileageSurplus` in
chilometri e `cruiseRange` in miglia (misurato dal vivo su Omoda 9: 209 km ↔ 130). Il
sensore diagnostico dichiarava miglia **per costante**, da due campioni su una sola auto.

⚠️ Non è dimostrato che su un altro modello quel campo sia in chilometri: la misura sul
Jaecoo J7 riguarda `mileageSurplus` (issue #3, e il filo su #7), non questo campo. Questi
test fissano quindi una DIFESA, non la correzione di un difetto osservato — e soprattutto
fissano le tre cose da cui la difesa deve difendersi, perché ognuna, sbagliata, farebbe
danno a chi oggi funziona.
"""
from __future__ import annotations

import pytest

from custom_components.omoda9.sensor import _cruise_range_miglia

MIGLIO_KM = 1.609344
# Frame vero, 2026-08-24. Serve come base a cui togliere un pezzo per volta.
OMODA9 = {"mileageSurplus": "209", "cruiseRange": "130",
          "pureElectricRange": "145", "pureElectricRangeMile": "90"}


# ── il caso che NON deve cambiare ────────────────────────────────────────────────────
def test_omoda9_reale_passa_intatto():
    assert _cruise_range_miglia(OMODA9) == 130.0


@pytest.mark.parametrize("km,mi", [("182", "113"), ("215", "134")])
def test_i_due_campioni_storici_passano_intatti(km, mi):
    """I campioni di giugno e luglio su cui era stata dedotta l'unità: nessuno si muove."""
    assert _cruise_range_miglia({"mileageSurplus": km, "cruiseRange": mi}) == float(mi)


# ── il caso per cui la difesa esiste ─────────────────────────────────────────────────
def test_auto_che_manda_i_km_viene_convertita():
    v = _cruise_range_miglia({"mileageSurplus": "209", "cruiseRange": "209"})
    assert v == pytest.approx(209 / MIGLIO_KM, abs=0.01)
    assert v * MIGLIO_KM == pytest.approx(209, abs=0.01)   # HA riconverte: torna 209 km


# ── LA SOGLIA: l'unico cancello che converte davvero ─────────────────────────────────
# Senza questi quattro, spostare 0,93 a 0,10 o 1,07 a 1,49 non farebbe fallire niente:
# provato con mutazione, quattro mutanti su quattro sopravvivevano.
@pytest.mark.parametrize("rapporto,converte", [
    (0.92, False), (0.93, True), (1.07, True), (1.08, False),
])
def test_i_bordi_della_finestra_di_conversione(rapporto, converte):
    mi = 130.0
    rt = {"cruiseRange": str(mi), "mileageSurplus": str(mi * rapporto)}
    v = _cruise_range_miglia(rt)
    if converte:
        assert v == pytest.approx(mi / MIGLIO_KM, abs=0.01), "dentro la finestra: deve convertire"
    else:
        assert v == mi, "fuori dalla finestra: si tiene il grezzo, non si inventa"


# ── (1) senza ancora si TIENE L'ULTIMO NOTO, non si ripiega sul grezzo ───────────────
def test_senza_ancora_non_si_pubblica_un_numero_possibilmente_falso():
    """Il grezzo qui sarebbe il difetto di ritorno: su un'auto in km 209 diventerebbe
    336,35 km sul quadro di HA, e finirebbe pure nell'ultimo valore noto. `None` lascia in
    piedi l'ultimo numero già giusto. Stesso guasto corretto in v1.7.1 su `_range_totale`."""
    assert _cruise_range_miglia({"cruiseRange": "130"}) is None
    assert _cruise_range_miglia({"cruiseRange": "130", "mileageSurplus": "0"}) is None


def test_un_frame_parziale_non_sporca_la_serie():
    """Sequenza reale: frame pieno, frame senza ancora, frame pieno. In mezzo nessun salto."""
    pieno = _cruise_range_miglia(OMODA9)
    parziale = _cruise_range_miglia({k: v for k, v in OMODA9.items() if k != "mileageSurplus"})
    assert pieno == 130.0
    assert parziale is None          # ⇒ RestoreSensor tiene 130, nessuna spuntata a 336 km
    assert _cruise_range_miglia(OMODA9) == 130.0


# ── (2) e (3) le due guardie ─────────────────────────────────────────────────────────
def test_limite_noto_se_fosse_lautonomia_elettrica_non_ce_ne_accorgeremmo():
    """Documenta un LIMITE, non una difesa — e va letto come tale.

    Se su un modello `cruiseRange` fosse l'autonomia elettrica in chilometri, il rapporto con
    `mileageSurplus` può valere ~1,609 per pura aritmetica e la funzione direbbe «è già in
    miglia». Una guardia dedicata è stata scritta e rimossa perché restituiva lo stesso
    valore del ramo normale (ramo morto) e faceva congelare il sensore sulla nostra auto.
    Questo test fissa il comportamento attuale così che, se un giorno lo si cambia, lo si
    faccia sapendo di cambiarlo."""
    rt = {"mileageSurplus": "209", "cruiseRange": "130", "pureElectricRange": "130"}
    assert _cruise_range_miglia(rt) == 130.0


def test_se_la_coppia_gemella_nega_i_km_non_si_decide():
    """`pureElectricRange`/`pureElectricRangeMile` sono gemelli per NOME: se il loro
    rapporto non è ~1,609, i campi senza suffisso di quest'auto non sono metrici e l'ancora
    non vale."""
    rt = dict(OMODA9, mileageSurplus="130", pureElectricRange="145", pureElectricRangeMile="145")
    assert _cruise_range_miglia(rt) == 130.0


# ── valori degeneri: uno per riga, niente parametrize a maglie larghe ────────────────
def test_zero_resta_zero():
    """⚠️ 0 è un segnaposto che il sensore pubblicava già come 0. Trasformarlo in `None`
    farebbe ricomparire l'ultimo valore noto al posto di uno zero vero."""
    assert _cruise_range_miglia({"cruiseRange": "0", "mileageSurplus": "209"}) == 0.0


def test_campo_assente_e_none():
    assert _cruise_range_miglia({}) is None


def test_campo_non_numerico_e_none():
    assert _cruise_range_miglia({"cruiseRange": "abc", "mileageSurplus": "209"}) is None
