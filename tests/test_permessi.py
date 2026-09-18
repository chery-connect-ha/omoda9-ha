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

# Jaecoo 7 PHEV EU — ⚠️ NON è più un profilo inventato: dal 2026-08-10 è la lista **reale** di
# quel veicolo (182 voci dei rami 2/3/4, vedi `fixtures.py`).
#
# Il profilo che stava qui prima era ipotetico e sbagliato **proprio nei due valori che
# decidono**: dava `20411 = 1` (lunotto raggiungibile dal clima) e `2047 = 1` senza il resto del
# quadro. Sul veicolo vero `20411 = 0` e il lunotto non ha alcuna via aperta. Tre test erano
# verdi descrivendo comportamenti che su quell'auto non accadono — di qui la regola: un profilo
# di prova inventato è peggio di nessun profilo, perché la suite certifica l'invenzione.
JAECOO = FX.JAECOO7_PHEV_EU


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

    ⚠️ Questo è l'unico test della suite ancorato a una **misura contro il backend vero su
    un'auto che non possediamo**. Il 2026-08-10 l'utente dell'issue #1 ha rispedito la stessa
    `heatingControl` togliendo a mano `backDefrosting`, `blSeatHeating` e `brSeatHeating`, e la
    risposta è passata da `A00084` (rifiutato) ad `A00079` (accettato). Qui si verifica che la
    nostra potatura, sul suo profilo permessi reale, produca **esattamente quel corpo**.

    Non dimostra la corrispondenza dei singoli campi: i tre sono stati tolti insieme, quindi la
    misura dice «almeno uno dei tre bloccava», non quale. Dimostra però che il corpo che
    spediremmo è uno che il backend ha davvero accettato."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_riscalda_on"]
    corpo, saltati = P.pota("heatingControl", dict(c["body"]), JAECOO)
    assert sorted(saltati) == ["backDefrosting", "blSeatHeating", "brSeatHeating"]
    # le otto chiavi del corpo che ha ottenuto A00079 (ISSUE1_commento_20260810.md)
    assert set(corpo) == {"airControlType", "airType", "duration", "temperature",
                          "frontWindshieldHeat", "mSeatHeating", "pSeatHeating",
                          "steerWheelHeatSwitch"}
    # `duration` e `temperature` non hanno alcuna voce figlia sotto la 209: le chiavi non
    # mappate passano, e devono continuare a passare — potarle sarebbe un difetto.
    assert corpo["duration"] and corpo["temperature"]


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
    """⚠️ Il caso che la prima versione sbagliava: una lista in cui la **categoria** è negata
    in blocco ma i figli non compaiono. Guardando solo la figlia, `consentito()` la dava per
    consentita (sconosciuto = consentito) e il ripiego non scattava.

    ⚠️ Il profilo `corta` qui sotto è **sintetico**, e va tenuto tale. La motivazione scritta
    qui fino al 2026-08-10 diceva che era il caso dell'auto dell'issue #1, «~200 voci contro le
    nostre 334, i figli 2141-2148 possono non esserci»: il dato grezzo arrivato quel giorno l'ha
    smentita: quella lista ha **280** voci e gli otto figli **ci sono tutti, tutti a 0** (vedi la
    docstring di `permessi.porta_chiusa`, e `FX.JAECOO7_PHEV_EU`). Il difetto era reale, ma per
    un'altra strada. Questo test resta perché copre il caso «figlio assente», che sui due
    profili reali non si presenta più e che nessun altro test esercita."""
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
    # Sul veicolo vero dell'issue #1 la macro freddo è negata in blocco (210 = 0): il comando
    # partirà e verrà rifiutato, e l'utente ha diritto di saperlo prima. Il vecchio profilo
    # inventato diceva il contrario.
    assert P.porta_chiusa("coolingControl", JAECOO) is True


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


def test_ripiego_off_spegne_anche_il_clima(core, P):
    """Spegnere il sedile per la via del clima **spegne anche il clima**, e va detto.

    Il nome precedente (`..._non_accende_il_clima`) era vero alla lettera e fuorviante nella
    sostanza: nascondeva l'effetto invece di dichiararlo. Il corpo resta questo — è simmetrico
    all'accensione e non inventiamo forme che nessuno ha visto accettare — ma la nota
    all'utente deve dire *spegne*, non *accende*."""
    commands = core["commands"]
    c = commands.CMD_MAP["sedile_guida_caldo_off"]
    _ep, corpo, _s, nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert corpo["airControlType"] == "0"
    assert nota and "spegne" in nota and "accende" not in nota


def test_lunotto_sul_veicolo_vero_non_ha_nessuna_via(core, P):
    """Il lunotto dell'issue #1 non si ripiega: **non ha una porta alternativa aperta**.

    Questo test prima asseriva il contrario, e lo faceva su un profilo inventato che dava
    `20411 = 1`. Sul veicolo vero sono negate sia la categoria dedicata (232) sia la voce sotto
    il clima (20411): non esiste una via da preferire, quindi si spedisce come sempre e si
    riporta il rifiuto vero del backend. Inventare un ripiego qui significherebbe accendere il
    climatizzatore di casa d'altri per una funzione che comunque non partirebbe."""
    commands = core["commands"]
    c = commands.CMD_MAP["defrost_lunotto"]
    ep, corpo, saltati, nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert (ep, corpo, saltati, nota) == (c["endpoint"], c["body"], [], None)
    # ma all'utente si dice perché arriverà un rifiuto, invece di lasciarlo indovinare
    assert P.verdetto(ep, JAECOO)


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


# ───────────────────── 4-bis. ricomposizione della macro negata in blocco ─────────────────────
#
# `instrada` sposta UN campo; qui a essere negato è il comando intero. La macro «raffredda tutto»
# del veicolo dell'issue #1 non ha una porta (categoria 210 chiusa), ma i suoi pezzi ce l'hanno:
# si riscrive come un'unica `airControl` con gli stessi campi.
#
# ⚠️ MISURATO, non dedotto. L'utente dell'issue #1 ha spedito a mano, dal sandbox, ad auto ferma:
#   {"airControlType":"1","airType":"1","temperature":"16.0","times":"15",
#    "mSeatAiry":"3","pSeatAiry":"3"}  → A00079
# ed è poi **uscito a toccare i cuscini**: entrambi i sedili anteriori ventilavano davvero. È
# l'unico punto di questa suite ancorato a una misura su ENTRAMBI gli strati (backend e vettura),
# su un'auto che non possediamo. I test qui sotto tengono quel corpo come riferimento letterale.

# Scheda plausibile e COMPLETA di una vettura che non scende sotto i 16 °C. Porta anche gli
# estremi LO/HI, perché una scheda vera che dichiara `isHaveLoAndHi` li ha entrambi e li vuole
# coerenti col range (`const.capabilities_from_item`): senza di essi `adatta_capability` sarebbe
# un no-op e il test proverebbe il valore giusto per il motivo sbagliato.
_SCHEDA_JAECOO = {"durate_aria": [5, 10, 15], "clima_min": 16.0, "clima_max": 30.0,
                  "clima_lo": 15.0, "clima_hi": 31.0}


def test_ricomposizione_riproduce_il_corpo_misurato(core, P):
    """Il corpo ricomposto dev'essere **quello che l'utente ha misurato**, chiave per chiave."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_on"]
    # `adatta_capability` gira prima, sull'endpoint ancora originale: mette la posizione LO
    # dichiarata dalla vettura al posto del 15.0 cablato per l'Omoda 9.
    corpo = commands.adatta_capability(c["endpoint"], dict(c["body"]), _SCHEDA_JAECOO)
    assert corpo["temperature"] == "15.0", "premessa: entra la POSIZIONE LO, non un setpoint"
    ep, corpo, saltati, nota = P.adatta(c["endpoint"], corpo, JAECOO)
    commands._setpoint_da_posizione(corpo, _SCHEDA_JAECOO)   # secondo giro: la porta è cambiata
    commands._limita_temperatura(corpo, _SCHEDA_JAECOO)

    assert ep == "airControl"
    assert corpo == {"airControlType": "1", "airType": "1", "temperature": "16.0",
                     "times": "15", "mSeatAiry": "3", "pSeatAiry": "3"}
    # i due posteriori sono negati anche sotto il clima (20414/20415) → potati e DETTI
    assert saltati == ["blSeatAiry", "brSeatAiry"]
    assert nota and "clima" in nota


def test_ricomposizione_spegne_in_modo_simmetrico(core, P):
    """Lo spegnimento passa dalla stessa porta e spegne il clima, che è la verità: la macro
    accesa dal clima non si può fermare da un endpoint che questa vettura non autorizza."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_off"]
    ep, corpo, saltati, nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)
    assert (ep, corpo["airControlType"], nota is not None) == ("airControl", "0", True)
    assert "duration" not in corpo and corpo["times"] == "15"
    assert saltati == ["blSeatAiry", "brSeatAiry"]


def test_ricomposizione_muta_sullomoda9(core, P):
    """La macro del costruttore è aperta ⇒ non la si sostituisce con un'imitazione nostra.

    Vale come invariante per chi il componente ce l'ha installato: è già coperto dal no-op
    letterale su tutto il catalogo, ma questo lo inchioda al punto esatto — se un domani la
    guardia «la porta ufficiale è aperta» sparisse, l'Omoda 9 comincerebbe a spedire `airControl`
    al posto di `coolingControl` senza che nessun altro test lo dica a voce alta."""
    commands = core["commands"]
    for chiave in ("clima_raffredda_on", "clima_raffredda_off"):
        c = commands.CMD_MAP[chiave]
        assert P.ricomponi(c["endpoint"], dict(c["body"]), OMODA9) == (
            c["endpoint"], c["body"], None)


@pytest.mark.parametrize("perms", [None, {}], ids=["mai-letta", "illeggibile"])
def test_ricomposizione_senza_lista_non_agisce(core, P, perms):
    """Fallimento permissivo: la regola che ogni funzione nuova di questo modulo deve superare."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_on"]
    assert P.ricomponi(c["endpoint"], dict(c["body"]), perms or {}) == (
        c["endpoint"], c["body"], None)


def test_ricomposizione_non_scavalca_una_seconda_porta_chiusa(core, P):
    """Se anche il clima è negato non si ricompone: si spedisce come sempre e l'utente riceve il
    rifiuto vero. Ricomporre verso una porta chiusa non guadagnerebbe nulla e toglierebbe il
    verdetto preventivo, perché quello guarda l'endpoint **finale**."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_on"]
    for chiuso in ({**JAECOO, 204: 0},          # categoria del clima negata
                   {**JAECOO, 2041: 0}):        # cuore del clima negato, categoria aperta
        ep, corpo, nota = P.ricomponi(c["endpoint"], dict(c["body"]), chiuso)
        assert (ep, corpo, nota) == (c["endpoint"], c["body"], None)
        assert P.verdetto(ep, chiuso), "senza ricomposizione il verdetto deve restare"


def test_ricomposizione_scatta_anche_solo_per_il_cuore_negato(core, P):
    """I due segnali sono distinti e ne basta uno. Profilo **sintetico**: sulle liste reali che
    abbiamo, quando la voce base è negata lo è anche la categoria."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_on"]
    solo_cuore = {**JAECOO, 210: 1, 2103: 0}
    ep, _corpo, nota = P.ricomponi(c["endpoint"], dict(c["body"]), solo_cuore)
    assert (ep, nota is not None) == ("airControl", True)


def test_un_campo_non_traducibile_annulla_la_ricomposizione(core, P):
    """La guardia contro l'estensione distratta, ed è la più importante di questa sezione.

    Se al corpo di una macro ricomponibile si aggiungesse un campo per cui non conosciamo una
    voce sotto il clima — è il caso di `steerWheelHeatSwitch`, la ragione per cui `heatingControl`
    NON è in `RICOMPONI` — le uscite possibili sarebbero due: spedirlo a una porta che non
    sappiamo se lo accetta, o buttarlo via in silenzio. Entrambe sbagliate. Si annulla tutto: la
    macro parte intera, verrà rifiutata, e l'utente lo legge — che è lo stato precedente, non un
    peggioramento."""
    corpo = {"airControlType": "1", "airType": "1", "temperature": "15.0", "duration": "15",
             "mSeatAiry": "3", "campoMaiVisto": "1"}
    ep, uscito, nota = P.ricomponi("coolingControl", dict(corpo), JAECOO)
    assert (ep, uscito, nota) == ("coolingControl", corpo, None)


def test_il_caldo_non_si_ricompone(core, P):
    """`heatingControl` è fuori da `RICOMPONI` **di proposito** e il test lo dichiara.

    Non è una dimenticanza da correggere: `steerWheelHeatSwitch` non ha una voce nota sotto la
    204 (il volante ha categoria 208 e un endpoint proprio, che funziona), e su nessuna delle due
    liste reali la 209 è negata. Chi un giorno vorrà aggiungerlo deve prima misurare, e questo
    test è il punto in cui dichiararlo."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_riscalda_on"]
    caldo_negato = {**JAECOO, 209: 0, 2093: 0}
    assert P.ricomponi(c["endpoint"], dict(c["body"]), caldo_negato) == (
        c["endpoint"], c["body"], None)
    assert "heatingControl" not in P.RICOMPONI


def test_ricomposizione_solo_verso_campi_che_sappiamo_potare(core, P):
    """Guardia strutturale: ogni destinazione di `RICOMPONI` deve avere la sua tabella in
    `POTABILI`, altrimenti i campi accessori arriverebbero alla porta nuova **senza** essere
    validati contro le voci di quella categoria — cioè si ricomporrebbe alla cieca."""
    for origine, destinazione in P.RICOMPONI.items():
        assert destinazione in P.POTABILI, f"{origine}→{destinazione}: nessuna tabella di potatura"
        assert destinazione in P.CATEGORIA, f"{origine}→{destinazione}: categoria sconosciuta"
        assert destinazione in P.VOCE_BASE, f"{origine}→{destinazione}: voce base sconosciuta"


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


def test_send_ricompone_la_macro_freddo(core, cloud, ctx):
    """La catena intera, dal tasto all'URL: «Raffredda tutto» sul veicolo dell'issue #1.

    È il test che vale per tutti gli altri di questa sezione messi insieme, perché confronta il
    corpo che parte davvero con quello **misurato dal vivo** l'11 agosto 2026 — stessa vettura,
    stesso account, A00079 e sedili che ventilavano per davvero.

    Verifica anche i due messaggi che l'utente legge, e soprattutto quello che NON deve più
    leggere: il verdetto «il costruttore non autorizza affatto questa funzione» era vero finché
    la richiesta partiva verso la 210, ed è falso ora che parte verso la 204 — dirlo comunque
    farebbe concludere che l'aggiornamento non ha funzionato proprio a chi lo sta usando.

    ⚠️ `emit` e `avvisa` vanno passati **separati**, e non è un dettaglio di stile. Chi non passa
    `avvisa` lo riceve uguale a `emit` (`send` lo prevede), i due canali collassano e il test non
    può più distinguerli: verificato per mutazione che portando la nota di ricomposizione da
    `avvisa` a `emit` — cioè rimettendola sul canale effimero che il pezzo «avvisi visibili»
    esiste per abbandonare, dove restava leggibile 12 millisecondi — la suite restava tutta verde.
    Un avviso pubblicato solo su `emit` è un avviso che l'utente non legge."""
    commands = core["commands"]
    ctx.caps = dict(_SCHEDA_JAECOO)
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")
    detti, avvisi = [], []

    esito = commands.send(ctx, "clima_raffredda_on", emit=detti.append, avvisa=avvisi.append)

    chiamate = cloud.calls_to("/asc/vehicleControl/")
    assert len(chiamate) == 1
    assert chiamate[0]["path"].endswith("/airControl"), (
        f"la macro non è stata ricomposta: {chiamate[0]['path']}")
    corpo = {k: v for k, v in chiamate[0]["body"].items()
             if k not in ("clientType", "seq", "taskId", "vin", "appId", "sign")}
    assert corpo == {"airControlType": "1", "airType": "1", "temperature": "16.0",
                     "times": "15", "mSeatAiry": "3", "pSeatAiry": "3"}
    # sul canale che SOPRAVVIVE (`avvisa`), non su quello che il passaggio successivo copre
    assert any("ricomposto" in m for m in avvisi), f"la ricomposizione non è dichiarata: {avvisi}"
    assert any("salto" in m for m in avvisi), f"i due posteriori non sono dichiarati: {avvisi}"
    assert not any("non autorizza affatto" in m for m in avvisi + detti), (
        f"verdetto rimasto su un endpoint che ora è consentito: {avvisi + detti}")
    assert "saltate" in esito and "skipped" in esito


@pytest.mark.parametrize("caps,atteso", [
    ({}, "16.0"),                                                     # nessuna scheda
    ({"clima_lo": 12.0, "clima_hi": 34.0}, "16.0"),                   # solo gli estremi
    ({"clima_min": 18.0, "clima_max": 28.0}, "18.0"),                 # solo il range
    (dict(_SCHEDA_JAECOO), "16.0"),                                   # scheda completa
], ids=["nessuna-scheda", "solo-estremi", "solo-range", "completa"])
def test_la_macro_ricomposta_non_spedisce_mai_una_posizione_come_setpoint(core, cloud, ctx,
                                                                         caps, atteso):
    """Il difetto che questo test chiude, e le due schede che gli scivolavano attraverso.

    Nella macro `temperature` è la posizione LO — «il massimo freddo», che per costruzione sta
    FUORI dall'intervallo impostabile. Passando dal clima diventa un setpoint. `_limita_temperatura`
    da sola non basta: quando la vettura non dichiara il range impostabile ripiega su LO..HI, e
    LO..HI **contiene LO**, quindi il controllo passava sempre. Risultato: senza scheda partiva il
    `15.0` cablato per l'Omoda 9, e su una vettura che dichiara solo gli estremi partiva il suo LO
    (qui `12.0`). Il corpo **misurato** che il backend accetta porta `16.0`.

    La riga «solo-range» è quella che dimostra che non si è cablato un `16.0`: se la vettura dice
    di partire da 18 °C, si spedisce 18."""
    commands = core["commands"]
    ctx.caps = caps
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "clima_raffredda_on")

    corpo = cloud.calls_to("/asc/vehicleControl/airControl")[0]["body"]
    assert corpo["temperature"] == atteso


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


# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-10 — tre buchi chiusi dopo la revisione avversariale del pacchetto
# «funzioni inesplorate» (vedi 40_permessi/ e FUNZIONI_INESPLORATE_20260810.md).
# ─────────────────────────────────────────────────────────────────────────────


def test_disappannamento_potato_dove_negato(core):
    """`frontDefrosting` è accessorio: dove la voce 2045 è negata si toglie il campo e il
    clima parte lo stesso, invece di far rifiutare tutta la richiesta per un campo solo."""
    permessi = core["permessi"]
    senza = {**OMODA9, 2045: 0}

    corpo, saltati = permessi.pota("airControl",
                                   {"airControlType": "1", "airType": "1",
                                    "frontDefrosting": "1", "temperature": "21.0",
                                    "times": "15"}, senza)

    assert "frontDefrosting" not in corpo
    assert saltati == ["frontDefrosting"]
    # ciò che regge la richiesta resta: il clima si accende comunque
    assert corpo["airControlType"] == "1" and corpo["temperature"] == "21.0"


def test_disappannamento_intatto_sullomoda9(core):
    """Sulla nostra auto (2045 consentita) la potatura non deve toccare nulla."""
    permessi = core["permessi"]
    corpo_in = {"airControlType": "1", "airType": "1", "frontDefrosting": "1",
                "temperature": "21.0", "times": "15"}

    corpo, saltati = permessi.pota("airControl", dict(corpo_in), OMODA9)

    assert corpo == corpo_in and saltati == []


def test_antifurto_avvisa_prima_del_rifiuto(core, cloud, ctx):
    """L'antifurto usa `path` e non passa dalla potatura: fino alla v1.11.1 questo gli faceva
    saltare anche l'AVVISO, e su un veicolo con la sicurezza negata l'utente vedeva un `A00084`
    nudo — l'errore che la v1.10.1 aveva appena finito di correggere per gli altri comandi."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti({**OMODA9, 401: 0}))
    cloud.on("/act/theftAlarm/setSwitch", code="A00084")
    detti = []

    # il rifiuto arriva comunque (non lo si può evitare: non c'è nulla da potare) e resta un
    # fallimento vero → CommandError, così lo switch ottimistico torna indietro invece di
    # mostrare un finto successo. La novità è l'avviso che lo PRECEDE.
    with pytest.raises(commands.CommandError):
        commands.send(ctx, "antifurto_on", emit=detti.append)

    assert any("non autorizza affatto" in m for m in detti), detti
    # …e il comando parte lo stesso: l'avviso spiega, non censura
    assert cloud.count("/act/theftAlarm/setSwitch") == 1


def test_antifurto_nessun_avviso_dove_consentito(core, cloud, ctx):
    """Sulla nostra auto (401 consentita) l'avviso non deve comparire: sarebbe un allarme falso."""
    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(OMODA9))
    cloud.on("/act/theftAlarm/setSwitch", code="A00079")
    detti = []

    commands.send(ctx, "antifurto_on", emit=detti.append)

    assert not any("non autorizza affatto" in m for m in detti), detti


def test_ciclo_settimanale_negato_viene_annunciato(core):
    """Su un veicolo che consente solo il ciclo su giorni scelti (2131) e nega la settimana
    (2132), il nostro `cycleData` fisso a [1..7] verrà rifiutato: va detto PRIMA."""
    permessi = core["permessi"]
    invertito = {**OMODA9, 2131: 1, 2132: 0}
    corpo = {"mainSwitch": 1, "chargeAppointPlans": [
        {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": 480,
         "switchStatus": 1, "timeConsuming": 720}]}

    avviso = permessi.ciclo_non_autorizzato("chargeAppointControl", corpo, invertito)

    assert avviso and "tutti i giorni" in avviso


def test_ciclo_settimanale_ok_sullomoda9(core):
    """Sulla nostra auto è consentito proprio il ciclo di 7 giorni: nessun avviso."""
    permessi = core["permessi"]
    corpo = {"mainSwitch": 1, "chargeAppointPlans": [
        {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": 0,
         "switchStatus": 1, "timeConsuming": 720}]}

    assert permessi.ciclo_non_autorizzato("chargeAppointControl", corpo, OMODA9) is None


def test_ciclo_non_inventa_giorni(core):
    """⚠️ Il controllo deve solo AVVISARE. Correggere i giorni scelti dall'utente sarebbe peggio
    del rifiuto: un piano che parte in giorni che nessuno ha chiesto è un danno silenzioso."""
    permessi = core["permessi"]
    invertito = {**OMODA9, 2131: 1, 2132: 0}
    corpo = {"chargeAppointPlans": [{"cycleData": [1, 2, 3, 4, 5, 6, 7]}]}

    permessi.ciclo_non_autorizzato("chargeAppointControl", corpo, invertito)

    assert corpo["chargeAppointPlans"][0]["cycleData"] == [1, 2, 3, 4, 5, 6, 7]


def test_ciclo_lista_non_letta_non_avvisa(core):
    """Fallimento permissivo anche qui: senza lista non si spaventa l'utente."""
    permessi = core["permessi"]
    corpo = {"chargeAppointPlans": [{"cycleData": [1, 3, 5]}]}

    assert permessi.ciclo_non_autorizzato("chargeAppointControl", corpo, {}) is None


# ───────────────────── 6. il verdetto preventivo: dire perché arriverà un rifiuto ─────────────────────

def test_verdetto_e_potatura_convivono(core, P, cloud, ctx):
    """I due fatti non si escludono, ed è il difetto che questo verdetto viene a chiudere.

    Sul veicolo vero dell'issue #1 la macro freddo pota quattro sedili **e** ha la categoria 210
    negata. Finché i due rami erano alternativi, l'utente leggeva solo «salto i quattro sedili»,
    ne deduceva che il clima si sarebbe acceso, e non si accendeva.

    ⚠️ Si misura su ciò che l'utente **legge davvero**, cioè su `send()`. La prima stesura di
    questo test chiamava le due funzioni pure una dopo l'altra e verificava che entrambe avessero
    qualcosa da dire: verissimo, e del tutto inutile — rimettere l'`elif` in `send()` la lasciava
    verde, perché la convivenza dei due messaggi non sta nelle funzioni ma nel loro chiamante.

    ⚠️ Il profilo NON è più quello del veicolo dell'issue #1 tale e quale, ed è una perdita di cui
    vale la pena lasciare traccia. Su quella vettura la macro freddo ora viene **ricomposta** su
    `airControl` (categoria 204 aperta), quindi l'endpoint finale non è più negato e il verdetto —
    correttamente — tace. Qui serve un caso in cui la macro resti condannata: si chiude anche il
    clima. È un profilo **sintetico**, e va dichiarato tale: nessuna delle due liste reali che
    possediamo ha la 204 negata. Il difetto che questo test sorveglia (i due messaggi resi
    alternativi da un `elif`) vive però nel chiamante e non nel profilo."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_raffredda_on"]
    senza_scampo = {**JAECOO, 204: 0}          # sintetico: né la macro né il clima
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(senza_scampo))
    cloud.on("/asc/vehicleControl/", code="A00084")
    detti = []

    # la premessa: su questo profilo c'è davvero sia da potare sia da avvisare
    ep, _corpo, saltati, _nota = P.adatta(c["endpoint"], dict(c["body"]), senza_scampo)
    assert ep == c["endpoint"], "con il clima chiuso non ci si deve ricomporre da nessuna parte"
    assert saltati and P.verdetto(ep, senza_scampo)

    # il comando parte lo stesso e il backend lo rifiuta: il verdetto informa, non sopprime
    with pytest.raises(commands.CommandError):
        commands.send(ctx, "clima_raffredda_on", emit=detti.append)

    assert any("salto" in m for m in detti), f"manca l'elenco dei campi potati: {detti}"
    assert any("non autorizza affatto" in m for m in detti), (
        f"manca l'avviso che il comando è condannato comunque: {detti}")
    # ⚠️ …e i due messaggi devono REGGERE INSIEME. Non basta che ci siano entrambi: la prima
    # stesura li faceva convivere e poi diceva «non c'è nulla da adattare» subito dopo aver
    # elencato quattro campi adattati. Due righe vere una alla volta, che affiancate mentono.
    assert not any("nulla da adattare" in m for m in detti), (
        f"il verdetto nega l'elenco dei campi potati che lo precede: {detti}")


def test_i_due_avvisi_non_si_contraddicono(core, P):
    """La guardia sul TESTO, non sulla logica.

    Il verdetto esce accanto all'elenco dei campi potati, quindi non può contenere frasi che
    presuppongano di essere solo: «non c'è nulla da adattare» è vera nel ramo `path` (dove
    davvero non c'è corpo) e falsa accanto a una potatura. Se un domani qualcuno riscrive il
    messaggio dimenticandosene, questo test lo ferma prima dell'utente."""
    for messaggio in (P.MSG_CATEGORIA_NEGATA, P.MSG_BASE_NEGATA):
        assert "nulla da adattare" not in messaggio, (
            f"il messaggio presuppone che non ci sia stata potatura: {messaggio!r}")


def test_verdetto_dice_il_cuore_negato(core, P):
    """Il secondo ramo di `verdetto` — la voce BASE negata mentre la categoria è aperta.

    Serve perché `base_negata()` era codice morto e la Fase C lo resuscita: senza un test che
    lo inchiodi, si può cancellare il ramo e la suite resta verde (verificato per mutazione).

    ⚠️ Su nessuno dei due profili reali questo caso si presenta: quando la voce base è negata
    lo è anche la categoria, e vince `porta_chiusa`. Il profilo qui sotto è quindi **sintetico**
    e costruito apposta — prova che il ramo funziona, NON che esista un veicolo che lo produce."""
    solo_cuore_negato = {**OMODA9, 210: 1, 2103: 0}
    avviso = P.verdetto("coolingControl", solo_cuore_negato)
    assert avviso == P.MSG_BASE_NEGATA, (
        f"il ramo della voce base non parla: {avviso!r}")
    # e non si confonde col ramo della categoria, che ha la precedenza quando scatta
    assert P.verdetto("coolingControl", {**OMODA9, 210: 0, 2103: 0}) == P.MSG_CATEGORIA_NEGATA


def test_verdetto_muto_sullomoda9(core, P):
    """Il rumore nuovo per chi il componente ce l'ha già installato dev'essere **zero**.

    Sul nostro profilo il verdetto tace su tutto il catalogo tranne la ricarica immediata, dove
    la categoria 220 è negata anche da noi — e lì l'avviso usciva già prima di questa modifica."""
    commands = core["commands"]
    parlanti = set()
    for chiave, c in commands.CMD_MAP.items():
        if c.get("path") or not c.get("endpoint"):
            continue
        ep, _corpo, _s, _n = P.adatta(c["endpoint"], dict(c["body"]), OMODA9)
        if P.verdetto(ep, OMODA9):
            parlanti.add(chiave)
    assert parlanti == {"ricarica_start", "ricarica_stop"}, (
        f"messaggi nuovi non previsti sull'Omoda 9: {parlanti}")


def test_verdetto_senza_lista_tace(P):
    """Fallimento permissivo, la regola che ogni funzione nuova deve superare: senza lista
    permessi il componente si comporta esattamente come prima, quindi non avvisa di nulla."""
    assert P.verdetto("coolingControl", {}) is None
    assert P.verdetto("coolingControl", None) is None
    assert P.verdetto("", JAECOO) is None
    assert P.verdetto("endpointMaiVisto", JAECOO) is None      # ignoto = aperto


def test_verdetto_sta_nello_stato_di_home_assistant(core, P):
    """Lo stato di un'entità HA è troncato a 255 caratteri: un avviso tagliato a metà parola è
    peggio del non dirlo. Si misura col prefisso peggiore del catalogo, non a occhio."""
    commands = core["commands"]
    prefisso = max(len(c["name"]) for c in commands.CMD_MAP.values()) + 2   # "nome: "

    # ⚠️ La nota del ripiego è il messaggio PIÙ LUNGO dei tre e fino al 2026-08-10 era l'unico
    # non misurato da nessun test: si guardava solo `verdetto`. Si misura sul ramo peggiore
    # («accende» è più lungo di «spegne») ricavandola dal codice, non ricopiandola qui.
    c = commands.CMD_MAP["sedile_guida_caldo"]
    _ep, _corpo, nota = P.instrada(c["endpoint"], dict(c["body"]), JAECOO)
    assert nota, "premessa del test: su questo profilo il ripiego scatta davvero"
    assert prefisso + len(nota) <= 255, f"nota del ripiego: {prefisso + len(nota)} caratteri"
    for perms in (JAECOO, {**OMODA9, 214: 0, 2103: 0}):
        for ep in ("coolingControl", "seatControl", "heatingControl", "chargeStartStopControl"):
            avviso = P.verdetto(ep, perms)
            if avviso:
                assert prefisso + len(avviso) <= 255, f"{ep}: {prefisso + len(avviso)} caratteri"


def test_tabelle_senza_voci_morte(core, P):
    """Ogni riga delle tabelle deve corrispondere a un comando che esiste davvero.

    Una voce irraggiungibile non è innocua: il prossimo manutentore la legge come informazione
    sul backend, e non lo è. `remoteStart` e `appointmentTravel` erano rimaste così."""
    commands = core["commands"]
    endpoint_veri = {c["endpoint"] for c in commands.CMD_MAP.values() if c.get("endpoint")}
    assert set(P.CATEGORIA) <= endpoint_veri, (
        f"voci morte in CATEGORIA: {set(P.CATEGORIA) - endpoint_veri}")
    assert set(P.CICLO) <= endpoint_veri, (
        f"voci morte in CICLO: {set(P.CICLO) - endpoint_veri}")


# ───────────────────── 7. il corpo di ripiego incontra la scheda della vettura ─────────────────
#
# ⚠️ AVVERTENZA, da leggere prima di fidarsi di questi test.
# Il percorso di ripiego **non è mai stato eseguito da nessuno contro un backend vero**, e
# sull'Omoda 9 non è nemmeno raggiungibile (tutte le voci `204xx` di ripiego sono negate: lo
# dimostra `test_omoda9_nessun_comando_viene_toccato`). Quel che segue prova che il COMPONENTE
# costruisce il corpo che intendiamo — endpoint, campi, valori, messaggi. Non prova, e non può
# provare, che il backend Chery accetti quel corpo, né che la vettura esegua: quello sarebbe uno
# strato 2 che nessuna misura di questo filone ha mai raggiunto. Il primo a esercitarlo davvero
# sarà l'utente dell'issue #1.

# Scheda di una vettura PLAUSIBILE e più stretta della nostra: clima da 22 a 30 °C, solo 5 o 10
# minuti. ⚠️ La prima stesura di questi test dichiarava invece `clima_lo: 18 / clima_hi: 20`, e
# con quei numeri il test era verde perché misurava il vincolo sbagliato — vedi
# `test_limita_temperatura_usa_il_range_impostabile`. Quella scheda è implausibile perché un HI
# a 20 °C vorrebbe dire una vettura che al massimo del caldo fa 20°.
# ⚠️ Implausibile, NON impossibile: `const.capabilities_from_item` impone `lo <= min` e
# `hi >= max` **solo se il range impostabile è stato dichiarato e ritenuto plausibile**; senza
# `minTemperature`/`maxTemperature` quella coppia passerebbe senza alcun controllo di coerenza.
# L'argomento che regge è la vettura, non il filtro.
_SCHEDA_STRETTA = {"durate_aria": [5, 10], "clima_min": 22.0, "clima_max": 30.0}


def test_ripiego_rispetta_la_scheda_della_vettura(core, cloud, ctx):
    """Il difetto: il corpo di ripiego nasce DOPO gli adattatori alla scheda, quindi non li
    incontrava mai. `permessi.py` non conosce la vettura e mette 21.0 e 15 — i valori
    dell'Omoda 9 — su un'auto che magari ammette solo 5 e 10 minuti e non scende sotto i 22 °C.

    Si misura sul corpo che atterra davvero sull'URL, non sulla funzione pura: è l'unico punto
    in cui l'ordine delle chiamate dentro `send()` è osservabile."""
    commands = core["commands"]
    ctx.caps = dict(_SCHEDA_STRETTA)
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "sedile_guida_caldo")

    inviato = cloud.calls_to("/asc/vehicleControl/")[0]
    assert inviato["path"].endswith("/airControl"), "il ripiego deve essere scattato"
    assert inviato["body"]["times"] == "10", (
        f"durata non riportata nell'insieme ammesso: {inviato['body']['times']}")
    assert inviato["body"]["temperature"] == "22.0", (
        f"temperatura fuori dal range impostabile dichiarato: {inviato['body']['temperature']}")
    assert inviato["body"]["mSeatHeating"] == "3"   # il campo dell'utente resta intatto


def test_ripiego_non_annuncia_una_durata_che_l_utente_non_ha_scelto(core, cloud, ctx):
    """Correggere il corpo è giusto; annunciarlo qui non lo è.

    `_adatta_durata` dichiara sempre la correzione, e ha ragione a farlo quando il numero l'ha
    scelto l'utente col cursore «Durata clima». Nel ripiego il numero l'abbiamo messo noi: chi
    preme «Sedile guida riscaldato» leggerebbe «durata 15′ non ammessa da questa vettura → uso
    10′» senza aver mai visto una durata. Sarebbe lo stesso difetto — dire all'utente cose che
    non corrispondono a ciò che ha fatto — che questa versione toglie di mezzo altrove."""
    commands = core["commands"]
    ctx.caps = dict(_SCHEDA_STRETTA)
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")
    detti = []

    commands.send(ctx, "sedile_guida_caldo", emit=detti.append)

    assert not any("durata" in m for m in detti), (
        f"annunciata una durata che l'utente non ha mai scelto: {detti}")
    # …e il corpo è stato corretto lo stesso: silenzio non vuol dire inerzia
    assert cloud.calls_to("/asc/vehicleControl/")[0]["body"]["times"] == "10"
    # l'avviso che invece SERVE resta: l'utente deve sapere che parte anche il clima
    assert any("tramite il clima" in m for m in detti), detti


def test_la_durata_scelta_dall_utente_resta_annunciata(core, cloud, ctx):
    """Il rovescio del test precedente, che ne fissa il confine: il silenzio vale SOLO per il
    corpo di ripiego. Sul clima vero, dove il numero esce da un cursore, l'utente deve continuare
    a sapere che gliel'abbiamo cambiato — altrimenti vede 30 nell'interfaccia e l'auto ne fa 10."""
    commands = core["commands"]
    ctx.caps = dict(_SCHEDA_STRETTA)
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(OMODA9))
    cloud.on("/asc/vehicleControl/", code="A00079")
    detti = []

    commands.send(ctx, "clima_on", emit=detti.append, params={"times": "30"})

    assert any("durata" in m and "30" in m for m in detti), detti
    assert cloud.calls_to("/asc/vehicleControl/")[0]["body"]["times"] == "10"


def test_ripiego_senza_scheda_spedisce_come_prima(core, cloud, ctx):
    """La regola invariata di tutto il componente: se il backend non dichiara nulla, non si
    inventa nulla. Senza scheda tecnica il corpo di ripiego resta quello di `BASE_AIRCONTROL`."""
    commands = core["commands"]
    ctx.caps = {}
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "sedile_guida_caldo")

    corpo = cloud.calls_to("/asc/vehicleControl/")[0]["body"]
    assert (corpo["times"], corpo["temperature"]) == ("15", "21.0")


@pytest.mark.parametrize("caps,times,temperatura", [
    ({"durate_aria": [5, 10]}, "10", "21.0"),                     # solo le durate dichiarate
    ({"clima_min": 22.0, "clima_max": 30.0}, "15", "22.0"),       # solo il range impostabile
    ({"clima_lo": 15.0, "clima_hi": 31.0}, "15", "21.0"),         # solo gli estremi: 21° ci sta
], ids=["solo-durate", "solo-range", "solo-estremi"])
def test_ripiego_con_scheda_parziale(core, cloud, ctx, caps, times, temperatura):
    """Una vettura può dichiarare una cosa e tacere l'altra: `_caps_correnti` scrive le durate,
    il range e gli estremi in modo indipendente. Ciò che è dichiarato si rispetta, il resto resta
    com'era — non si deduce un range da una durata né viceversa.

    La riga «solo-estremi» porta i valori VERI dell'Omoda 9 (LO 15 / HI 31) e per questo non
    corregge nulla: è il caso normale, e serve a ricordare che LO/HI da soli quasi mai mordono —
    per questo non possono essere il vincolo principale."""
    commands = core["commands"]
    ctx.caps = dict(caps)
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    commands.send(ctx, "sedile_guida_caldo")

    corpo = cloud.calls_to("/asc/vehicleControl/")[0]["body"]
    assert (corpo["times"], corpo["temperature"]) == (times, temperatura)


@pytest.mark.parametrize("valore,caps,atteso", [
    ("21.0", {"clima_min": 16, "clima_max": 20}, "20.0"),      # sopra il massimo impostabile
    ("21.0", {"clima_min": 22, "clima_max": 30}, "22.0"),      # sotto il minimo impostabile
    ("21.0", {"clima_min": 16, "clima_max": 30}, "21.0"),      # già dentro: non si tocca
    ("21.0", {"clima_min": 22}, "21.0"),                       # dichiarazione incompleta
    ("21.0", {}, "21.0"),                                      # nessuna dichiarazione
    ("21.0", {"clima_lo": 15, "clima_hi": 20}, "20.0"),        # niente range: ripiego su LO/HI
    # entrambi dichiarati: vince min/max, che è il PRIMO della lista di precedenza — non il più
    # stretto. Oggi i due criteri coincidono (`lo <= min`, `hi >= max` quando il filtro di
    # `const` è attivo), quindi questo caso da solo non li distingue: a distinguerli è il caso
    # qui sotto, dove LO/HI sarebbe più stretto e non deve comunque vincere.
    ("21.0", {"clima_min": 22, "clima_max": 30,
              "clima_lo": 15, "clima_hi": 31}, "22.0"),
    ("17.0", {"clima_min": 16, "clima_max": 30,
              "clima_lo": 18, "clima_hi": 28}, "17.0"),        # LO/HI più stretto: NON vince
    ("21.0", {"clima_min": 30, "clima_max": 18}, "21.0"),      # range rovesciato: non si sceglie
    ("non un numero", {"clima_min": 16, "clima_max": 20}, "non un numero"),
])
def test_limita_temperatura(core, valore, caps, atteso):
    """Ogni forma inattesa deve valere «non toccare».

    ⚠️ Onestà su che cosa prova: le ultime due righe (range rovesciato, valore non numerico)
    sono difesa in profondità, **non** percorsi raggiungibili oggi. `coordinator._caps_correnti`
    scrive `clima_min`/`clima_max` solo insieme e solo dopo averli convertiti in `float`, e
    `const.capabilities_from_item` li rifiuta se non sono crescenti. Restano perché questa
    funzione è pubblica dentro il modulo e il prossimo chiamante potrebbe non sapere da dove
    arrivano quei valori."""
    commands = core["commands"]
    corpo = {"temperature": valore}
    commands._limita_temperatura(corpo, caps)
    assert corpo["temperature"] == atteso


def test_limita_temperatura_usa_il_range_impostabile(core):
    """Il difetto che questa revisione ha trovato, isolato in un test che lo fa fallire.

    La prima stesura limitava su `clima_lo`/`clima_hi`. Sembrava corretto, ma quelli sono le
    posizioni ESTREME LO/HI, che `const.capabilities_from_item` accetta solo se stanno **fuori**
    dal range impostabile (`lo <= min`, `hi >= max`). Quindi su una vettura vera che parte da
    22 °C — l'esempio con cui la funzione si presentava — il 21.0 del corpo di ripiego cadeva
    dentro LO..HI e restava intatto: la cura non curava il caso che dichiarava di curare.

    Qui la scheda è quella di una vettura possibile: range 22-30, estremi 15/31."""
    commands = core["commands"]
    scheda_realistica = {"clima_min": 22.0, "clima_max": 30.0,
                         "clima_lo": 15.0, "clima_hi": 31.0}
    corpo = {"temperature": "21.0"}
    commands._limita_temperatura(corpo, scheda_realistica)
    assert corpo["temperature"] == "22.0", (
        "limitato sugli estremi LO/HI invece che sul range impostabile: su questa scheda "
        "quel vincolo non morde mai")


def test_temperatura_corretta_ha_la_forma_dell_envelope(core):
    """Un decimale, sempre — `"22.0"`, non `"22"` né `"22.25"`.

    È l'unico punto in cui il componente **conia** un valore per il corpo invece di inoltrarne
    uno del catalogo o dell'utente, e la forma osservata negli envelope dell'app è `21.0`. Un
    `str(float)` nudo passerebbe tutti gli altri test — i valori in gioco sono interi — e
    divergerebbe solo su una scheda con mezzo grado, cioè sull'auto di qualcun altro."""
    commands = core["commands"]
    for minimo, atteso in ((22, "22.0"), (22.25, "22.2"), (18.5, "18.5")):
        corpo = {"temperature": "16.0"}
        commands._limita_temperatura(corpo, {"clima_min": minimo, "clima_max": 30})
        assert corpo["temperature"] == atteso


def test_limita_temperatura_non_inventa_il_campo(core):
    """Su un corpo senza `temperature` non se ne aggiunge una: spedire un campo che il comando
    non prevede è un modo per farsi rifiutare tutto."""
    commands = core["commands"]
    corpo = {"mSeatHeating": "3"}
    commands._limita_temperatura(corpo, {"clima_min": 22, "clima_max": 30})
    assert corpo == {"mSeatHeating": "3"}


def test_adatta_capability_non_tocca_il_ripiego(core):
    """Perché `adatta_capability` NON compare fra gli adattatori richiamati dopo il ripiego.

    Non è una scelta di stile: su `airControl` — l'unica destinazione possibile del ripiego —
    quella funzione è esclusa di proposito, perché lì `temperature` è una scelta dell'utente e
    non la posizione LO/HI di una macro. Chiamarla lì sarebbe una riga che non fa mai nulla,
    presentata come parte della cura. Questo test la inchioda: se un domani `airControl` entrasse
    in `_ESTREMO_PER_ENDPOINT`, il ripiego avrebbe due padroni sulla stessa chiave.

    La prima riga fissa anche la premessa di tutto il ragionamento — «airControl è l'unica
    destinazione possibile del ripiego» — che tre commenti danno per buona e nessuno verificava:
    se domani si aggiungesse una seconda destinazione, gli adattatori richiamati in `send()`
    dopo il cambio di porta andrebbero ripensati per quella."""
    commands = core["commands"]
    P = core["permessi"]
    destinazioni = set()
    for (endpoint, campo), (dedicata, alternativa) in P.RIPIEGO.items():
        # profilo costruito apposta: porta dedicata sbarrata, alternativa aperta
        perms = {P.CATEGORIA[endpoint]: 0, dedicata: 0, P.CATEGORIA["airControl"]: 1,
                 alternativa: 1}
        nuovo, _corpo, nota = P.instrada(endpoint, {campo: "3"}, perms)
        assert nota, f"{endpoint}/{campo}: il ripiego doveva scattare"
        destinazioni.add(nuovo)
    assert destinazioni == {"airControl"}, f"seconda destinazione di ripiego: {destinazioni}"
    assert "airControl" not in commands._ESTREMO_PER_ENDPOINT
    corpo = {"temperature": "21.0"}
    assert commands.adatta_capability("airControl", corpo,
                                      {"clima_lo": 18, "clima_hi": 30}) == {"temperature": "21.0"}


def test_omoda9_il_ripiego_non_e_nemmeno_raggiungibile(core, cloud, ctx):
    """L'invariante che protegge chi il componente ce l'ha già installato, misurata attraverso
    `send()` e non sulla funzione pura: sulla nostra auto nessun comando cambia porta, quindi
    tutto il codice della fase C resta materialmente irraggiungibile — comprese le due
    correzioni silenziose, che non possono toccare un corpo che non passa di lì."""
    commands = core["commands"]
    ctx.caps = dict(_SCHEDA_STRETTA)        # scheda stretta apposta: se scattasse, si vedrebbe
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(OMODA9))
    cloud.on("/asc/vehicleControl/", code="A00079")

    attesi = [(c["endpoint"], c["body"].get("temperature")) for c in commands.CMD_MAP.values()
              if c.get("endpoint") and not c.get("path")]
    for chiave, c in commands.CMD_MAP.items():
        if c.get("path") or not c.get("endpoint"):
            continue
        commands.send(ctx, chiave)

    inviati = [(ch["path"].rsplit("/", 1)[-1], ch["body"].get("temperature"))
               for ch in cloud.calls_to("/asc/vehicleControl/")]
    # Endpoint **e** temperatura: il solo endpoint non basterebbe a smascherare una chiamata a
    # `_limita_temperatura` fuori dal ripiego. Con questa scheda il clima parte da 22 °C, quindi
    # una limitazione che sfuggisse trasformerebbe il 21.0 del catalogo in 22.0 — visibile qui e
    # invisibile a un confronto sui soli endpoint. (`times`, invece, è corretto per davvero anche
    # sull'Omoda 9: quella è la correzione dichiarata di `_adatta_durata`, e ci deve essere.)
    assert inviati == attesi, "un comando ha cambiato porta o temperatura sull'Omoda 9"


# ───────────────────── 8. i sospetti: quello che non sappiamo, detto come tale ─────────────────

def test_sospetti_non_toccano_il_corpo(core, P):
    """`times` somiglia alla voce 2044, ma somigliare non è mappare. La somiglianza sta in un
    log; il corpo parte intero. In questo progetto una mappatura per nome ha già prodotto un
    errore (`timeConsuming` → 2134), e su un veicolo dove 2044 è negata potare `times`
    romperebbe il clima per un'ipotesi."""
    commands = core["commands"]
    c = commands.CMD_MAP["clima_on"]
    _ep, corpo, saltati, _nota = P.adatta(c["endpoint"], dict(c["body"]), JAECOO)

    # la cifra citata nel commento di `SOSPETTI_NON_MAPPATI`: un numero scritto in un commento e
    # controllato da nessuno diventa falso al primo comando aggiunto.
    assert sum(1 for v in commands.CMD_MAP.values() if "times" in v.get("body", {})) == 14
    assert JAECOO[2044] == 0, "il profilo reale nega davvero quella voce"
    assert "times" in corpo, "il corpo non si tocca: la corrispondenza non è provata"
    assert "times" not in saltati
    assert P.sospetti(corpo, JAECOO) == [("times", 2044)], "…ma il dubbio va registrato"


def test_send_registra_il_sospetto_senza_toccare_il_corpo(core, cloud, ctx, caplog):
    """Il ponte fra `sospetti()` e il mondo reale, che altrimenti nessuno esercita.

    Senza questo test si potrebbe cancellare il giro di log dentro `send()` e la suite resterebbe
    verde: la funzione pura sarebbe provata, il suo unico chiamante no — cioè lo stesso difetto
    (una riga che nessuno verifica) che questa fase è venuta a chiudere altrove. Qui si guarda
    che la riga esca **e** che il `times` parta intatto: il sospetto è una nota, non una potatura."""
    import logging

    commands = core["commands"]
    cloud.on("/tsp/v1/app/vmc/queryVehicleAuthority", _permessi_finti(JAECOO))
    cloud.on("/asc/vehicleControl/", code="A00079")

    with caplog.at_level(logging.DEBUG):
        commands.send(ctx, "clima_on")

    righe = [r.getMessage() for r in caplog.records if "permessi" in r.getMessage()]
    assert any("times" in r and "2044" in r for r in righe), righe
    assert cloud.calls_to("/asc/vehicleControl/")[0]["body"]["times"] == "15"


def test_sospetti_muti_sullomoda9(core, P):
    """Sul nostro profilo la voce 2044 è consentita: nessun sospetto, nessuna riga di log."""
    commands = core["commands"]
    for c in commands.CMD_MAP.values():
        if not c.get("endpoint"):
            continue
        assert P.sospetti(dict(c["body"]), OMODA9) == []


def test_sospetti_senza_lista_tacciono(P):
    """Fallimento permissivo, la regola che ogni funzione nuova deve superare."""
    assert P.sospetti({"times": "15"}, {}) == []
    assert P.sospetti({"times": "15"}, None) == []
    assert P.sospetti({}, JAECOO) == []


def test_sospetti_restano_fuori_dalle_tabelle_che_decidono(core, P):
    """La guardia strutturale: finché una corrispondenza è solo sospetta non può stare dove il
    codice pota o instrada. Se qualcuno spostasse `times` in `POTABILI` per «completezza», il
    corpo del clima cambierebbe su un'auto vera sulla base di un'ipotesi mai verificata."""
    sospette = set(P.SOSPETTI_NON_MAPPATI)
    for endpoint, tabella in P.POTABILI.items():
        assert sospette.isdisjoint(tabella), f"{endpoint}: una chiave sospetta è diventata potabile"
    assert sospette.isdisjoint({campo for _ep, campo in P.RIPIEGO})
