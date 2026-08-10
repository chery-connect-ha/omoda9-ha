"""La scheda tecnica della vettura al posto delle costanti cablate.

Fino alla v1.12.1 le macro «Raffredda tutto»/«Riscalda tutto» spedivano `temperature`
15.0 e 31.0, e ogni comando comfort una durata di 15 minuti. Sono i valori dell'**Omoda 9**,
scritti a mano come se valessero per tutta la gamma. Il backend li dichiara per-veicolo in
`queryList` — la stessa risposta da cui prendiamo già nome e `powerType`, quindi zero
chiamate in più.

Questi test bloccano il confine che conta: **si cambia qualcosa solo quando il backend
dichiara**. Un backend muto deve produrre esattamente il corpo di prima, altrimenti la
riscrittura diventa un modo silenzioso per rompere l'auto di qualcun altro.
"""
from __future__ import annotations

import pytest

from custom_components.omoda9.const import (
    DATA_AIR_DURATIONS,
    DATA_CLIMATE_HI,
    DATA_CLIMATE_LO,
    DATA_CLIMATE_MAX,
    DATA_CLIMATE_MIN,
    capabilities_from_item,
)
from tests.core_loader import load_core

commands = load_core()["commands"]


# ───────────────────────── lettura della scheda da queryList ─────────────────────────
def test_estremi_lo_hi_letti_quando_la_vettura_li_dichiara():
    """I valori veri dell'Omoda 9, presi dalla risposta reale del 2026-08-10."""
    caps = capabilities_from_item({
        "isHaveLoAndHi": 1, "loValue": 15.0, "hiValue": 31.0,
        "minTemperature": 16.0, "maxTemperature": 30.0})
    assert caps[DATA_CLIMATE_LO] == 15.0
    assert caps[DATA_CLIMATE_HI] == 31.0


def test_senza_lo_e_hi_non_si_inventa_una_chiave():
    """`isHaveLoAndHi = 0` non è un dato mancante: dice che gli estremi SONO min/max.
    Una chiave in più direbbe la stessa cosa due volte e potrebbe divergere."""
    caps = capabilities_from_item({
        "isHaveLoAndHi": 0, "loValue": 15.0, "hiValue": 31.0,
        "minTemperature": 16.0, "maxTemperature": 30.0})
    assert DATA_CLIMATE_LO not in caps and DATA_CLIMATE_HI not in caps


@pytest.mark.parametrize("item", [
    {"isHaveLoAndHi": 1, "loValue": 31.0, "hiValue": 15.0},          # invertiti
    {"isHaveLoAndHi": 1, "loValue": 15.0, "hiValue": 15.0},          # degeneri
    {"isHaveLoAndHi": 1, "loValue": -5.0, "hiValue": 31.0},          # fuori scala
    {"isHaveLoAndHi": 1, "loValue": 15.0, "hiValue": 99.0},          # fuori scala
    {"isHaveLoAndHi": 1, "loValue": "boh", "hiValue": 31.0},         # non numerico
    {"isHaveLoAndHi": 1, "hiValue": 31.0},                           # incompleto
])
def test_estremi_implausibili_scartati(item):
    caps = capabilities_from_item(item)
    assert DATA_CLIMATE_LO not in caps and DATA_CLIMATE_HI not in caps


def test_estremi_devono_stare_fuori_dal_range_dichiarato():
    """LO sta sotto il minimo e HI sopra il massimo: è la definizione. Se il backend manda
    un LO *dentro* il range, il campo non è quello che crediamo → meglio non usarlo che
    spedire un «massimo freddo» più caldo del normale."""
    caps = capabilities_from_item({
        "isHaveLoAndHi": 1, "loValue": 20.0, "hiValue": 31.0,
        "minTemperature": 16.0, "maxTemperature": 30.0})
    assert DATA_CLIMATE_LO not in caps


def test_durate_lette_come_insieme():
    caps = capabilities_from_item({"maxAirDuration": "5,10,15"})
    assert caps[DATA_AIR_DURATIONS] == [5, 10, 15]


@pytest.mark.parametrize("valore, atteso", [
    ("15", [15]),
    (" 5 , 10 ", [5, 10]),
    ("10,5,10", [5, 10]),        # disordinate e con doppioni
    ("5,0,10", [5, 10]),         # lo zero non è una durata
    ("5,999", [5]),              # oltre l'ora = dato sbagliato, non vettura esotica
])
def test_durate_normalizzate(valore, atteso):
    assert capabilities_from_item({"maxAirDuration": valore})[DATA_AIR_DURATIONS] == atteso


@pytest.mark.parametrize("item", [{}, {"maxAirDuration": ""}, {"maxAirDuration": "x"},
                                  {"maxAirDuration": "0"}, {"maxAirDuration": None}])
def test_durate_illeggibili_non_finiscono_in_cache(item):
    assert DATA_AIR_DURATIONS not in capabilities_from_item(item)


# ───────────────────────── scelta della durata da spedire ─────────────────────────
@pytest.mark.parametrize("voluta, durate, atteso", [
    (15, [5, 10, 15], None),   # già ammessa: non si tocca
    (15, [5, 10], 10),         # si scende al più grande ammesso
    (12, [5, 10, 15], 10),     # idem, valore intermedio
    (3,  [5, 10, 15], 5),      # si è chiesto meno del minimo → il minimo
    (0,  [5, 10], 5),          # zero e negativi non sono un caso a parte
    (-4, [5, 10], 5),
    (10, [10], None),          # insieme con un solo valore, già ammesso
    (99, [10], 10),
    ("15", [5, 10], 10),       # il corpo trasporta stringhe
    (15, [], None),            # nessuna dichiarazione: non si corregge
    ("x", [5, 10], None),      # richiesta illeggibile: non si indovina
])
def test_durata_ammessa(voluta, durate, atteso):
    assert commands.durata_ammessa(voluta, durate) == atteso


# ───────────────────────── adattamento del corpo del comando ─────────────────────────
def test_estremo_freddo_e_caldo_presi_dalla_scheda():
    caps = {"clima_lo": 17.0, "clima_hi": 28.0}
    freddo = commands.adatta_capability("coolingControl", {"temperature": "15.0"}, caps)
    caldo = commands.adatta_capability("heatingControl", {"temperature": "31.0"}, caps)
    assert freddo["temperature"] == "17.0"
    assert caldo["temperature"] == "28.0"


def test_backend_muto_lascia_il_corpo_identico():
    """Il caso che protegge tutti gli utenti attuali: nessuna dichiarazione ⇒ byte per byte
    quello che si spediva prima."""
    corpo = {"temperature": "15.0", "duration": "15"}
    assert commands.adatta_capability("coolingControl", dict(corpo), {}) == corpo
    assert commands.adatta_capability("coolingControl", dict(corpo), None) == corpo


def test_omoda9_non_cambia_nulla():
    """Sulla vettura di sviluppo i valori dichiarati coincidono con quelli cablati: il
    corpo spedito dev'essere identico a prima. Se questo test si rompe, l'adattamento sta
    cambiando comportamento su un'auto su cui non deve cambiare niente."""
    caps = {"clima_lo": 15.0, "clima_hi": 31.0, "durate_aria": [5, 10, 15]}
    corpo = {"airControlType": "1", "temperature": "15.0", "duration": "15"}
    atteso = dict(corpo)
    body = commands.adatta_capability("coolingControl", dict(corpo), caps)
    commands._adatta_durata("coolingControl", body, caps)
    assert body == atteso


def test_airControl_non_viene_toccato():
    """La temperatura del clima la sceglie l'utente dalla card: non è un estremo di
    vettura e non deve essere riscritta."""
    corpo = {"airControlType": "1", "temperature": "21.0"}
    caps = {"clima_lo": 15.0, "clima_hi": 31.0}
    assert commands.adatta_capability("airControl", dict(corpo), caps) == corpo


def test_durata_corretta_in_entrambi_i_nomi():
    """`times` per airControl e comfort, `duration` per le macro cooling/heating: due nomi
    per la stessa grandezza, entrambi vanno riportati nell'insieme ammesso."""
    caps = {"durate_aria": [5, 10]}
    b1 = {"times": "15"}
    b2 = {"duration": "15"}
    commands._adatta_durata("airControl", b1, caps)
    commands._adatta_durata("coolingControl", b2, caps)
    assert b1["times"] == "10" and b2["duration"] == "10"


def test_durata_scelta_dall_utente_comunque_validata():
    """Una durata fuori insieme è invalida da chiunque arrivi: anche dal selettore di HA."""
    caps = {"durate_aria": [5, 10]}
    body = {"times": "15"}          # come se venisse da number.omoda9_clima_durata
    commands._adatta_durata("airControl", body, caps)
    assert body["times"] == "10"


def test_la_correzione_della_durata_viene_dichiarata():
    """Il cursore arriva a 30′, l'Omoda 9 ne ammette 15: chi imposta 30 deve SAPERE che
    all'auto ne sono arrivati 15. Tutti gli altri adattamenti lo dicono; questo non può
    essere l'unico muto — è un numero scelto a mano dall'utente."""
    detti: list[str] = []
    commands._adatta_durata("airControl", {"times": "30"}, {"durate_aria": [5, 10, 15]},
                            detti.append)
    assert detti and "30" in detti[0] and "15" in detti[0]


def test_nessun_avviso_se_non_si_corregge_nulla():
    """Un messaggio per una correzione che non c'è stata è rumore che fa dubitare."""
    detti: list[str] = []
    commands._adatta_durata("airControl", {"times": "15"}, {"durate_aria": [5, 10, 15]},
                            detti.append)
    assert detti == []


@pytest.mark.parametrize("endpoint", ["seatControl", "frontWindshieldControl",
                                      "backDefrostingControl"])
def test_durata_non_toccata_fuori_dal_clima(endpoint):
    """`maxAirDuration` è la durata dell'**aria**. Il campo `times` compare anche sugli 8
    comandi dei sedili e sulle due resistenze dei vetri: sono riscaldatori elettrici, che
    quel campo non governa. Correggerli accorcerebbe il sedile riscaldato per una regola
    che non lo riguarda — invisibile qui (tutto 15), sbagliato su un'altra vettura."""
    body = {"mSeatHeating": "3", "times": "15"}
    commands._adatta_durata(endpoint, body, {"durate_aria": [5, 10]})
    assert body["times"] == "15"


# ───────────── il cablaggio: dalle capability in entry.data al corpo spedito ─────────────
# I test qui sopra esercitano due funzioni pure. Il difetto che una revisione avversariale
# ha trovato nella prima stesura non stava lì: stava nel PONTE fra `entry.data` e `ctx.caps`,
# dove un ripiego «se non c'è LO/HI usa min/max» trasformava un'assenza in una dichiarazione
# inventata e faceva spedire 16.0/30.0 al posto dei 15.0/31.0 di sempre. La suite era verde.
def _coord_con(data: dict):
    """Il minimo per esercitare i metodi del coordinator senza avviare Home Assistant."""
    from custom_components.omoda9.coordinator import Omoda9Coordinator

    c = type("C", (), {})()
    c.entry = type("E", (), {"data": data, "options": {}})()
    c.climate_limits = lambda: Omoda9Coordinator.climate_limits(c)
    c.climate_extremes = lambda: Omoda9Coordinator.climate_extremes(c)
    c.air_durations = lambda: Omoda9Coordinator.air_durations(c)
    c._caps_correnti = lambda: Omoda9Coordinator._caps_correnti(c)
    return c


def test_niente_dichiarazioni_niente_capability():
    """Il caso di gran lunga più comune: nessuna chiave ⇒ dizionario VUOTO, non valori di
    ripiego. `core/` deve poter distinguere «assente» da «dichiarato»."""
    assert _coord_con({})._caps_correnti() == {}


def test_estremi_non_ripiegano_sul_range():
    """La trappola: senza LO/HI gli estremi *sembrano* essere min e max. Non lo sono — o
    meglio, non lo sappiamo, e spedire 16/30 al posto di 15/31 cambia il comportamento di
    utenti funzionanti sulla base di un dato che il backend non ha mai dato."""
    coord = _coord_con({DATA_CLIMATE_MIN: 16.0, DATA_CLIMATE_MAX: 30.0})
    assert coord.climate_extremes() == (None, None)
    assert "clima_lo" not in coord._caps_correnti()


def test_corpo_identico_alla_1_12_1_quando_il_backend_tace():
    """Il test che vale per tutti gli utenti già installati: senza dichiarazioni il corpo
    spedito dev'essere quello di sempre, campo per campo. È il test che nella prima stesura
    mancava — e che avrebbe intercettato la regressione al primo giro."""
    caps = _coord_con({})._caps_correnti()
    atteso = {"airControlType": "1", "airType": "1", "temperature": "15.0", "duration": "15"}
    body = commands.adatta_capability("coolingControl", dict(atteso), caps)
    commands._adatta_durata("coolingControl", body, caps)
    assert body == atteso


def test_capability_dichiarate_arrivano_fino_al_corpo():
    """E il verso opposto: quando il backend dichiara, il valore dev'essere quello suo.
    Senza questo, «non cambiare mai niente» passerebbe tutti i test qui sopra."""
    coord = _coord_con({DATA_CLIMATE_LO: 17.0, DATA_CLIMATE_HI: 28.0,
                        DATA_AIR_DURATIONS: [5, 10]})
    caps = coord._caps_correnti()
    body = commands.adatta_capability("coolingControl",
                                      {"temperature": "15.0", "duration": "15"}, caps)
    commands._adatta_durata("coolingControl", body, caps)
    assert body == {"temperature": "17.0", "duration": "10"}


def test_il_range_impostabile_arriva_a_core_come_dichiarazione_a_se():
    """Il range (min/max) e gli estremi (LO/HI) devono viaggiare come **due** dichiarazioni.

    Serve al corpo di ripiego su `airControl`, che porta un 21.0 messo da noi: per sapere se è
    ammesso bisogna guardare il range impostabile. Gli estremi non bastano — per costruzione
    stanno FUORI da quel range (`capabilities_from_item` rifiuta la coppia se `lo > min` o
    `hi < max`), quindi un setpoint fuori dal range può benissimo cadere dentro LO..HI.

    ⚠️ E resta una dichiarazione, non un default: `climate_limits()` ricade su 16-30 quando il
    backend tace, ma quel 16-30 non deve mai arrivare a `core/`, altrimenti l'assenza diventa
    indistinguibile da una risposta vera.

    ⚠️ Sul «per costruzione stanno FUORI»: `capabilities_from_item` lo impone solo quando il
    range è stato dichiarato. Qui lo si dichiara, quindi vale."""
    coord = _coord_con({DATA_CLIMATE_MIN: 22.0, DATA_CLIMATE_MAX: 30.0,
                        DATA_CLIMATE_LO: 15.0, DATA_CLIMATE_HI: 31.0})
    caps = coord._caps_correnti()
    assert (caps["clima_min"], caps["clima_max"]) == (22.0, 30.0)
    assert (caps["clima_lo"], caps["clima_hi"]) == (15.0, 31.0)

    corpo = {"temperature": "21.0"}
    commands._limita_temperatura(corpo, caps)
    assert corpo["temperature"] == "22.0"

    # senza dichiarazione niente chiavi: il default 16-30 di `climate_limits()` resta in HA
    assert coord.climate_limits()[:2] == (22.0, 30.0)
    vuoto = _coord_con({})._caps_correnti()
    assert "clima_min" not in vuoto and "clima_max" not in vuoto


@pytest.mark.parametrize("dati", [
    {DATA_CLIMATE_MIN: 22.0},                      # solo il minimo
    {DATA_CLIMATE_MAX: 30.0},                      # solo il massimo
    {DATA_CLIMATE_MIN: 22.0, DATA_CLIMATE_MAX: "non un numero"},
], ids=["solo-min", "solo-max", "sporco"])
def test_mezzo_range_non_e_una_dichiarazione(dati):
    """Metà intervallo non è un intervallo: o entrambe le chiavi o nessuna.

    Una `clima_min` da sola che arrivasse a `core/` sarebbe un vincolo a una coda sola, e la
    regola del componente è che ciò che non è dichiarato non esiste. Il caso «sporco» copre
    `entry.data`, che passa da JSON e può contenere qualunque cosa."""
    caps = _coord_con(dati)._caps_correnti()
    assert "clima_min" not in caps and "clima_max" not in caps, caps


def test_durate_corrotte_in_entry_data_non_rompono_i_comandi():
    """`entry.data` passa da JSON e può tornare indietro sporca. Meglio nessuna capability
    che un'eccezione dentro la property `ctx`, che romperebbe OGNI comando."""
    assert _coord_con({DATA_AIR_DURATIONS: ["x", None]}).air_durations() == []
    assert _coord_con({DATA_AIR_DURATIONS: "5,10"}).air_durations() == []
    assert _coord_con({DATA_CLIMATE_LO: "boh", DATA_CLIMATE_HI: 31.0}).climate_extremes() \
        == (None, None)


def test_il_contesto_non_riceve_capability_inventate(tmp_path):
    """Il punto ESATTO in cui il difetto era stato iniettato: `_build_ctx`.

    I test qui sopra verificano `_caps_correnti()`, ma il `CoreCtx` potrebbe benissimo
    riempirsi le capability per conto suo — ed è quello che faceva la prima stesura. Una
    revisione avversariale ha dimostrato il buco sostituendo il parametro `caps=` con dei
    valori assurdi: la suite restava **tutta verde**. Questo test esercita il costruttore
    vero, così quella mutazione non passa più."""
    from custom_components.omoda9.coordinator import Omoda9Coordinator

    c = type("C", (), {})()
    c.entry = type("E", (), {"data": {}, "options": {}})()
    c.vin, c.tuserid, c.pin = "VINFINTO", "1", "0000"
    c.email, c.phone, c.area_code = "x@y.z", "", "39"
    c.token_path = str(tmp_path / "token.json")
    c.tsp_host, c.bff, c.channel_id = "https://tsp.invalid", "https://bff.invalid", "1"
    c.hass = type("H", (), {"config": type("Cf", (), {"path": staticmethod(str)})()})()
    for nome in ("climate_limits", "climate_extremes", "air_durations", "_caps_correnti"):
        setattr(c, nome, (lambda n: lambda: getattr(Omoda9Coordinator, n)(c))(nome))

    ctx = Omoda9Coordinator._build_ctx(c)
    assert ctx.caps == {}, (
        "senza dichiarazioni del backend il contesto non deve trasportare capability: "
        f"trovate {ctx.caps}")


def test_marcatore_versionato():
    """Se qualcuno aggiunge una capability senza aggiungere un marcatore, gli entry già
    installati non la leggeranno mai: hanno il marcatore vecchio e la lettura esce subito."""
    from custom_components.omoda9.const import DATA_CAPS_PROBED, DATA_CAPS_PROBED_V2
    assert DATA_CAPS_PROBED != DATA_CAPS_PROBED_V2
