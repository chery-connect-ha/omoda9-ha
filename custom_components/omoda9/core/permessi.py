#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`permessi.py` — adatta i comandi a ciò che il backend autorizza SU QUEL veicolo.

**Il problema.** Il catalogo comandi (`commands.py`) è cablato sull'Omoda 9 di chi ha scritto
l'integrazione: un endpoint fisso per funzione, e le macro comfort spedite sempre intere. Su un
veicolo diverso questo produce fallimenti totali dove l'app ufficiale invece riesce — è il caso
dell'issue #1 (Jaecoo 7 PHEV: sedili, sbrinamento lunotto e macro rispondono tutti `A00084`).

**Cosa abbiamo misurato (2026-08-09), e che qui diventa codice.** Il backend **valida il corpo
campo per campo** contro le voci figlie della categoria dell'endpoint chiamato. Due esperimenti
controllati a variabile singola, su due endpoint indipendenti, con previsione scritta prima:

* `chargeAppointControl` — cambia solo `cycleData`: `[1,3,5]` (voce 2131 *ciclo personalizzato*,
  negata) → **A00084**; `[1..7]` (voce 2132, consentita) → **A00079**;
* `airControl` — cambia solo la presenza di `backDefrosting` (voce 20411 negata sotto 204):
  con il campo → **A00084**; senza → **A00079** (ed è `clima_on`, il comando di tutti i giorni).

Documentazione e dati grezzi: `40_permessi/PROVA_AB_cycleData_20260809.md`,
`40_permessi/PROVA_AB_airControl_20260810.md`, `40_permessi/PERMESSI_VEICOLO.md`.

**Le due cure, che sono la stessa difesa contro la stessa validazione:**

1. **Potatura** — un solo campo negato fa rifiutare *tutta* la richiesta, anche le parti
   consentite. Prima di spedire una macro si tolgono i campi che quel veicolo non ammette: la
   macro passa e fa ciò che può, invece di fallire in blocco.
2. **Instradamento** — per i comandi singoli non c'è nulla da potare: lì il problema è che
   bussiamo sempre alla stessa porta. La stessa funzione fisica esiste sotto più categorie
   (il sedile sotto 214 *e* sotto 204) e i due veicoli sono configurati a specchio.

**Non è un'invenzione nostra: è ciò che fa l'app ufficiale.** Nel decompilato,
`RusPermissionsProvider` espone **32** funzioni `can*` che leggono questa stessa lista con una
logica **OR** fra la voce sotto il clima e la categoria dedicata (`canRearWindowDefrosting` →
`20411` oppure `232`), più **2** funzioni `isSeparate*` che guardano **solo** la categoria dedicata
e decidono se usare l'endpoint dedicato o infilare il campo dentro `airControl`. E in
`RusCarCntrolViewModel::controlOneTouchHeatOrCool` ci sono **11** chiamate a `isShowByPermission`,
una per ciascun figlio della macro (`2094`-`20910` per il caldo, `2104`-`2107` per il freddo): è
l'app che pota il corpo campo per campo. Le tabelle qui sotto ricalcano quella mappa.

⚠️ **REGOLA NON NEGOZIABILE — FALLIMENTO PERMISSIVO.** Lista non letta, illeggibile, endpoint in
timeout (osservato: due volte oltre i 60 s), categoria o voce sconosciuta ⇒ **ci si comporta
esattamente come prima**, corpo intero ed endpoint di sempre. Non si toglie mai una funzione per
un problema di rete. Corollario: sull'Omoda 9, dove tutto ciò che usiamo è consentito, questo
modulo è un **no-op** — nessuna entità cambia, nessun endpoint cambia (`tests/test_permessi.py`).

⚠️ **Questo modulo NON crea e NON toglie entità.** Filtrare le entità con questa lista è stato
valutato e **ritirato**: farebbe sparire `switch.omoda9_ricarica` (categoria 220 negata sulla
nostra auto) rompendo l'invariante delle 105, la lista è per-**utente** e non per veicolo, e in
Home Assistant nascondere è distruttivo (lascia orfani) mentre nell'app è reversibile.
"""
from __future__ import annotations

import json
import logging

_LOGGER = logging.getLogger(__name__)

# Percorso BFF, stesso strato di auth di queryList/setVecDefault già usati per il taskId.
PATH = "/tsp/v1/app/vmc/queryVehicleAuthority"

# Sentinella: "ho provato a leggere e non ci sono riuscito" (≠ None = "non ho ancora provato").
# In entrambi i casi si spedisce come prima; serve solo a non ritentare a ogni comando.
IGNOTO: dict = {}


# ─────────────────────── categoria di ciascun endpoint ───────────────────────
# La corrispondenza è per ENDPOINT TECNICO, mai per nome della funzione: il bagagliaio compare
# sia come `2032` (figlio delle serrature, negato da noi) sia come categoria `205` (consentita),
# e il nostro pulsante usa `powerLiftgateControl` → 205, che infatti funziona.
CATEGORIA = {
    "airControl": 204,
    "heatingControl": 209,
    "coolingControl": 210,
    "seatControl": 214,
    "frontWindshieldControl": 215,
    "backDefrostingControl": 232,
    "steeringWheelControl": 208,
    "lockControl": 203,
    "powerLiftgateControl": 205,
    "windowControl": 206,
    "skylightControl": 207,
    "chargeStartStopControl": 220,
    "chargeAppointControl": 213,
    "findCar": 202,
    "vehicleLocation": 211,
}
# NB `remoteStart` non compare: il comando è stato tolto dal catalogo dopo una prova dal vivo
# (vedi `commands.py`). Teneva qui la categoria 231, e una riga irraggiungibile si legge come
# informazione anche quando non lo è.

# ─────────────────────── categoria dei comandi fuori da /asc/vehicleControl ───────────────────
# L'antifurto vive su `/act` e nel catalogo usa la chiave `path`: non passa da `adatta()` perché
# non c'è nulla da potare né una porta alternativa. Gli serve però la categoria per l'AVVISO
# preventivo, che fino alla v1.11.1 non riceveva: su un veicolo con la sicurezza negata l'utente
# vedeva un `A00084` nudo. La categoria la dichiara la voce di catalogo (`"categoria": 401`).

# ─────────────────────── voce figlia di ciascun campo ───────────────────────
# Solo i campi ACCESSORI, quelli che si possono togliere lasciando una richiesta ancora sensata.
# I campi che definiscono la richiesta stessa (accensione/temperatura/durata del clima) NON sono
# qui di proposito: toglierli produrrebbe un corpo senza senso, e vanno trattati come "o tutto o
# niente" (vedi `voce_base`).
POTABILI = {
    # macro "riscalda tutto" (209): base = 2093 (aria condizionata)
    "heatingControl": {
        "steerWheelHeatSwitch": 2094,
        "frontWindshieldHeat": 2095,
        "mSeatHeating": 2096, "pSeatHeating": 2097,
        "blSeatHeating": 2098, "brSeatHeating": 2099,
        "backDefrosting": 20910,
    },
    # macro "raffredda tutto" (210): base = 2103
    "coolingControl": {
        "mSeatAiry": 2104, "pSeatAiry": 2105,
        "blSeatAiry": 2106, "brSeatAiry": 2107,
    },
    # clima singolo (204) — accessori che l'endpoint accetta ma che noi oggi non spediamo mai;
    # li spediamo però quando ci ripieghiamo qui (vedi RIPIEGO), e allora vanno validati.
    "airControl": {
        "airPurControlType": 2046,
        # `frontDefrosting` = disappannamento del parabrezza dal clima (voce 2045), il campo che
        # alimenta lo switch omonimo. Sta qui perché è ACCESSORIO: toglierlo lascia una richiesta
        # di clima ancora sensata, che è esattamente il comportamento voluto su un veicolo che
        # non lo autorizza — il clima parte lo stesso, senza il disappannamento.
        "frontDefrosting": 2045,
        "mSeatHeating": 2047, "pSeatHeating": 2048,
        "mSeatAiry": 2049, "pSeatAiry": 20410,
        "backDefrosting": 20411,
        "blSeatHeating": 20412, "brSeatHeating": 20413,
        "blSeatAiry": 20414, "brSeatAiry": 20415,
        "frontWindshieldHeat": 20416,
    },
}

# Voce che autorizza il CUORE della richiesta: se questa è negata non c'è potatura che tenga.
VOCE_BASE = {"heatingControl": 2093, "coolingControl": 2103, "airControl": 2041}

# ─────────────────────── instradamento: la stessa funzione, due porte ───────────────────────
# Per ogni (endpoint dedicato, campo): la voce che lo autorizza sull'endpoint dedicato e la voce
# che lo autorizzerebbe passando invece da `airControl`. Ricalca `isSeparate*` dell'app: si usa
# la porta dedicata se è aperta, altrimenti si prova l'altra.
RIPIEGO = {
    ("backDefrostingControl", "backDefrosting"):     (2321, 20411),
    ("frontWindshieldControl", "frontWindshieldHeat"): (2151, 20416),
    ("seatControl", "mSeatHeating"):  (2141, 2047),
    ("seatControl", "pSeatHeating"):  (2142, 2048),
    ("seatControl", "mSeatAiry"):     (2143, 2049),
    ("seatControl", "pSeatAiry"):     (2144, 20410),
    ("seatControl", "blSeatHeating"): (2145, 20412),
    ("seatControl", "brSeatHeating"): (2146, 20413),
    ("seatControl", "blSeatAiry"):    (2147, 20414),
    ("seatControl", "brSeatAiry"):    (2148, 20415),
}

# Corpo minimo che `airControl` pretende quando ci si ripiega dentro. Ricalcato sull'envelope
# reale dell'app (cattura 2026-06-20: airControlType, airType, temperature, times + il campo).
# ⚠️ `airControlType` fa parte della richiesta: passando di qui **si comanda anche il clima** —
# lo si ACCENDE accendendo il campo e lo si SPEGNE spegnendolo, esattamente come fanno le macro.
# È un effetto collaterale dichiarato, non un incidente, e si attiva solo su veicoli dove oggi
# quel comando fallirebbe comunque al 100%.
# ⚠️ `temperature` e `times` qui sono SEGNAPOSTO: sono i valori dell'Omoda 9, e questo modulo non
# conosce la scheda tecnica della vettura. Chi chiama DEVE farli ripassare dagli adattatori alla
# scheda DOPO l'instradamento, perché quelli girano PRIMA (a quel punto l'endpoint era ancora
# quello dedicato e questi due valori non esistevano nel corpo).
# Gli adattatori giusti sono `commands._limita_temperatura` e `commands._adatta_durata`, e sono
# quelli che `commands.send()` richiama quando l'endpoint è cambiato. ⚠️ NON
# `commands.adatta_capability`: quella lavora solo su `coolingControl`/`heatingControl`, dove
# `temperature` è la posizione LO/HI della macro, e su `airControl` è esclusa di proposito.
# Chiamarla qui sarebbe una riga che non fa mai nulla.
BASE_AIRCONTROL = {"airType": "1", "temperature": "21.0", "times": "15"}


def _num(x):
    try:
        return int(str(x).strip())
    except (TypeError, ValueError):
        return None


def normalizza(payload) -> dict:
    """Da risposta grezza del BFF a `{id(int): state(int)}`. Ritorna `IGNOTO` su qualunque forma
    inattesa: meglio non sapere che sapere male."""
    try:
        data = payload.get("data") if isinstance(payload, dict) else None
        lista = data.get("permissionList") if isinstance(data, dict) else None
        if not isinstance(lista, list) or not lista:
            return IGNOTO
        out = {}
        for voce in lista:
            if not isinstance(voce, dict):
                continue
            vid, st = _num(voce.get("id")), _num(voce.get("state"))
            if vid is not None and st is not None:
                out[vid] = st
        return out or IGNOTO
    except Exception:  # noqa: BLE001 — qualunque sorpresa = "non lo so"
        return IGNOTO


def leggi(ctx, token, tuid) -> dict:
    """Interroga la lista permessi del veicolo. **Non attua nulla, non usa il PIN, non conia
    taskId.** Qualunque errore (rete, timeout, forma) ⇒ `IGNOTO` ⇒ si spedisce come prima."""
    if not token or not tuid:
        return IGNOTO
    try:
        import requests

        from . import omoda_auth as A

        H = A.headers_post(PATH, ctx=ctx, extra={
            "Authorization": f"Bearer {ctx_access(ctx)}",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/plain, */*"})
        r = requests.post(
            ctx.bff + PATH,
            data=json.dumps({"vin": ctx.vin, "tUserId": str(tuid),
                             "channelId": ctx.channel_id}),
            headers=H, timeout=15)
        return normalizza(r.json())
    except Exception as err:  # noqa: BLE001
        # Volutamente a livello DEBUG: non sapere i permessi è una condizione NORMALE e
        # innocua (si spedisce come prima). Un WARNING a ogni avvio sarebbe solo rumore.
        _LOGGER.debug("[permessi] lettura non riuscita (%s) → si procede come sempre", err)
        return IGNOTO


def ctx_access(ctx):
    """Token d'accesso già in mano al componente (nessun login, nessun OTP)."""
    from . import wake

    return wake._access_token(ctx)


def consentito(perms: dict, voce: int | None) -> bool:
    """Vero se la voce è consentita **o sconosciuta**. Sconosciuto = consentito: è il
    fallimento permissivo, ed è la ragione per cui questo modulo non può togliere funzioni a
    un veicolo di cui non sappiamo abbastanza."""
    if not perms or voce is None:
        return True
    return perms.get(voce, 1) != 0


def pota(endpoint: str, body: dict, perms: dict) -> tuple[dict, list]:
    """Toglie dal corpo i campi la cui voce figlia è negata su questo veicolo.

    Ritorna `(corpo, saltati)` dove `saltati` è la lista dei nomi di campo rimossi. Se non c'è
    niente da togliere ritorna il corpo **identico** (stesso contenuto), così sull'Omoda 9 il
    comportamento è bit-per-bit quello di prima."""
    tabella = POTABILI.get(endpoint)
    if not perms or not tabella:
        return body, []
    saltati = [c for c in body if c in tabella and not consentito(perms, tabella[c])]
    if not saltati:
        return body, []
    return {k: v for k, v in body.items() if k not in saltati}, saltati


def base_negata(endpoint: str, perms: dict) -> bool:
    """Vero se è negato il cuore stesso della richiesta: qui la potatura non serve a nulla e
    conviene dirlo invece di lasciare l'utente a indovinare perché non è cambiato niente."""
    return not consentito(perms, VOCE_BASE.get(endpoint))


def porta_chiusa(endpoint: str, perms: dict) -> bool:
    """Vero se è negata l'INTERA categoria dell'endpoint (non una sua voce figlia).

    ⚠️ Questa funzione esiste per un difetto reale della prima versione, che merita di restare
    scritto. Il ripiego decideva guardando **solo la voce figlia**, e `consentito()` tratta una
    voce sconosciuta come consentita (fallimento permissivo). Bastava allora che i figli
    `2141`-`2148` mancassero perché la porta dedicata fosse giudicata aperta, il ripiego non
    scattasse mai, e la funzione restasse rotta **proprio sul veicolo per cui era stata scritta**.

    ⚠️ Sul veicolo dell'issue #1 le cose stanno diversamente da come si era supposto, e ora il
    dato grezzo c'è (`45_capability/permessi_jaecoo7_phev_eu.json`, 280 voci contro le nostre
    334): gli otto figli `2141`-`2148` **ci sono tutti, e valgono tutti 0**, insieme alla
    categoria 214. Il difetto restava reale, solo per un'altra strada. La vecchia stima «~200
    voci» era di seconda mano ed era sbagliata.

    La categoria è il segnale più grossolano ma anche il più affidabile: c'è sempre, ed è quello
    che i due `isSeparate*` dell'app guardano. Resta permissiva: categoria sconosciuta = aperta."""
    return categoria_chiusa(CATEGORIA.get(endpoint), perms)


# Il testo dell'avviso «categoria negata» vive in UNA sola costante perché lo emettono due rami
# diversi di `commands.send()`: i comandi con endpoint (via `verdetto`) e quelli con `path`
# esplicito (l'antifurto, via `categoria_chiusa`). Erano due stringhe gemelle copiate a mano, e
# due stringhe gemelle divergono: la misura del limite dei 255 caratteri ne guardava una sola.
# ⚠️ Il testo deve reggere ACCANTO all'elenco dei campi potati, non al posto suo. La coda
# «non c'è nulla da adattare» era nata quando i due avvisi erano alternativi (`elif`): tolto
# l'`elif`, sul veicolo dell'issue #1 «Raffredda tutto» produce le due righe in fila —
#   «salto aria sedile guida, …» seguito da «non c'è nulla da adattare» —
# e la seconda nega la prima, oltre a essere falsa: quattro campi li abbiamo appena adattati.
# Dire invece che nessun adattamento basta è vero in entrambi i casi, con o senza potatura.
MSG_CATEGORIA_NEGATA = ("il costruttore non autorizza affatto questa funzione su questa auto: "
                        "nessun adattamento può farla passare")
MSG_BASE_NEGATA = ("questa auto non autorizza il cuore di questa richiesta: il rifiuto che sta "
                   "per arrivare non dipende dall'integrazione")


def verdetto(endpoint: str, perms: dict) -> str | None:
    """La frase da dire PRIMA di spedire quando il comando è condannato comunque, o None.

    Va valutata DOPO l'instradamento e la potatura, e **in aggiunta** all'elenco dei campi
    potati, mai in alternativa: sono due fatti diversi e all'utente servono entrambi. Sul
    veicolo dell'issue #1 la macro «Raffredda tutto» produce quattro campi potati **e** ha la
    categoria 210 negata: dirgli solo «salto i quattro sedili» gli fa credere che il clima si
    accenderà, e non si accende.

    Non modifica nulla e non impedisce l'invio: il comando parte e l'utente riceve il rifiuto
    vero del backend, che è un'informazione. Sopprimerlo non lo sarebbe.

    I due rami guardano segnali diversi — `porta_chiusa` la categoria, `base_negata` la voce
    base — e sul profilo reale del veicolo dell'issue #1 il freddo li accende entrambi (210 e
    2103 negate); esistono profili in cui scatterebbe solo il secondo. La categoria viene prima
    perché è il segnale che c'è sempre."""
    if not perms or not endpoint:
        return None
    if porta_chiusa(endpoint, perms):
        return MSG_CATEGORIA_NEGATA
    if base_negata(endpoint, perms):
        return MSG_BASE_NEGATA
    return None


def categoria_chiusa(categoria: int | None, perms: dict) -> bool:
    """Come `porta_chiusa`, ma partendo dal numero di categoria invece che dall'endpoint.

    Serve ai comandi che non stanno su `/asc/vehicleControl` (l'antifurto, che usa `path` e
    dichiara la categoria nel catalogo). Stessa regola permissiva: categoria ignota o lista non
    letta ⇒ aperta, perché non si toglie mai una funzione per un dato che non abbiamo."""
    return not consentito(perms, categoria)


# ─────────────────────── ciclo dei piani programmati ───────────────────────
# Ricarica e viaggio programmati portano una LISTA DI GIORNI, e il backend valida anche quella:
# misurato su `chargeAppointControl` con un A/B a variabile singola — `cycleData` [1,3,5] (voce
# 2131 «ciclo personalizzato», negata) → A00084; [1..7] (voce 2132, consentita) → A00079.
# Per ogni endpoint: (voce del ciclo personalizzato, voce del ciclo di 7 giorni, nome del campo).
# ⚠️ La polarità NON è la stessa fra le due funzioni: sulla nostra auto la 213 consente solo i
# 7 giorni e la 212 solo il personalizzato. Per questo la tabella è per-endpoint e non una regola.
CICLO = {
    "chargeAppointControl": (2131, 2132, "cycleData"),
}
# NB `appointmentTravel` non compare: non esiste un comando con quell'endpoint — il piano di
# partenza programmata è di sola lettura (`sensor.py`). Le sue voci restano però interessanti e
# vanno conservate qui: (2121 «ciclo personalizzato», 2122 «7 giorni», campo `travelWeekday`),
# con la polarità INVERTITA rispetto alla ricarica e identica su entrambe le auto conosciute.


def _giorni(body: dict, campo: str) -> list | None:
    """Estrae la lista dei giorni dal corpo, sia se è in cima sia dentro il piano annidato."""
    if isinstance(body.get(campo), list):
        return body[campo]
    for valore in body.values():
        if isinstance(valore, list):
            for voce in valore:
                if isinstance(voce, dict) and isinstance(voce.get(campo), list):
                    return voce[campo]
    return None


def ciclo_non_autorizzato(endpoint: str, body: dict, perms: dict) -> str | None:
    """Messaggio da mostrare PRIMA dell'invio se il ciclo scelto non è autorizzato, altrimenti None.

    Non corregge nulla di proposito: gli unici rimedi possibili sarebbero cambiare i giorni scelti
    dall'utente o togliere la lista, e un piano che parte in giorni che nessuno ha chiesto è
    peggio di un rifiuto onesto. Serve solo a far capire che il `A00084` che sta per arrivare non
    è un difetto dell'integrazione."""
    regola = CICLO.get(endpoint)
    if not perms or not regola:
        return None
    voce_personalizzato, voce_settimana, campo = regola
    giorni = _giorni(body, campo)
    if not giorni:
        return None
    settimana = len(giorni) == 7
    if consentito(perms, voce_settimana if settimana else voce_personalizzato):
        return None
    return ("questa auto non autorizza il ciclo "
            + ("di tutti i giorni" if settimana else "su giorni scelti")
            + " per questa programmazione")


def instrada(endpoint: str, body: dict, perms: dict) -> tuple[str, dict, str | None]:
    """Sceglie la porta aperta su QUESTO veicolo.

    Ritorna `(endpoint, corpo, nota)`. `nota` è valorizzata solo quando si è cambiata strada,
    ed è pensata per finire sotto gli occhi dell'utente: un comando che arriva per una via
    diversa, e che di conseguenza tocca anche il clima, non deve essere una sorpresa."""
    if not perms:
        return endpoint, body, None
    for campo in list(body):
        regola = RIPIEGO.get((endpoint, campo))
        if not regola:
            continue
        dedicata, alternativa = regola
        # Una porta è aperta se lo sono SIA la sua categoria SIA la voce figlia. Guardare solo
        # la figlia era il difetto della prima versione: su una lista più corta della nostra la
        # figlia manca, «sconosciuta» vale «consentita», e il ripiego non scattava mai.
        if consentito(perms, dedicata) and not porta_chiusa(endpoint, perms):
            return endpoint, body, None          # la porta di sempre è aperta: non si tocca nulla
        if not consentito(perms, alternativa) or porta_chiusa("airControl", perms):
            return endpoint, body, None          # chiuse entrambe: si spedisce e si riporta il rifiuto vero
        acceso = str(body.get(campo, "0")).strip() not in ("0", "", "false", "False")
        nuovo = dict(BASE_AIRCONTROL)
        nuovo["airControlType"] = "1" if acceso else "0"
        nuovo[campo] = body[campo]
        # ⚠️ Il verbo segue il campo: spegnendo il sedile si spegne anche il clima. Dire sempre
        # «si accende» era falso proprio nel ramo che l'utente usa per FERMARE qualcosa.
        return ("airControl", nuovo,
                "questa funzione non è autorizzata sulla sua via abituale su questo veicolo: "
                "inviata tramite il clima, che quindi si "
                + ("accende" if acceso else "spegne") + " insieme a lei")
    return endpoint, body, None


def adatta(endpoint: str, body: dict, perms: dict) -> tuple[str, dict, list, str | None]:
    """Punto d'ingresso unico: prima si sceglie la porta, poi si pota ciò che si spedisce.

    L'ordine conta: potare prima dell'instradamento significherebbe valutare i campi contro le
    voci dell'endpoint sbagliato."""
    if not perms:
        return endpoint, body, [], None
    endpoint, body, nota = instrada(endpoint, body, perms)
    body, saltati = pota(endpoint, body, perms)
    return endpoint, body, saltati, nota


# ────────────────────── sospetti: quello che non sappiamo, detto come tale ──────────────────────
# Chiavi che compaiono nei corpi ma per cui NON abbiamo una corrispondenza PROVATA con una voce
# della lista. Servono ESCLUSIVAMENTE al log e alla diagnostica: sono mappature PER NOME, e in
# questo progetto una mappatura per nome ha già prodotto un errore (`timeConsuming` → 2134). Non
# possono e non devono influenzare il corpo spedito: per questo stanno qui e non in `POTABILI`.
#
#   `times` ↔ 2044 «impostare la durata»: sulla nostra auto vale 1, sul veicolo dell'issue #1
#   vale 0. `times` non sta solo nel corpo di ripiego: lo portano **quattordici** comandi del
#   catalogo, e fra questi `clima_on`, `clima_off` e i due disappannamenti del parabrezza dal
#   clima partono interi anche su quel veicolo (categoria 204 e voce 2045 consentite: niente
#   potatura, niente cambio di porta). Quindi delle due l'una: o 2044 non governa `times` — e
#   allora non c'è niente da fare — oppure lo governa, e allora «Clima acceso» su quell'auto è già
#   rotto oggi, senza che noi cambiamo una riga. È una domanda all'utente, non un esperimento:
#   finché non ha risposto, potare sarebbe indovinare.
SOSPETTI_NON_MAPPATI = {"times": 2044}


def sospetti(body: dict, perms: dict) -> list[tuple[str, int]]:
    """Chiavi del corpo la cui voce SOSPETTA (non provata) risulta negata su questo veicolo.

    Solo per il log e la diagnostica. Chi chiama non deve toccare il corpo in base a questo
    ritorno: se lo facesse, una mappatura per nome sarebbe diventata comportamento.

    Lista assente o vuota ⇒ lista vuota, come ogni altra funzione di questo modulo: non sapere
    non deve mai produrre un'affermazione."""
    if not perms:
        return []
    return [(chiave, voce) for chiave, voce in SOSPETTI_NON_MAPPATI.items()
            if chiave in body and perms.get(voce) == 0]
