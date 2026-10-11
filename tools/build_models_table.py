#!/usr/bin/env python3
"""Builds the tested-models table from the reports, so nobody has to keep it by hand.

The point of #9 is in its title: a capability report rather than a hand-kept table. A table
maintained by a person is a table that is accurate on the day it is written. This one is
regenerated from the files, so it is accurate whenever the files are.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
USCITA = RADICE / "docs" / "tested-models.md"


def main() -> int:
    file = sorted((RADICE / "reports").glob("*.json"))
    rapporti = []
    for f in file:
        v = (json.loads(f.read_text(encoding="utf-8")) or {}).get("vehicle") or {}
        rapporti.append((v.get("brand") or "?", v.get("model") or "?",
                         v.get("power_type"), set(v.get("entities") or []), f.name))
    rapporti.sort(key=lambda r: (r[0], r[1]))

    tipo = {0: "BEV", None: "unknown"}
    righe = ["# Tested models",
             "",
             "**Generated from `reports/`. Do not edit by hand** - a table kept by a person",
             "is accurate on the day it is written; run `tools/build_models_table.py` instead.",
             "",
             "How to add your car: download the diagnostics from Home Assistant and open a",
             "pull request putting the file in `reports/`. See `reports/README.md`.",
             ""]
    if not rapporti:
        righe += ["No reports yet.", ""]
    else:
        righe += ["| Brand | Model | Power | Entities | Report |", "|---|---|---|---|---|"]
        for b, m, pt, ent, nome in rapporti:
            righe.append(f"| {b} | {m} | {tipo.get(pt, str(pt))} | {len(ent)} | "
                         f"[`{nome}`](../reports/{nome}) |")
        righe.append("")
        # Cio' che un modello ha e un altro no: e' l'unica parte della tabella che serve a
        # chi scrive codice per un'auto che non possiede.
        if len(rapporti) > 1:
            comuni = set.intersection(*[r[3] for r in rapporti])
            righe += ["## What differs between them", "",
                      f"{len(comuni)} entities appear on every car reported so far. "
                      "These do not:", ""]
            for b, m, pt, ent, nome in rapporti:
                solo = sorted(ent - comuni)
                righe.append(f"**{b} {m}** - {len(solo)} not shared: "
                             + (", ".join(f"`{e.split('.', 1)[1]}`" for e in solo) if solo
                                else "none") + "  ")
            righe.append("")
    USCITA.parent.mkdir(parents=True, exist_ok=True)
    USCITA.write_text("\n".join(righe), encoding="utf-8")
    print(f"{USCITA.relative_to(RADICE)}: {len(rapporti)} reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
