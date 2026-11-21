"""
omoda.py — client per l'API telematica OMODA/JAECOO (backend "legend", Chery/LionAI).

Modulo condiviso: costanti d'ambiente PRODUZIONE EU, helper di firma (ancora da
confermare), e funzioni di basso livello per le chiamate REST.

Tutto deriva da OMODA9_HANDOFF.md (reverse engineering statico dell'APK 1.1.9).
NB: la firma delle richieste (timestamp/nonce/sign) NON e' ancora confermata —
le ipotesi vivono in `firma_ipotesi_*` e si scelgono iterando sugli errori del
server (vedi probe.py).

Uso strettamente personale, sul proprio veicolo e account.
"""

import os
import time
import uuid
import hashlib
import hmac
import json

import requests


# ─────────────────────────────────────────────────────────────────────────────
# Costanti d'ambiente — PRODUZIONE EU (da assets/flutter_assets/env/.env.prod)
# ─────────────────────────────────────────────────────────────────────────────
BFF = os.environ.get("OMODA_BFF", "https://legend-oj.omodaauto.nl/api")  # backend REST (default EU)
H5 = os.environ.get("OMODA_H5", "https://legend-oj.omodaauto.nl/h5")

# Auth CLIENT dell'app (NON le credenziali utente): base64 di "legendApp:legendApp"
APP_BASIC = "Basic bGVnZW5kQXBwOmxlZ2VuZEFwcA=="

TENANT_CODE = os.environ.get("OMODA_TENANT_CODE", "300006")   # tenant istanza (default EU)
CHANNEL_ID = os.environ.get("CHANNEL_ID", "1")
COUNTRY_ID = os.environ.get("OMODA_COUNTRY_ID", "1")          # 1 = UE
APP_VERSION = "1.1.9"
APP_VERSION_CODE = "26060602"

# Ambienti alternativi (cross-check se la prod fa i capricci) — vedi handoff §3
BFF_SIT = "https://api-app-stg-eu-oj.lionaitech.com/api"
BFF_UAT = "https://legend-oj-uat.omodaauto.nl/api"

# ─────────────────────────────────────────────────────────────────────────────
# Endpoint REST (path relativi a BFF = host + "/api"). Vedi FINDINGS.md.
# ─────────────────────────────────────────────────────────────────────────────
EP_LOGIN = "auth/oauth2/token"               # ✅ no firma, vuole OTP (campo "code")
EP_LOGOUT = "auth/token/logout"
EP_SEND_SMS = "marketing/v2/app/code/sendSmsCode"   # ⚠️ dietro WAF Aliyun (405 a tentativi)
EP_SEND_MAIL = "marketing/v2/app/code/sendMailCode"
EP_IS_REGISTER = "marketing/v1/app/user/isRegister"  # richiede Bearer
EP_TSP_LOGIN = "tsp/v1/app/auth/login"       # Stadio 2 telematica
EP_TSP_TUSERID = "tsp/v1/app/auth/getTuserId"
EP_VMC_LIST = "tsp/v1/app/vmc/queryList"     # ⭐ elenco veicoli (VIN)
EP_VMC_ATTRS = "tsp/v1/app/vmc/queryAttributes"  # ⭐⭐ stato/telemetria

# Candidate a secretKey / chiave di cifratura, estratte dal binario (handoff §6)
AES_KEY_HEX = "d6031998d1b3bbfebf59cc9bbff9aee1"
EC_PUBKEY_HEX = (
    "0418de98b02db9a306f2afcd7235f72a819b80ab12ebd653172476fecd462aab"
    "ffc4ff191b946a5f54d8d0aa2f418808cc25ab056962d30651a114afd2755ad3"
    "36747f93475b7a1fca3b88f2b6a208ccfe469408584dc2b2912675bf5b9e582928"
)


# ─────────────────────────────────────────────────────────────────────────────
# Ipotesi di firma (handoff §6) — da confermare iterando sugli errori del server.
# Ogni funzione prende il dict di parametri da firmare + la secretKey e ritorna
# la stringa `sign`. Si prova un'ipotesi alla volta finche' il server smette di
# lamentarsi di "sign mancante/errata".
# ─────────────────────────────────────────────────────────────────────────────
def _params_ordinati(params):
    """k=v concatenati con & in ordine alfabetico di chiave (pattern cinese tipico)."""
    return "&".join(f"{k}={params[k]}" for k in sorted(params))


def firma_ipotesi_1(params, secret):
    """MD5(parametri_ordinati + "&key=" + secret), hex maiuscolo."""
    s = _params_ordinati(params) + "&key=" + secret
    return hashlib.md5(s.encode()).hexdigest().upper()


def firma_ipotesi_2(params, secret):
    """HMAC-SHA256(parametri_ordinati, secret), hex minuscolo."""
    s = _params_ordinati(params)
    return hmac.new(secret.encode(), s.encode(), hashlib.sha256).hexdigest()


def firma_ipotesi_3(params, secret, app_id="legendApp"):
    """MD5(appId + timestamp + nonce + secret), hex maiuscolo."""
    s = f"{app_id}{params.get('timestamp','')}{params.get('nonce','')}{secret}"
    return hashlib.md5(s.encode()).hexdigest().upper()


# ─────────────────────────────────────────────────────────────────────────────
# Helper richieste
# ─────────────────────────────────────────────────────────────────────────────
def nuovo_timestamp():
    return str(int(time.time() * 1000))


def nuovo_nonce():
    return uuid.uuid4().hex


def header_base(extra=None):
    """Header comuni a tutte le chiamate BFF. `extra` sovrascrive/aggiunge."""
    h = {
        "Authorization": APP_BASIC,
        "tenant": TENANT_CODE,          # nome header da verificare
        "channelId": CHANNEL_ID,
        "countryId": COUNTRY_ID,
        "appversion": APP_VERSION,
        "timestamp": nuovo_timestamp(),
        "nonce": nuovo_nonce(),
        "User-Agent": "okhttp/4.9.0",   # tipico client Android/Flutter
    }
    if extra:
        h.update(extra)
    return h


def stampa_risposta(r):
    """Dump leggibile della risposta — da incollare per iterare sulla firma."""
    print(f"→ {r.request.method} {r.url}")
    print(f"  HTTP {r.status_code}  content-type={r.headers.get('content-type')}")
    body = r.text
    try:
        body = json.dumps(r.json(), ensure_ascii=False, indent=2)
    except Exception:
        pass
    print("  body:")
    for line in body.splitlines() or [body]:
        print("    " + line)
    print()
    return r
