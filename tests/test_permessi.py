"""Potatura e instradamento: adattare i comandi a ciò che il backend autorizza su QUEL veicolo.

**Perché questi test sono i più delicati della suite.** Toccano la costruzione del comando che
parte davvero verso un'auto vera. Un errore qui non produce un test rosso: produce un comando che
arriva alla macchina sbagliata, o una funzione che sparisce a un utente che ce l'aveva.

Da qui l'ordine delle asserzioni, che non è casuale:

1. **Prima si difende chi già lo usa** (`test_omoda9_*`): sul profilo dell'Omoda 9, dove tutto ciò
   che spediamo è autorizzato, l'adattamento deve essere un **no-op letterale** — stesso endpoint,
   stesso corpo, per ogni singolo comando del catalogo.
2. **Poi il fallimento permissivo** (`test_ignoto_*`): lista assente o illeggibile ⇒ come prima.
   È la regola che impedisce a un timeout di rete di togliere funzioni all'utente.
3. **Solo alla fine il comportamento nuovo**, sui profili che non possediamo.

Il comportamento sotto test è stato **misurato**, non dedotto: due esperimenti controllati a
variabile singola su due endpoint indipendenti (2026-08-09), documentati in
`40_permessi/PROVA_AB_cycleData_20260809.md` e `40_permessi/PROVA_AB_airControl_20260810.md`.
"""
from __future__ import annotations

import pytest

import fixtures as FX


# ─────────────────────────────────────────────────────────────────────────────
# Profili veicolo (modelli compatti, solo le voci che ci riguardano).
# ─────────────────────────────────────────────────────────────────────────────

# Omoda 9 PHEV EU — ricalcato sulla lista reale letta il 2026-08-09 (334 voci). Qui stanno le
# sole voci toccate dai comandi del catalogo: le altre sono ignote, e ignoto = consentito.
OMODA9 = {
    204: 1, 2041: 1, 2042: 1, 2043: 1, 2044: 1, 2045: 1, 2046: 1,
    # sotto il clima i sedili e gli sbrinatori sono NEGATI: su questa auto si passa dalle
    # categorie dedicate. Sulla Jaecoo 7 è l'esatto contrario — è il caso "a specchio".
    2047: 0, 2048: 0, 2049: 0, 20410: 0, 20411: 0, 20412: 0, 20413: 0,
    20414: 0, 20415: 0, 20416: 0, 20417: 0, 20418: 0,
    208: 1, 2081: 1, 2082: 1,
    209: 1, 2093: 1, 2094: 1, 2095: 1, 2096: 1, 2097: 1, 2098: 1, 2099: 1, 20910: 1,
    210: 1, 2103: 1, 2104: 1, 2105: 1, 2106: 1, 2107: 1,
    214: 1, 2141: 1, 2142: 1, 2143: 1, 2144: 1, 2145: 1, 2146: 1, 2147: 1, 2148: 1,
    215: 1, 2151: 1, 2152: 1,
    232: 1, 2321: 1, 2322: 1,
    203: 1, 2031: 1, 2032: 0, 2033: 1,
    205: 1, 2051: 1, 2052: 1,
    206: 1, 2061: 1, 2062: 1, 2063: 1,
    207: 1, 2071: 1, 2072: 1, 2073: 1,
    213: 1, 2131: 0, 2132: 1, 2133: 1, 2134: 0,
    220: 0, 2201: 0, 2202: 0,
    231: 0, 2311: 0,
    # terza fila: NEGATA perché l'auto ha cinque posti — qui la lista descrive il FERRO,
    # non un permesso. È la ragione per cui questo modulo non può dedurre l'equipaggiamento.
    2149: 0, 21410: 0, 21411: 0, 21412: 0, 20419: 0, 20420: 0, 20421: 0, 20422: 0,
}

# Jaecoo 7 PHEV — profilo "a specchio" dell'issue #1: la categoria sedili dedicata è negata e i
# sedili vivono sotto il clima. ⚠️ IPOTETICO: di quel veicolo non abbiamo ancora nessun dato
# grezzo (lo "specchio" è una descrizione di seconda mano). Serve a fissare il comportamento
# atteso, non a dichiarare come sia fatta quella macchina.
JAECOO = dict(OMODA9)
JAECOO.update({
    214: 0, 2141: 0, 2142: 0, 2143: 0, 2144: 0, 2145: 0, 2146: 0, 2147: 0, 2148: 0,
    2047: 1, 2048: 1, 2049: 1, 20410: 1, 20411: 1, 20416: 1,   # consentiti sotto il clima
    232: 0, 2321: 0, 2322: 0,                                   # niente lunotto dedicato
    20910: 0,                                                   # e nella macro il lunotto è negato
})


@pytest.fixture
def P(core):
    return core["permessi"]


# ───────────────────── 1. l'Omoda 9 non deve cambiare di una virgola ─────────────────────

def test_omoda9_nessun_comando_viene_toccato(core, P):
    """Su questo profilo l'adattamento è un no-op **letterale**, comando per comando.

    È l'invariante che protegge chi il componente ce l'ha già installato: stessi endpoint,
    stessi corpi, quindi stessi effetti e stesso storico. Se questo test diventa rosso, un
    utente reale sta per vedere un comportamento diverso senza averlo chiesto."""
    commands = core["commands"]
    cambiati = []
    for chiave, c in commands.CMD_MAP.items():
        if c.get("path") or not c.get("endpoint"):
            continue        # antifurto & co.: path esplicito, fuori dalla tabella categorie
        ep, corpo, saltati, nota = P.adatta(c["endpoint"], dict(c["body"]), OMODA9)
        if ep != c["endpoint"] or corpo != c["body"] or saltati or nota:
            cambiati.append((chiave, ep, saltati, nota))
    assert not cambiati, f"comandi alterati sull'Omoda 9 (devono essere zero): {cambiati}"


def test_omoda9_le_macro_restano_intere(core, P):
    """Le macro comfort sono il bersaglio naturale della potatura: qui NON va potato nulla,
    perché sotto le categorie 209/210 questa auto ha tutto consentito."""
    commands = core["commands"]
    for chiave in ("clima_riscalda_on", "clima_raffredda_on"):
        c = commands.CMD_MAP[chiave]
        corpo, saltati = P.pota(c["endpoint"], dict(c["body"]), OMODA9)
        assert saltati == [], f"{chiave}: potati campi che l'auto autorizza → {saltati}"
        assert corpo == c["body"]


# ───────────────────── 2. fallimento permissivo ─────────────────────

@pytest.mark.parametrize("perms", [None, {}], ids=["mai-letta", "illeggibile"])
def test_ignoto_si_spedisce_come_sempre(core, P, perms):
    """Senza lista non si toglie NIENTE. Un timeout del backend — osservato davvero, due volte
    oltre i 60 s — non deve mai tradursi in una funzione in meno per l'utente."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_riscalda_on"]
    ep, corpo, saltati, nota = P.adatta(c["endpoint"], dict(c["body"]), perms or {})
    assert (ep, corpo, saltati, nota) == (c["endpoint"], c["body"], [], None)


def test_voce_sconosciuta_vale_consentita(P):
    """Una voce che non conosciamo non è una voce negata. Vale per i modelli che avranno id
    che oggi non esistono nella nostra tabella."""
    assert P.consentito({1: 1}, 999999) is True
    assert P.consentito({}, 2047) is True
    assert P.consentito({2047: 0}, 2047) is False


@pytest.mark.parametrize("payload", [
    None, {}, {"data": None}, {"data": {}}, {"data": {"permissionList": []}},
    {"data": {"permissionList": "non una lista"}}, "stringa al posto del json",
    {"data": {"permissionList": [{"senza": "id"}]}},
])
def test_risposte_malformate_non_esplodono(P, payload):
    """Meglio non sapere che sapere male: qualunque forma inattesa diventa `IGNOTO`."""
    assert P.normalizza(payload) == P.IGNOTO


# ───────────────────── 3. potatura ─────────────────────

def test_potatura_toglie_solo_il_campo_negato(core, P):
    """Il cuore della cura: un campo negato non deve più far rifiutare tutta la macro.

    Sul profilo Jaecoo il lunotto è negato sotto la macro riscaldamento: deve sparire quel
    campo e **solo** quello, così il comando passa e fa le altre sei cose."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_riscalda_on"]
    corpo, saltati = P.pota("heatingControl", dict(c["body"]), JAECOO)
    assert saltati == ["backDefrosting"]
    assert "backDefrosting" not in corpo
    for campo in ("mSeatHeating", "steerWheelHeatSwitch", "frontWindshieldHeat",
                  "airControlType", "temperature"):
        assert campo in corpo, f"{campo} tolto per errore: la potatura deve essere chirurgica"


def test_potatura_non_tocca_i_campi_base(P):
    """Accensione, temperatura e durata definiscono la richiesta: non sono potabili. Toglierli
    produrrebbe un corpo senza senso invece di un comando ridotto."""
    corpo = {"airControlType": "1", "airType": "1", "temperature": "31.0", "duration": "15"}
    negato_tutto = {v: 0 for v in range(2000, 21500)}
    fuori, saltati = P.pota("heatingControl", dict(corpo), negato_tutto)
    assert fuori == corpo and saltati == []


def test_base_negata_si_riconosce(P):
    """Se è negato il cuore della richiesta, la potatura non può salvare nulla: va detto."""
    assert P.base_negata("heatingControl", {2093: 0}) is True
    assert P.base_negata("heatingControl", OMODA9) is False


# ───────────────────── 4. instradamento ─────────────────────

def test_instradamento_scatta_anche_se_la_voce_figlia_MANCA(core, P):
    """⚠️ Il caso che la prima versione sbagliava, ed è il caso reale dell'issue #1.

    La lista di quel veicolo ha ~200 voci contro le nostre 334: i figli `2141`-`2148` possono
    non esserci affatto, mentre è la **categoria** 214 a essere negata in blocco. Guardando solo
    la figlia, `consentito()` la dava per consentita (sconosciuto = consentito) e il ripiego non
    scattava: la funzione restava rotta proprio sull'auto per cui era stata scritta."""
    commands = core["commands"]
    corta = {204: 1, 2047: 1, 214: 0}          # categoria negata, NESSUN figlio 214x presente
    c = commands.CMD_MAP["sedile_guida_caldo"]
    ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), corta)
    assert ep == "airControl", "il ripiego non è scattato: si guardava solo la voce figlia"
    assert corpo["mSeatHeating"] == "3" and nota


def test_categoria_negata_si_riconosce(core, P):
    """`porta_chiusa` è ciò che rende visibile all'utente il caso «non c'è nulla da adattare»."""
    commands = core["commands"]
    assert P.porta_chiusa("seatControl", {214: 0}) is True
    assert P.porta_chiusa("seatControl", OMODA9) is False
    assert P.porta_chiusa("chargeStartStopControl", OMODA9) is True   # 220 negata da noi
    assert P.porta_chiusa("seatControl", {}) is False                 # ignoto = aperta
    assert P.porta_chiusa("coolingControl", JAECOO) is False


def test_non_si_ripiega_se_anche_il_clima_e_chiuso(core, P):
    """Se pure la categoria 204 è negata, l'alternativa non esiste: non si cambia strada."""
    commands = core["commands"]
    chiuso = dict(JAECOO); chiuso[204] = 0
    c = commands.CMD_MAP["sedile_guida_caldo"]
    ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), chiuso)
    assert (ep, corpo, nota) == (c["endpoint"], c["body"], None)


def test_instradamento_sedile_passa_dal_clima(core, P):
    """Il caso dell'issue #1. Categoria sedili negata, voce sotto il clima consentita ⇒ si
    cambia porta invece di sbattere contro quella chiusa."""
    commands = core["commands"]
    c = commands.CMD_MAP["sedile_guida_caldo"]
    ep, corpo, saltati, nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert ep == "airControl"
    assert corpo["mSeatHeating"] == "3"
    assert corpo["airControlType"] == "1"      # accendendo, si accende anche il clima
    assert saltati == []
    assert nota and "clima" in nota            # e all'utente lo si dice


def test_instradamento_spegnimento_non_accende_il_clima(core, P):
    """Spegnere un sedile passando dal clima non deve **accendere** il clima."""
    commands = core["commands"]
    c = commands.CMD_MAP["sedile_guida_caldo_off"]
    _ep, corpo, _s, _n = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert corpo["airControlType"] == "0"


def test_instradamento_lunotto(core, P):
    """Stessa regola per lo sbrinamento lunotto: `isSeparateRearWindowDefrosting` nell'app
    guarda solo la categoria dedicata (232) per scegliere la via."""
    commands = core["commands"]
    c = commands.CMD_MAP["defrost_lunotto"]
    ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert ep == "airControl" and corpo["backDefrosting"] == "1" and nota


def test_porta_dedicata_aperta_si_resta(core, P):
    """Se la via di sempre è autorizzata non si cambia nulla: il ripiego è l'eccezione."""
    commands = core["commands"]
    c = commands.CMD_MAP["defrost_lunotto"]
    ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), OMODA9)
    assert (ep, corpo, nota) == (c["endpoint"], c["body"], None)


def test_entrambe_chiuse_si_spedisce_lo_stesso(core, P):
    """Nessuna delle due vie è autorizzata: **non** si inventa una terza strada e non si
    sopprime il comando. Si spedisce come sempre e l'utente riceve il rifiuto vero del
    backend, che è un'informazione — inventare un errore nostro non lo sarebbe."""
    commands = core["commands"]
    chiuso = dict(JAECOO)
    chiuso.update({2047: 0})
    c = commands.CMD_MAP["sedile_guida_caldo"]
    ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), chiuso)
    assert (ep, corpo, nota) == (c["endpoint"], c["body"], None)


# ───────────────────── 5. il messaggio all'utente ─────────────────────

def test_la_coda_non_sfonda_il_limite_dello_stato(core):
    """Uno stato Home Assistant non supera i 255 caratteri. La coda o entra intera o non si
    mette: tagliata a metà parola sarebbe peggio del silenzio (il dettaglio è comunque già
    passato dalla riga di avanzamento)."""
    commands = core["commands"]
    assert commands._coda_saltati(["backDefrosting"], 250) == ""
    coda = commands._coda_saltati(["backDefrosting"], 100)
    assert coda and 100 + len(coda) <= 255
    assert "skipped" in coda        # bilingue: HACS mostra lo stesso testo a tutti


def test_nomi_saltati_sono_leggibili(core):
    commands = core["commands"]
    assert commands.nomi_saltati(["backDefrosting", "mSeatHeating"]) == "lunotto, sedile guida"
    assert commands.nomi_saltati(["campoIgnoto"]) == "campoIgnoto"   # mai una riga vuota


# ───────────────────── 6. la catena vera, attraverso send() ─────────────────────

def _permessi_finti(mappa):
    return {"code": "000000",
            "data": {"permissionList": [{"id": str(k), "state": v} for k, v in mappa.items()]}}


def test_send_instrada_davvero_verso_un_altro_endpoint(core, cloud, ctx):
    """Il test che conta: non la funzione pura, ma l'URL su cui la richiesta atterra."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "sedile_guida_caldo")

    chiamate = cloud.calls_to("/asc/vehicleControl/")
    assert len(chiamate) == 1
    assert chiamate[0]["path"].endswith("/airControl"), (
        f"instradamento non applicato: {chiamate[0]['path']}")
    assert chiamate[0]["body"]["mSeatHeating"] == "3"


def test_send_pota_davvero_il_corpo(core, cloud, ctx):
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    esito = commands.send(ctx, "clima_riscalda_on")

    inviato = cloud.calls_to("/asc/vehicleControl/")[0]["body"]
    assert "backDefrosting" not in inviato
    assert inviato["mSeatHeating"] == "3"        # il resto della macro parte comunque
    assert "saltate" in esito and "skipped" in esito


def test_send_sull_omoda9_resta_identico(core, cloud, ctx):
    """La stessa catena, col profilo di casa: endpoint e corpo devono essere quelli di sempre."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(OMODA9))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "sedile_guida_caldo")
    commands.send(ctx, "clima_riscalda_on")

    percorsi = [c["path"] for c in cloud.calls_to("/asc/vehicleControl/")]
    assert percorsi[0].endswith("/seatControl")
    assert percorsi[1].endswith("/heatingControl")
    assert "backDefrosting" in cloud.calls_to("/asc/vehicleControl/")[1]["body"]


def test_la_lista_si_legge_una_volta_sola(core, cloud, ctx):
    """Una lettura in più a ogni comando sarebbe traffico verso il cloud del costruttore per
    un dato che non cambia. Si legge al primo comando e si tiene nel contesto del veicolo."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(OMODA9))
    cloud.on("/asc/vehicleControl/", code="A00079")

    for _ in range(3):
        commands.send(ctx, "clima_on")

    assert cloud.count("/tsp/v1/app/vmc/queryVehicleAuthority") == 1


def test_lista_in_errore_non_blocca_il_comando(core, cloud, ctx):
    """Il backend va in timeout su quell'endpoint: il comando deve partire lo stesso, intero."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", raises=TimeoutError("timeout finto"))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "clima_riscalda_on")

    inviato = cloud.calls_to("/asc/vehicleControl/")[0]["body"]
    assert "backDefrosting" in inviato          # nessuna potatura: non sappiamo nulla
    assert ctx.permessi == {}                   # e non si ritenta al prossimo comando
