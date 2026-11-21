"""Il validatore dei rapporti dei veicoli.

Il controllo che conta e' il primo, e non riguarda la qualita' del dato: riguarda la persona
che ha caricato il file. Un rapporto e' un file committato in un repository pubblico, quindi
resta nella storia di git; una diagnostica sfuggita non redatta non si ritira cancellandola.
Questi test esistono perche' quel controllo non deve poter smettere di funzionare in
silenzio.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE / "tools"))


def _valida(tmp_path, dati, testo=None):
    import validate_report
    f = tmp_path / "rapporto.json"
    f.write_text(testo if testo is not None else json.dumps(dati), encoding="utf-8")
    return validate_report.valida(f)


def _buono():
    from custom_components.omoda9.legacy import CANON_ENTITY_ID
    ent = sorted(CANON_ENTITY_ID.values())[:12]
    return {"vehicle": {"brand": "Omoda", "model": "Omoda 5Ev", "power_type": 0,
                        "entity_count": len(ent), "entities": ent}}


def test_un_rapporto_sano_passa(tmp_path):
    assert _valida(tmp_path, _buono()) == []


@pytest.mark.parametrize("veleno,atteso", [
    ('"vin": "LNNABDCX3TD024097"', "VIN"),
    ('"email": "qualcuno@esempio.it"', "e-mail"),
    ('"lat": 45.1', "coordinate"),
    ('"access_token": "abcdefghijklmnop"', "token"),
])
def test_niente_dati_personali(tmp_path, veleno, atteso):
    """Il controllo che protegge chi ha caricato il file. Se uno solo di questi passasse,
    il dato sarebbe pubblico e permanente prima che qualcuno se ne accorga."""
    d = _buono()
    testo = json.dumps(d)[:-1] + "," + veleno + "}"
    problemi = _valida(tmp_path, None, testo=testo)
    assert any(atteso in p for p in problemi), f"{veleno} non e' stato intercettato: {problemi}"


def test_una_bev_con_i_sensori_del_termico_non_passa(tmp_path):
    """La regola del domain model. Se il file dichiara entrambe le cose una delle due e'
    falsa, e quale delle due e' esattamente cio' che questa raccolta serve a scoprire:
    quindi si apre una issue, non si corregge il file."""
    from custom_components.omoda9.legacy import CANON_ENTITY_ID
    benzina = CANON_ENTITY_ID[("sensor", "rt_range_benzina")]
    d = _buono()
    d["vehicle"]["entities"] = sorted(set(d["vehicle"]["entities"]) | {benzina})
    d["vehicle"]["entity_count"] = len(d["vehicle"]["entities"])
    problemi = _valida(tmp_path, d)
    assert any("termico" in p for p in problemi), problemi


def test_un_entity_id_sconosciuto_non_passa(tmp_path):
    """Puo' voler dire una versione diversa oppure un file ritoccato a mano. Due cose da
    capire prima di metterle in tabella, non da ignorare."""
    d = _buono()
    d["vehicle"]["entities"] = d["vehicle"]["entities"] + ["sensor.inventato_di_sana_pianta"]
    d["vehicle"]["entity_count"] = len(d["vehicle"]["entities"])
    problemi = _valida(tmp_path, d)
    assert any("non sa produrre" in p for p in problemi), problemi


def test_il_conteggio_che_non_torna_non_passa(tmp_path):
    """Banale, e per questo il primo segno di un file modificato a mano."""
    d = _buono()
    d["vehicle"]["entity_count"] = 999
    assert any("elenca" in p for p in _valida(tmp_path, d))


def test_senza_marca_o_modello_non_passa(tmp_path):
    for campo in ("brand", "model"):
        d = _buono()
        d["vehicle"][campo] = ""
        assert any(campo in p for p in _valida(tmp_path, d)), campo


def test_una_diagnostica_di_una_versione_vecchia_lo_dice(tmp_path):
    """Senza la sezione `vehicle` non e' un rapporto: e' una diagnostica di prima che
    esistesse. Il messaggio deve dire quale versione serve, o la persona riprova con lo
    stesso file."""
    problemi = _valida(tmp_path, {"entry": {"version": 1}})
    assert any("beta.10" in p for p in problemi), problemi


def test_la_tabella_generata_e_allineata_ai_rapporti():
    """La tabella non si tiene a mano - e' il titolo della #9. Questo test e' la ragione per
    cui non ricomincera' a essere tenuta a mano senza che nessuno lo noti."""
    import subprocess
    prima = (RADICE / "docs" / "tested-models.md")
    vecchio = prima.read_text(encoding="utf-8") if prima.exists() else None
    subprocess.run([sys.executable, str(RADICE / "tools" / "build_models_table.py")],
                   check=True, capture_output=True)
    assert prima.read_text(encoding="utf-8") == vecchio, \
        "docs/tested-models.md non e' allineata: lancia tools/build_models_table.py"


def test_un_vin_nel_nome_del_file_non_passa(tmp_path):
    """Il controllo sul contenuto da solo e' monco, e lo ha notato un tester prima che
    costasse a qualcuno: la diagnostica redige cio' che sta DENTRO il file, e nessuno guarda
    come si chiama. Il nome di un file committato sta nella storia di git esattamente come
    il suo contenuto."""
    import validate_report
    f = tmp_path / "omoda9-LNNABDCX3TD024097-report.json"
    f.write_text(json.dumps(_buono()), encoding="utf-8")
    problemi = validate_report.valida(f)
    assert any("NOME del file" in p for p in problemi), problemi


def test_un_nome_di_file_pulito_passa(tmp_path):
    import validate_report
    f = tmp_path / "omoda-omoda-5-ev-it.json"
    f.write_text(json.dumps(_buono()), encoding="utf-8")
    assert validate_report.valida(f) == []
