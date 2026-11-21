"""Auto-provisioning dei certificati mutual-TLS MQTT (broker EMQX dell'auto).

I certificati client EMQX sono **costanti universali per-regione** (`Subject: CN=client`),
**NON** dati per-account: sono identici per tutti gli utenti di una regione. Provengono
verbatim dagli asset **PUBBLICI** dell'APK ufficiale (`assets/tspemqx-app-<host>_*`), dove
sono offuscati con un cifrario di flusso a keystream fisso e deobfuscati a runtime da
`libapp.so`. Qui sono bundlati nella stessa forma cifrata + il keystream (vedi
`certs/store.json`) e deobfuscati al setup. Nessun dato per-utente viene spedito.

L'isolamento tra account avviene via username/password MQTT (clientId + md5) e ACL sui
topic, NON tramite il certificato → un singolo cert condiviso è il modello dell'app stessa.
"""
from __future__ import annotations

import base64
import json
import os

_STORE = os.path.join(os.path.dirname(__file__), "certs", "store.json")
_REQUIRED = ("ca.pem", "client.pem", "client.key")


def _load() -> dict:
    with open(_STORE, encoding="utf-8") as f:
        return json.load(f)


def available_regions() -> list[str]:
    """Host MQTT (regioni) per cui esiste un set di cert bundlato."""
    try:
        return sorted(_load().get("regions", {}))
    except Exception:
        return []


def decrypt_region(host: str) -> dict[str, bytes] | None:
    """Ritorna {'ca.pem','client.pem','client.key': bytes} per il broker `host`, o None.

    Deobfusca gli asset (XOR col keystream fisso, length-preserving) — identico a ciò
    che fa `libapp.so` quando carica gli stessi asset dall'APK."""
    try:
        store = _load()
        reg = store.get("regions", {}).get(host)
        if not reg:
            return None
        ks = base64.b64decode(store["ks"])
        out: dict[str, bytes] = {}
        for name in _REQUIRED:
            b64 = reg.get(name)
            if not b64:
                return None
            ct = base64.b64decode(b64)
            if len(ct) > len(ks):
                return None
            out[name] = bytes(c ^ ks[i] for i, c in enumerate(ct))
        return out
    except Exception:
        return None
