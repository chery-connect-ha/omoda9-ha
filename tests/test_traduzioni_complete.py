"""Le tre lingue devono portare le stesse chiavi.

`strings.json` è la sorgente che Home Assistant usa per generare le traduzioni;
`translations/en.json` e `translations/it.json` sono quelle servite all'utente. Se una
chiave esiste in una e manca in un'altra, l'entità compare **senza nome** — o con la
chiave grezza — soltanto per chi ha quella lingua, e chi sviluppa non se ne accorge
perché la sua è quella completa.

Non è ipotetico: portando i contatori di energia dalla linea fork il 2026-08-24, quella
linea aveva `en.json` e non `it.json`. Copiare senza guardare avrebbe dato tre entità
senza nome a tutti gli utenti italiani.

⚠️ Questo test guarda le CHIAVI, non le TRADUZIONI. Un `name` copiato in inglese dentro
`it.json` lo passa: dice che non hai dimenticato un file, non che hai tradotto.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "custom_components" / "omoda9"
FILES = {
    "strings.json": PKG / "strings.json",
    "translations/en.json": PKG / "translations" / "en.json",
    "translations/it.json": PKG / "translations" / "it.json",
}


def _chiavi(path: Path) -> set[str]:
    """Tutte le chiavi foglia, come percorsi puntati: `entity.sensor.batteria.name`."""
    def cammina(nodo, prefisso=""):
        if isinstance(nodo, dict):
            for k, v in nodo.items():
                yield from cammina(v, f"{prefisso}.{k}" if prefisso else k)
        else:
            yield prefisso

    return set(cammina(json.loads(path.read_text(encoding="utf-8"))))


@pytest.mark.parametrize("nome", [n for n in FILES if n != "strings.json"])
def test_ogni_lingua_ha_le_chiavi_di_strings(nome):
    """`strings.json` è il riferimento: ogni lingua deve coprirlo per intero."""
    rif = _chiavi(FILES["strings.json"])
    lingua = _chiavi(FILES[nome])

    mancanti = sorted(rif - lingua)
    assert not mancanti, (
        f"{nome} non ha {len(mancanti)} chiavi presenti in strings.json — chi usa quella "
        f"lingua vedrà entità senza nome: {mancanti[:12]}"
    )

    in_piu = sorted(lingua - rif)
    assert not in_piu, (
        f"{nome} ha {len(in_piu)} chiavi che strings.json non dichiara: o sono rimaste da "
        f"una rimozione, o vanno aggiunte anche lì: {in_piu[:12]}"
    )


# --------------------------------------------------------------------------------------
# Il test sopra confronta i FILE fra loro. Non basta, e il 2026-09-05 si e' visto perche':
# `_region_fields()` disegnava dieci campi in tutti e tre gli step di login, ma
# `strings.json` ne dichiarava solo sei sotto `login_password`. Quattro campi comparivano
# nel form SENZA etichetta, in tutte le lingue insieme -- quindi i tre file concordavano,
# il test passava, e il difetto era visibile solo aprendo quella schermata.
#
# Non era colpa di nessuna delle due pull request: #16 scrisse `login_password` quando
# `_region_fields()` non aveva ancora `preset`/`tenant_code`/`country_id`, e #19 aggiunse
# quelle chiavi ai due step che sul suo ramo esistevano. Il difetto e' nato dall'incontro.
# Un guardiano che confronta i file fra loro non puo' vedere una cosa del genere: deve
# confrontarli con quello che il form DISEGNA.
# --------------------------------------------------------------------------------------

STEP_CON_CAMPI_DI_REGIONE = ("login_email", "login_phone", "login_password")


def _campi_di_regione() -> set[str]:
    """Le chiavi che `_region_fields()` mette davvero nel form, chieste al codice."""
    from custom_components.omoda9.config_flow import Omoda9ConfigFlow

    # `_region_fields` non tocca `self`: si puo' chiamare senza costruire il flow.
    return {str(marcatore) for marcatore in Omoda9ConfigFlow._region_fields(None)}


@pytest.mark.parametrize("step", STEP_CON_CAMPI_DI_REGIONE)
def test_ogni_campo_disegnato_ha_una_etichetta(step):
    """Ogni campo che il form mostra deve avere un'etichetta in `strings.json`."""
    import json

    strings = json.loads(FILES["strings.json"].read_text(encoding="utf-8"))
    dichiarati = set(strings["config"]["step"][step].get("data", {}))

    senza_etichetta = sorted(_campi_di_regione() - dichiarati)
    assert not senza_etichetta, (
        f"lo step `{step}` disegna {len(senza_etichetta)} campi che strings.json non "
        f"nomina: {senza_etichetta}. Chi apre quella schermata li vede senza etichetta, "
        f"in OGNI lingua -- e il confronto fra i file non se ne accorge, perche' mancano "
        f"a tutti allo stesso modo."
    )
