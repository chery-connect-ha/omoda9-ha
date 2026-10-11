#!/usr/bin/env python3
"""Validates a vehicle report before it is allowed into the repository.

Why this runs in CI and not in somebody's head. A report is a file committed to a public
repository, which means it is in the git history for good: a diagnostics file that slipped
through unredacted cannot be taken back by deleting it, only by rebuilding the repository
from a cleaned tree, and whoever already cloned still has it. So the check that protects
the person who contributed the file has to run before the merge, every time, without
anybody remembering to look.

The checks are in order of what it costs to get them wrong.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

# Identificativi che NON devono mai comparire in un rapporto pubblicato. La diagnostica li
# redige gia' alla sorgente; questo e' il controllo che non si fida di quella promessa.
VIN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
COORD = re.compile(r'"(?:lat|lon|latitude|longitude)"\s*:\s*-?\d')
TOKEN = re.compile(r'"(?:access_token|refresh_token|userToken|token)"\s*:\s*"[^"]{8,}')

# Sensori che parlano del motore termico. Su una BEV confermata l'integrazione non li crea
# affatto, quindi trovarli accanto a `power_type: 0` vuol dire che una delle due cose e'
# falsa - e sapere quale e' precisamente il motivo per cui questa tabella esiste.
SUFFISSI_SOLO_TERMICO = (
    "rt_range_benzina", "rt_range_combinato", "rt_consumo_carburante",
    "rt_carburante_residuo", "rt_km_ibrido",
)


def _id_noti() -> set[str]:
    """Gli entity_id che questa integrazione sa produrre, dalla sua stessa tabella."""
    from custom_components.omoda9.legacy import CANON_ENTITY_ID
    return set(CANON_ENTITY_ID.values())


def _id_solo_termico() -> set[str]:
    from custom_components.omoda9.legacy import CANON_ENTITY_ID
    return {CANON_ENTITY_ID[("sensor", s)] for s in SUFFISSI_SOLO_TERMICO
            if ("sensor", s) in CANON_ENTITY_ID}


def valida(percorso: Path) -> list[str]:
    """Ritorna l'elenco dei problemi. Vuoto = il rapporto passa."""
    problemi: list[str] = []

    # 0. IL NOME DEL FILE. Il controllo sul contenuto da solo e' monco, e ce lo ha fatto
    # notare un tester prima che costasse a qualcuno: la diagnostica redige quello che c'e'
    # DENTRO, e nessuno guarda come si chiama il file. Chi lo rinomina a mano - o una
    # versione di Home Assistant che componga il nome diversamente - puo' scriverci un VIN
    # accanto a un contenuto perfettamente pulito. E il nome di un file committato sta nella
    # storia di git esattamente come il suo contenuto.
    if VIN.search(percorso.name) or EMAIL.search(percorso.name):
        problemi.append(
            f"ha un identificativo nel NOME del file ({percorso.name}). Il contenuto puo' "
            "essere pulito e il nome no: rinominalo come dice reports/README.md, "
            "`<marca>-<modello>-<regione>.json`.")

    testo = percorso.read_text(encoding="utf-8")

    # 1. Anti-fuga. Prima di tutto il resto: protegge chi ha caricato il file.
    for nome, pattern in (("un VIN", VIN), ("un indirizzo e-mail", EMAIL),
                          ("delle coordinate", COORD), ("un token", TOKEN)):
        if pattern.search(testo):
            problemi.append(
                f"contiene {nome}. Un file committato resta nella storia di git: "
                "non va corretto qui, va rigenerato dalla diagnostica di una versione "
                "che redige, e questo non va mergiato.")

    try:
        d = json.loads(testo)
    except json.JSONDecodeError as err:
        return problemi + [f"non e' JSON valido: {err}"]

    # Home Assistant INCAPSULA la diagnostica dell'integrazione sotto `data`, insieme alla
    # sua (versione di HA, manifest, tempi di avvio). Il file che l'utente scarica e' quello
    # incapsulato; quello che l'integrazione produce e' il contenuto. Si accettano entrambe
    # le forme, perche' un rapporto puo' arrivare gia' estratto - e perche' cercare solo la
    # radice ha respinto il primo rapporto vero dicendo che serviva una versione piu' nuova,
    # che era falso e mandava la persona a rifare una cosa fatta bene.
    v = d.get("vehicle")
    if not isinstance(v, dict) and isinstance(d.get("data"), dict):
        v = d["data"].get("vehicle")
    if not isinstance(v, dict):
        return problemi + [
            "non ha la sezione `vehicle`. Serve una diagnostica di v1.14.0-beta.10 o "
            "successiva: le versioni precedenti non riportano il veicolo."]

    # 2. Il vincolo del domain model: BEV confermata e sensori del termico si escludono.
    entita = v.get("entities") or []
    if v.get("power_type") == 0:
        termici = sorted(set(entita) & _id_solo_termico())
        if termici:
            problemi.append(
                f"dichiara `power_type: 0` (solo elettrica) e ha sensori del motore "
                f"termico: {', '.join(termici)}. Una delle due cose e' falsa, e quale "
                "delle due e' esattamente cio' che questa tabella serve a sapere: "
                "apri una issue invece di correggere il file.")

    # 3. entity_id che l'integrazione non sa produrre.
    noti = _id_noti()
    ignoti = sorted(set(entita) - noti)
    if ignoti:
        problemi.append(
            f"contiene {len(ignoti)} entity_id che questa versione non sa produrre "
            f"(es. {', '.join(ignoti[:4])}). Puo' voler dire una versione diversa, "
            "oppure un file modificato a mano: va capito prima di metterlo in tabella.")

    # 4. Coerenza interna. Banale, e per questo il primo segno di un file ritoccato.
    if v.get("entity_count") is not None and v.get("entity_count") != len(entita):
        problemi.append(
            f"dice `entity_count: {v.get('entity_count')}` ed elenca {len(entita)} entita'.")
    for campo in ("brand", "model"):
        if not (v.get(campo) or "").strip():
            problemi.append(f"ha `{campo}` vuoto: senza quello il rapporto non sta in tabella.")
    if not entita:
        problemi.append("non elenca nessuna entita'.")

    return problemi


def main(argv: list[str]) -> int:
    file = [Path(a) for a in argv[1:]] or sorted((RADICE / "reports").glob("*.json"))
    file = [f for f in file if f.name != "README.md"]
    if not file:
        print("nessun rapporto da validare.")
        return 0
    rotti = 0
    for f in file:
        problemi = valida(f)
        # Path relativa quando si puo', assoluta quando no: questo script si usa anche a
        # mano su un file appena scaricato, fuori dal repository, ed e' proprio il momento
        # in cui serve di piu'. Prima esplodeva li', mentre stampava un problema - cioe'
        # nascondeva il problema che aveva appena trovato.
        try:
            dove = f.relative_to(RADICE)
        except ValueError:
            dove = f
        if problemi:
            rotti += 1
            print(f"::error file={dove}::{f.name}: " + problemi[0])
            for p in problemi:
                print(f"  - {p}")
        else:
            print(f"ok  {dove}")
    return 1 if rotti else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
