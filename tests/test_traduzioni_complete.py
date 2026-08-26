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
