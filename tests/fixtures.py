"""Fixture ANONIMIZZATE del protocollo (P2-8/C3) — golden file versionati.

La conoscenza del protocollo Omoda viveva sparsa in note di sessione: qui diventa
materiale verificabile e diff-abile quando il backend cambia. Due famiglie:

  * **codici `A00xxx`** = risposte del backend tspconsole/BFF, con il significato e
    soprattutto il RIMEDIO atteso (`reason`). È la tabella su cui P2-5 costruirà il
    routing unico: i test qui sotto la bloccano PRIMA del refactor, così il refactor
    non può cambiare in silenzio come viene classificato un codice.
  * **envelope MQTT** `5A02` (telemetria), `1301` (posizione), `110x` (conferma comando),
    ricostruiti 1:1 nella forma reale ma con valori sintetici.

⚠️ Nessun dato reale. VIN/email/token/taskId hanno il FORMATO dei veri (il codice li
tratta per forma: lunghezza, prefisso, tipo) ma non appartengono a nessun account. Sono
scelti anche per non far scattare `check_secrets.sh` — vedi il marcatore sul VIN.
"""
from __future__ import annotations

import json

# ───────────────────────── identità sintetiche ─────────────────────────
VIN = "LZZAAAAAA1B2C3D4E"          # VIN_PLACEHOLDER: sintetico, non è un VIN reale
EMAIL = "mario.rossi@example.com"
# Il prefisso 300 NON è assegnato a nessun operatore mobile italiano (i cellulari veri
# stanno in 31x-39x) → ha la forma giusta ma non può essere di nessuno. ⚠️ Il marcatore
# va sulla RIGA del valore, non nel commento: l'allowlist di `check_secrets.sh` filtra
# per riga (stessa trappola già vista col VIN).
PHONE = "3001234567"               # PHONE_PLACEHOLDER: sintetico, non è di nessuno
AREA_CODE = "39"
PIN = "4917"
TUSERID = "100000000000000001"
ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.c2lnbmF0dXJlX2ZpbnRh"
USER_TOKEN = "ut_0123456789abcdef0123456789abcdef"
TASKID = "a1b2c3d4e5f60718293a4b5c6d7e8f90"
TSP_HOST = "https://tspconsole.example.invalid"
BFF = "https://bff.example.invalid/api"


def token_json() -> str:
    """token.json nella forma reale ({data:{...}}), con valori finti."""
    return json.dumps({"data": {"access_token": ACCESS_TOKEN,
                                "refresh_token": "rt_finto_0123456789abcdef",
                                "expires_in": 43200}})


# ───────────────────────── codici backend → rimedio atteso ─────────────────────────
# `reason` è ciò che il coordinator usa per instradare il rimedio all'utente:
#   "pin"    → Repair «PIN comandi errato» (riconfigura il PIN)
#   "reauth" → riautenticazione nativa HA (nuovo OTP)
#   "config" → nessun rimedio automatico, solo avviso (permessi/richiesta malformata)
#   None     → rifiuto dell'auto (occupata / non consentito / a riposo): solo avviso
#
# `counts_lockout` = se quel codice deve incrementare l'anti-lockout del PIN. È il campo
# che più conta: un `True` di troppo qui significa avvicinare il blocco dell'ACCOUNT REALE
# per un errore che col PIN non c'entra nulla (è il bug P1-2, chiuso in v1.5.27).
CHECKPASSWORD_CODES = {
    # — sessione morta: serve un OTP nuovo, il PIN è irrilevante —
    "A00000": {"reason": "reauth", "counts_lockout": False,
               "note": "token/sessione scaduti"},
    # — non è il PIN: permessi veicolo o richiesta costruita male —
    "A00374": {"reason": "config", "counts_lockout": False, "note": "permessi veicolo"},
    # A00084: stessa famiglia di A00374/A00554. Senza `reason` cadeva sul ramo di default e
    # l'utente leggeva «PIN rifiutato — riconfiguralo» per un problema di permessi (issue #1).
    "A00084": {"reason": "config", "counts_lockout": False,
               "note": "funzione non autorizzata sul veicolo"},
    "A00554": {"reason": "config", "counts_lockout": False, "note": "autorizzazione veicolo"},
    "A00567": {"reason": "config", "counts_lockout": False, "note": "taskId non valido"},
    "A00604": {"reason": "config", "counts_lockout": False, "note": "clientType mancante/errato"},
    "A00643": {"reason": "config", "counts_lockout": False, "note": "taskId assente"},
    "A00757": {"reason": "config", "counts_lockout": False, "note": "richiesta malformata"},
    # — davvero il PIN (default conservativo voluto: anche i codici ignoti finiscono qui) —
    "A00285": {"reason": "pin", "counts_lockout": True, "note": "password/PIN errato"},
    "A00282": {"reason": "pin", "counts_lockout": True, "note": "password/PIN errato"},
    "A99999": {"reason": "pin", "counts_lockout": True, "note": "codice SCONOSCIUTO → ramo PIN"},
}

# Esito dell'invio comando (`commands.send`): il backend risponde SEMPRE HTTP 200 e
# l'esito vero sta nel `code` del body.
COMMAND_CODES = {
    "000000": {"ok": True,  "reason": None, "retryable": False, "note": "accettato"},
    "A00079": {"ok": True,  "reason": None, "retryable": False, "note": "accettato dall'auto"},
    "A00082": {"ok": False, "reason": None, "retryable": True,
               "note": "veicolo OCCUPATO (un comando alla volta) → ritentabile"},
    "A00084": {"ok": False, "reason": "config", "retryable": False,
               "note": "funzione non autorizzata dal costruttore su questo veicolo"},
    "A00089": {"ok": False, "reason": None, "retryable": False, "note": "taskId non valido"},
    "A00546": {"ok": False, "reason": None, "retryable": False, "note": "taskId non valido"},
    "A00567": {"ok": False, "reason": None, "retryable": False, "note": "taskId non valido"},
    "A00000": {"ok": False, "reason": "reauth", "retryable": False, "note": "token scaduto"},
    "A07312": {"ok": False, "reason": None, "retryable": False, "note": "rate-limit sveglia"},
    "A07900": {"ok": False, "reason": None, "retryable": False, "note": "auto a riposo"},
}

# taskId rifiutato → si riconia e si riprova UNA volta (poi si arrende)
TASKID_INVALID_CODES = ("A00089", "A00546", "A00567")


# ───────────────────────── envelope MQTT ─────────────────────────
def envelope(service_type: str, data: dict) -> dict:
    """Involucro reale dei push dell'auto: {content:{serviceType, data:{...}}}."""
    return {"content": {"serviceType": service_type, "vin": VIN, "data": data}}


def telemetry_5a02(**overrides) -> dict:
    """Telemetria di stato 5A02 — il push più frequente (porte/clima/sedili/ricarica).

    I valori sono STRINGHE, come li manda l'auto: il mapping in HA li normalizza. Il
    campo `time` e i meta di conferma non devono finire fra i `fields` (vedi test)."""
    data = {
        "frontLeftDoor": "0", "frontRightDoor": "0",
        "backLeftDoor": "0", "backRightDoor": "0",
        "trunkDoor": "0", "hood": "0",
        "doorLock": "0",                 # 0 = Bloccata (verificato dal vivo 2026-06-17)
        "frontLeftWindowState": "0", "frontRightWindowState": "0",
        "backLeftWindowState": "0", "backRightWindowState": "0",
        "sunroofState": "0", "frontHVACState": "0",
        "chargeGunState": "0", "engineState": "0",
        "dSeatHeatingState": "0", "pSeatHeatingState": "0",
        "steerWheelHeating": "0", "rWinHeatingState": "0",
        # flag di UNITÀ, non valori: valgono sempre "1" e NON vanno mappati a sensori
        "rangeUnit": "1", "averageFuelUnit": "1", "tirePressureUnit": "1",
        "time": "1721390000000",
    }
    data.update({k: str(v) for k, v in overrides.items()})
    return envelope("5A02", data)


def position_1301(lat: float = 45.070312, lon: float = 7.686856) -> dict:
    """Push posizione: arriva SOLO in risposta al comando `vehicleLocation`."""
    return envelope("1301", {"lat": str(lat), "lon": str(lon),
                             "direction": "180", "gpsTime": "1721390000000"})


def cmd_confirm(service_type: str = "1105", result: str = "1",
                reason: list | None = None) -> dict:
    """Conferma comando dall'AUTO (diversa dall'«accettato» del backend).

    `result` 1/2 = eseguito, 5 = in corso (asincrono); `reason` valorizzato = fallito."""
    data = {"result": result, "resultTime": "1721390001000", "seq": f"{VIN}-1721390000"}
    if reason is not None:
        data["reason"] = reason
    if result == "5":
        data["hasAsy"] = "1"
    # una conferma porta ANCHE campi di stato reali: devono entrare nei fields
    data["doorLock"] = "1"
    return envelope(service_type, data)


# risposta realtime (/asr/manager/realtime) ad auto FERMA: segnaposto, non dati veri.
REALTIME_PLACEHOLDER = {
    "code": "000000",
    "body": {"dumpEnergy": "0", "totalVoltage": "0", "totalCurrent": "-1000",
             "averageEnergyConsumption": "-100", "hVoltageState": "0",
             "engineState": "0", "odometer": "12345", "resultTime": "1721390000000"},
}

# realtime con l'alta tensione ACCESA: qui i valori sono reali (marcia/ricarica)
REALTIME_LIVE = {
    "code": "000000",
    "body": {"dumpEnergy": "72", "totalVoltage": "384", "totalCurrent": "35",
             "averageEnergyConsumption": "17", "hVoltageState": "1",
             "engineState": "1", "odometer": "12420", "vehicleSpeed": "38",
             "lat": "45.070312", "lon": "7.686856", "resultTime": "1721390600000"},
}

# auto a riposo: il cloud non ha un frame da restituire
REALTIME_ASLEEP = {"code": "A07900"}


# ───────────────────── profilo permessi di un veicolo NON nostro ─────────────────────
# Jaecoo 7 PHEV, account EU — mappa `id → state` estratta con uno script dalla lista permessi
# REALE che l'utente dell'issue #1 ha pubblicato il 2026-08-10 (280 voci, 126 negate).
#
# Perché sta qui e non come JSON committato: il file grezzo arriva da un terzo e il gate
# `check_secrets.sh` scansiona tutta la history. Qui restano i soli numeri — nessun VIN, nessun
# `tUserId`, nessun identificativo (verificato sul contenuto). I `name` sono deliberatamente
# esclusi: il backend li localizza (quella lista torna in tedesco) e **nessuna logica del
# componente deve mai guardarli**.
#
# Sono omesse le 98 voci FIGLIE del ramo 1 (stato veicolo, `parentId` 101): verificate tutte a 1,
# e nessun comando le tocca. Restano le altre 182 — i comandi dei rami 2/3/4 più le cinque radici,
# fra cui il 101 stesso — che sono quelle che decidono.
# Fonte grezza: la lista permessi letta su un Jaecoo 7 PHEV EU (canale privato, mai in questo repo).
JAECOO7_PHEV_EU = {
    1: 1, 2: 1, 3: 1, 4: 1, 101: 1, 201: 0, 202: 1, 203: 1,
    204: 1, 205: 1, 206: 1, 207: 1, 208: 1, 209: 1, 210: 0, 211: 1,
    212: 1, 213: 1, 214: 0, 215: 1, 216: 0, 220: 0, 222: 0, 230: 0,
    231: 0, 232: 0, 233: 0, 234: 0, 235: 0, 236: 0, 237: 0, 301: 1,
    401: 1, 2011: 0, 2012: 0, 2013: 0, 2021: 1, 2022: 0, 2031: 1, 2032: 0,
    2033: 1, 2041: 1, 2042: 1, 2043: 1, 2044: 0, 2045: 1, 2046: 1, 2047: 1,
    2048: 1, 2049: 1, 2051: 1, 2052: 1, 2061: 1, 2062: 1, 2063: 1, 2071: 1,
    2072: 1, 2073: 1, 2081: 1, 2082: 1, 2093: 1, 2094: 1, 2095: 1, 2096: 1,
    2097: 1, 2098: 0, 2099: 0, 2103: 0, 2104: 0, 2105: 0, 2106: 0, 2107: 0,
    2111: 1, 2121: 1, 2122: 0, 2123: 1, 2131: 0, 2132: 1, 2133: 1, 2134: 0,
    2141: 0, 2142: 0, 2143: 0, 2144: 0, 2145: 0, 2146: 0, 2147: 0, 2148: 0,
    2149: 0, 2151: 1, 2152: 1, 2161: 0, 2162: 0, 2201: 0, 2202: 0, 2203: 0,
    2221: 0, 2222: 0, 2301: 0, 2302: 0, 2303: 0, 2304: 0, 2305: 0, 2306: 0,
    2307: 0, 2308: 0, 2309: 0, 2311: 0, 2321: 0, 2322: 0, 2331: 0, 2332: 0,
    2333: 0, 2334: 0, 2335: 0, 2336: 0, 2337: 0, 2338: 0, 2339: 0, 2341: 0,
    2342: 0, 2343: 0, 2344: 0, 2345: 0, 2351: 0, 2352: 0, 2353: 0, 2354: 0,
    2355: 0, 2356: 0, 2357: 0, 2361: 0, 2362: 0, 2363: 0, 2364: 0, 2365: 0,
    2366: 0, 2367: 0, 2368: 0, 2369: 0, 2371: 0, 2372: 0, 2373: 0, 3011: 1,
    3012: 1, 4011: 1, 20410: 1, 20411: 0, 20412: 0, 20413: 0, 20414: 0, 20415: 0,
    20416: 0, 20417: 0, 20418: 0, 20419: 0, 20420: 0, 20421: 0, 20422: 0, 20910: 0,
    21410: 0, 21411: 0, 21412: 0, 23010: 0, 23011: 0, 23012: 0, 23013: 0, 23014: 0,
    23015: 0, 23310: 0, 23311: 0, 23312: 0, 23313: 0, 23314: 0, 23315: 0, 23610: 0,
    23611: 0, 23612: 0, 23613: 0, 23614: 0, 23615: 0, 23616: 0,
}
