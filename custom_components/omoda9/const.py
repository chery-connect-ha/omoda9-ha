"""Costanti del custom component Omoda 9 / Jaecoo."""

DOMAIN = "omoda9"
PLATFORMS = ["sensor", "binary_sensor", "button", "lock", "switch", "climate",
             "number", "time", "cover", "device_tracker", "text"]

# Campi auto (5A02) ora rappresentati da entità native ATTUABILI (lock/switch/cover):
# esclusi dalla creazione di sensor/binary_sensor "di sola lettura" per non duplicarli.
# I campi comfort (sbrinamenti/volante/sedili guida-passeggero-posteriori) sono ora
# interruttori ON/OFF (vedi switch.py). NB: il sedile posteriore CENTRALE
# (mSeatHeatingState2/mSeatVentilateState2) NON ha un comando dedicato → resta sola lettura.
FIELDS_AS_RICH_ENTITY = {
    "doorLock", "frontHVACState", "trunkDoor", "sunroofState",
    "frontWindshieldHeat", "rWinHeatingState", "steerWheelHeating",
    "dSeatHeatingState", "dSeatVentilateState",
    # sedile passeggero
    "pSeatHeatingState", "pSeatVentilateState",
    # sedili posteriori SX/DX (telemetria *State2 ↔ comando bl/br SeatControl)
    "lSeatHeatingState2", "lSeatVentilateState2",
    "rSeatHeatingState2", "rSeatVentilateState2",
}

# Comandi del catalogo ora gestiti da lock/switch/cover → esclusi dai pulsanti singoli
# (il tap sul lock/switch/cover invoca lo stesso comando del catalogo).
COMMANDS_AS_RICH_ENTITY = {
    "blocca", "sblocca",
    # clima_on/clima_off ora pilotati dalla climate entity (climate.py) → niente pulsanti.
    "clima_on", "clima_off",
    # ricarica EV: switch dedicati (switch.py) → niente pulsanti singoli.
    # NB: `avvio_remoto` NON è qui → resta un pulsante (button.omoda9_avvio_remoto).
    "ricarica_start", "ricarica_stop", "ricarica_prog_on", "ricarica_prog_off",
    "baule_apri", "baule_chiudi",
    "finestrini_apri", "finestrini_chiudi",
    "tetto_apri", "tetto_chiudi",
    # comfort: ogni funzione è uno switch (ON+OFF) → niente pulsanti singoli
    "defrost_parabrezza", "defrost_parabrezza_off",
    "disappanna_parabrezza", "disappanna_parabrezza_off",
    "defrost_lunotto", "defrost_lunotto_off",
    "volante_caldo", "volante_caldo_off",
    "sedile_guida_caldo", "sedile_guida_caldo_off",
    "sedile_guida_aria", "sedile_guida_aria_off",
    "sedile_passeggero_caldo", "sedile_passeggero_caldo_off",
    "sedile_passeggero_aria", "sedile_passeggero_aria_off",
    "sedile_post_sx_caldo", "sedile_post_sx_caldo_off",
    "sedile_post_sx_aria", "sedile_post_sx_aria_off",
    "sedile_post_dx_caldo", "sedile_post_dx_caldo_off",
    "sedile_post_dx_aria", "sedile_post_dx_aria_off",
}

# Chiavi del config_entry (dati per-account, inseriti nel config flow)
CONF_EMAIL = "email"
CONF_PIN = "pin"
CONF_VIN = "vin"
CONF_TUSERID = "tuserid"
# Login via SMS (telefono): alternativa all'email. Alcuni account sono registrati col
# numero e NON hanno email → per loro il login email fallisce. Se `phone` è valorizzato
# nell'entry, il login usa il ramo SMS (invio codice via sendSmsCode + grant_type=mobile).
CONF_PHONE = "phone"
CONF_AREA_CODE = "area_code"     # prefisso internazionale in sole cifre (Italia = 39)
DEFAULT_AREA_CODE = "39"

# Lingua delle chiamate al backend: guida l'header `Accept-Language`, che a sua volta decide la
# lingua di e-mail OTP, SMS e messaggi del server (il backend non ha un parametro `lang` sul
# codice: comanda l'header). Il valore memorizzato È il valore dell'header (`en-GB`/`it-IT`).
#   * setup ESISTENTI (nessun campo `language`) → `LANGUAGE_FALLBACK` = it-IT: comportamento
#     storico invariato;
#   * setup NUOVI → il dropdown parte da `DEFAULT_LANGUAGE` = en-GB (questo fork è in inglese).
CONF_LANGUAGE = "language"
DEFAULT_LANGUAGE = "en-GB"       # default del dropdown per i NUOVI account
LANGUAGE_FALLBACK = "it-IT"      # entry senza il campo → comportamento storico
LANGUAGES = {"en-GB": "English", "it-IT": "Italiano"}   # valore-header → etichetta del dropdown

# Identità veicolo per il device HA (nome dinamico: "Omoda 9", "Jaecoo 7"…). `vehicle_name`
# = nickname/modello dall'app, salvato in entry.data (catturato al config flow o backfillato);
# è anche un'OPZIONE per l'override manuale. model/brand restano solo in entry.data.
CONF_VEHICLE_NAME = "vehicle_name"
DATA_VEHICLE_MODEL = "vehicle_model"
DATA_VEHICLE_BRAND = "vehicle_brand"
# fallback quando il modello non è (ancora) noto
DEFAULT_VEHICLE_NAME = "Omoda 9 / Jaecoo"

# ── Capability per-veicolo (dalla stessa risposta `queryList` dell'identità) ──────────────
# Il componente nasce su una Omoda 9 PHEV; il canale telemetria però è lo stesso per tutti i
# modelli e i BEV (Omoda E5…) mandano un sottoinsieme diverso di campi. Queste chiavi servono
# a NON indovinare: si adatta il comportamento solo quando il backend dichiara esplicitamente
# la capability. Assente/illeggibile ⇒ ci si comporta come si è sempre fatto.
#
# ⚠️ REGOLA: `power_type` va usato SOLO tramite `Omoda9Coordinator.is_pure_electric()`, che è
# vera unicamente per BEV CONFERMATO (powerType == 0). "Sconosciuto" non è "elettrica".
DATA_POWER_TYPE = "power_type"        # 0 = solo elettrica (BEV); altro/None = ha un motore termico
DATA_CLIMATE_MIN = "climate_min_temp"
DATA_CLIMATE_MAX = "climate_max_temp"
DATA_CLIMATE_STEP = "climate_temp_step"
# Estremi LO/HI: le posizioni oltre il range normale (sull'Omoda 9: 15.0 e 31.0, contro un
# range 16-30). Sono i valori che le macro "Raffredda tutto"/"Riscalda tutto" spediscono per
# dire «il massimo che questa vettura sa fare», e fino alla v1.12.1 erano cablati a mano.
# Presenti SOLO se il backend dichiara `isHaveLoAndHi`: senza LO/HI gli estremi coincidono
# con min/max e non serve una chiave in più.
DATA_CLIMATE_LO = "climate_lo"
DATA_CLIMATE_HI = "climate_hi"
# Durate ammesse per il clima, in minuti (`maxAirDuration`, es. "5,10,15"). È un INSIEME, non
# un massimo, malgrado il nome: spedire un valore fuori insieme è spedire un valore invalido.
DATA_AIR_DURATIONS = "air_durations"
# Marcatore "capability già interrogate": distingue «mai chiesto» da «chiesto, backend muto».
# Senza, un backend che non dichiara nulla farebbe rifare la queryList a ogni riavvio.
#
# ⚠️ È VERSIONATO, e la lezione costa cara: il marcatore v1 è in produzione dalla v1.10.0, e
# quando la v1.13.0 ha aggiunto le chiavi LO/HI e le durate, ogni installazione esistente
# aveva già `caps_probed: True` → `async_ensure_vehicle_identity` usciva subito e le chiavi
# nuove non sarebbero MAI state lette: funzionalità nata morta su tutti tranne i nuovi
# installati. Chi aggiunge una capability qui **deve** aggiungere un marcatore nuovo, così
# gli entry esistenti rileggono `queryList` una volta sola e poi si fermano di nuovo.
DATA_CAPS_PROBED = "caps_probed"          # v1.10.0: powerType + range clima
DATA_CAPS_PROBED_V2 = "caps_probed_v2"    # v1.13.0: estremi LO/HI + durate ammesse

# Range clima di ripiego (OMODA): usati quando il backend non lo dichiara. Erano cablati
# in climate.py; stanno qui perché ora li legge anche il coordinator.
CLIMA_MIN_DEFAULT = 16.0
CLIMA_MAX_DEFAULT = 30.0
CLIMA_STEP_DEFAULT = 1.0

# Limiti di sicurezza del range clima dichiarato dal backend. Un valore fuori da qui è un
# dato sbagliato, non una vettura esotica: si scarta e si tengono i default (16-30 °C, 1°).
_CLIMA_MIN_PLAUSIBILE = 14.0
_CLIMA_MAX_PLAUSIBILE = 33.0
_CLIMA_STEP_AMMESSI = (0.5, 1.0)
# Gli estremi LO/HI stanno FUORI dal range normale (qui 15.0 e 31.0 contro 16-30), quindi la
# banda di plausibilità dev'essere più larga di quella del range, non la stessa.
_ESTREMO_MIN_PLAUSIBILE = 10.0
_ESTREMO_MAX_PLAUSIBILE = 36.0
# Una durata clima oltre l'ora non è una vettura esotica, è un dato sbagliato.
_DURATA_MAX_PLAUSIBILE = 60


def _vero(v) -> bool:
    """Un flag del backend può arrivare come 1, "1", True o "true"."""
    return str(v).strip().lower() in ("1", "true", "yes")


def capabilities_from_item(item: dict) -> dict:
    """Capability per-veicolo da un elemento di `queryList`, già validate.

    Ritorna solo le chiavi che il backend ha dichiarato in modo *plausibile*: un campo
    assente, non numerico o fuori scala semplicemente non compare nel dizionario, così
    chi legge ricade sui default. Non solleva mai."""
    out: dict = {}
    if not isinstance(item, dict):
        return out
    try:
        pt = item.get("powerType")
        if pt is not None and str(pt).strip() != "":
            out[DATA_POWER_TYPE] = int(float(pt))
    except (TypeError, ValueError):
        pass
    try:
        lo = float(item["minTemperature"])
        hi = float(item["maxTemperature"])
        if _CLIMA_MIN_PLAUSIBILE <= lo < hi <= _CLIMA_MAX_PLAUSIBILE:
            out[DATA_CLIMATE_MIN] = lo
            out[DATA_CLIMATE_MAX] = hi
    except (TypeError, ValueError, KeyError):
        pass
    try:
        step = float(item["temperatureStepLength"])
        if step in _CLIMA_STEP_AMMESSI:
            out[DATA_CLIMATE_STEP] = step
    except (TypeError, ValueError, KeyError):
        pass
    # ── estremi LO/HI ────────────────────────────────────────────────────────────────────
    # Solo se la vettura dichiara di averli: `isHaveLoAndHi` a 0 significa che gli estremi
    # sono già min/max, e in quel caso una chiave in più direbbe solo la stessa cosa.
    try:
        if _vero(item.get("isHaveLoAndHi")):
            lo = float(item["loValue"])
            hi = float(item["hiValue"])
            # Coerenza col range, quando il range c'è: LO sta sotto il minimo e HI sopra il
            # massimo, per definizione. Se non è così i due campi sono invertiti o sbagliati
            # e si preferisce non averli.
            coerente = (
                DATA_CLIMATE_MIN not in out
                or (lo <= out[DATA_CLIMATE_MIN] and hi >= out[DATA_CLIMATE_MAX])
            )
            if _ESTREMO_MIN_PLAUSIBILE <= lo < hi <= _ESTREMO_MAX_PLAUSIBILE and coerente:
                out[DATA_CLIMATE_LO] = lo
                out[DATA_CLIMATE_HI] = hi
    except (TypeError, ValueError, KeyError):
        pass
    # ── durate ammesse per il clima ──────────────────────────────────────────────────────
    try:
        durate = sorted({
            int(float(p)) for p in str(item["maxAirDuration"]).split(",") if str(p).strip()
        })
        durate = [d for d in durate if 0 < d <= _DURATA_MAX_PLAUSIBILE]
        if durate:
            out[DATA_AIR_DURATIONS] = durate
    # ArithmeticError: `int(float("inf"))` solleva OverflowError, che NON è un ValueError.
    # Senza, un `maxAirDuration` assurdo faceva perdere l'intera identità del veicolo (il
    # chiamante ha un except cieco) e il marcatore non veniva scritto → riletture a ogni avvio.
    except (TypeError, ValueError, KeyError, ArithmeticError):
        pass
    return out

# Parametri di REGIONE (default = Europa). Esposti come options per supportare altre regioni.
CONF_BFF = "bff"
CONF_TSP_HOST = "tsp_host"
CONF_CAR_MQTT_HOST = "car_mqtt_host"
CONF_CAR_MQTT_PORT = "car_mqtt_port"
CONF_CHANNEL_ID = "channel_id"

# Provisioning certificati mutual-TLS MQTT (FASE 3c). Cartella (dentro il filesystem di HA)
# da cui importare i 4 cert nella certs_dir per-entry. Vuoto = i cert si mettono a mano.
CONF_CERTS_SRC = "certs_src"

# I 4 file mutual-TLS attesi nella certs_dir per-entry (= quelli del bridge certs_eu/).
CERT_FILES = ("ca.pem", "client.pem", "client.key", "eu_prd_cheryinternational.cer")

DEFAULTS = {
    CONF_BFF: "https://legend-oj.omodaauto.nl/api",
    CONF_TSP_HOST: "https://tspconsole-eu.cheryinternational.com",
    CONF_CAR_MQTT_HOST: "tspemqx-app-eu.cheryinternational.com",
    CONF_CAR_MQTT_PORT: 8083,
    CONF_CHANNEL_ID: "1",
}

# Costante app condivisa (non un segreto utente): seed per derivare la password MQTT
CAR_SEED = "fa89db3abe8045919d70c6ed3cc65bc5"

# Intervalli (secondi)
DEFAULT_SESSION_EVERY = 900
DEFAULT_AWAKE_WINDOW = 300

# Poll telemetria periodico (sveglia + lettura realtime). DUE intervalli in MINUTI,
# personalizzabili dalle opzioni dell'integrazione; 0 = disattivato:
#   - CONF_POLL_NORMAL  : a riposo/parcheggiata (default 60 min)
#   - CONF_POLL_CHARGING: quando è attaccata alla colonnina (default 30 min). Da v1.5.14 NON è
#     più il meccanismo che segue la ricarica (lo fa il loop a 2 min di CHARGING_POLL_EVERY, in
#     sola lettura): qui resta solo come BACKSTOP che avvia quel loop se l'auto non annuncia da
#     sola l'attacco del cavo, + refresh GPS periodico. Mentre carica l'auto è alimentata.
# Lo stato "attaccata" si rileva da `chargeGunState` (spina collegata).
# ⚠️ ogni ciclo SVEGLIA l'auto (vehicleLocation) per posizione + telemetria fresche anche
# a vettura parcheggiata → micro-consumo 12V e possibile contesa con l'app ufficiale.
CONF_POLL_NORMAL = "poll_normal_min"
CONF_POLL_CHARGING = "poll_charging_min"
DEFAULT_POLL_NORMAL_MIN = 60
DEFAULT_POLL_CHARGING_MIN = 30
# attesa tra la sveglia (localizza) e la lettura realtime forzata, perché l'auto torni online
POLL_WAKE_WAIT = 25
# Alta tensione (HV) e telemetria FRESCA. Scoperta verificata dal vivo 2026-06-22: il canale
# /asr/manager/realtime riporta odometro/SOC/tensione/corrente VERI solo quando l'alta tensione
# è accesa (hVoltageState=1: marcia, ricarica o clima acceso); ad HV spento ritorna uno snapshot
# stantio (odometro vecchio, dumpEnergy=0, totalVoltage=0, totalCurrent=-1000). Non esiste un
# comando "leggero" che forzi un report fresco (confermato dal reverse-engineering della SDK
# nativa Chery): l'unico modo è leggere mentre l'HV è GIÀ acceso. Perciò, appena vediamo l'HV
# acceso, rileggiamo il realtime a raffica per catturare i valori che salgono (odometro/batteria),
# poi smettiamo da soli quando si rispegne. Zero comandi all'auto.
HV_ON_POLL_EVERY = 60   # secondi tra due letture realtime mentre l'alta tensione è accesa
HV_ON_POLL_MAX = 90     # cap di sicurezza al numero di letture ravvicinate (~90 min di marcia)
# RICARICA: quando la spina è collegata l'auto carica per ORE (es. 246 min visti dal vivo 2026-06-23)
# e l'HV è acceso → il realtime ha batteria/corrente/tensione/tempo-residuo VERI. Lo stesso loop
# ravvicinato segue allora l'avanzamento della carica, ma con intervallo più rilassato e cap molto
# più alto della marcia (una carica AC piena può durare diverse ore). Verificato 2026-06-23: ad auto
# in ricarica una lettura realtime dà subito stato_ricarica/corrente_hv/tempo_residuo aggiornati.
CHARGING_POLL_EVERY = 120   # secondi tra due letture realtime mentre la spina è collegata (carica)
CHARGING_POLL_MAX = 300     # cap di sicurezza (~10h: copre una carica AC completa con margine)
# Intervallo massimo (secondi) fra due campioni di ricarica ancora integrati nei contatori
# di energia casa/fuori. Durante una carica il poll realtime gira ogni CHARGING_POLL_EVERY
# (120 s); un buco piu' largo significa che l'auto si e' addormentata o ha smesso di
# riportare, quindi NON si integra attraverso di esso — altrimenti si inventerebbe energia.
# 300 s = si tollera un poll perso, si rifiutano i buchi di sonno.
#
# ATTENZIONE, difetto noto e portato di proposito senza correggerlo: su cariche AC lente con
# polling rado quasi tutta la sessione cade nei buchi e il contatore SOTTOSTIMA. Caso reale
# misurato sulla linea fork: 0,53 kWh contati contro ~8,2 kWh ricavati dal SoC. Correggerlo
# e' un cambiamento a se', per non confondere il porting con il fix.
CHARGE_ENERGY_MAX_GAP = 300
# MARCIA (battito di rilevamento): l'auto IN MOVIMENTO non manda push MQTT (verificato dal vivo
# 2026-06-24: a vettura in marcia la sessione MQTT è connessa ma non arriva alcun 5A02 → motore/
# velocità restavano fermi al giorno prima) e il poll periodico "sveglia+leggi" è ogni ~ora. Senza
# un battito dedicato il refresh automatico durante un viaggio non partiva MAI. Questo timer fa SOLO
# una lettura realtime (NESSUN comando, NESSUNA sveglia, zero 12V): appena trova l'HV acceso, la
# stessa lettura arma il follow-up a HV_ON_POLL_EVERY (60s) che poi segue tutto il viaggio. Se il
# follow-up è già attivo (marcia/ricarica) il battito non fa nulla. A vettura ferma è una sola GET
# al cloud ogni intervallo (il realtime torna lo snapshot stantio, scartato): nessun consumo auto.
DRIVE_WATCH_EVERY = 180     # secondi tra due controlli "sei in marcia?" (sola lettura, no comandi)
# attesa nelle macro comfort tra la sveglia (localizza) e l'invio di coolingControl/heatingControl:
# i moduli clima+sedili rispondono solo a vettura DESTA e serve tempo perché la TBOX alimenti il
# bus comfort. Verificato dal vivo 2026-06-21: con ~35s il comando macro va a buon fine; con
# 14s falliva (timeout TBOX↔centraline). Sotto questo valore le macro tornano a dare errore.
MACRO_WAKE_WAIT = 35
# ...ma quei 35s servono solo se l'auto DORME. Se sta già pubblicando su MQTT il bus comfort è
# alimentato: la sveglia è inutile e l'attesa è dannosa. Misurato sul campo 2026-07-21…31: fra
# pressione del tasto e conferma passavano 45-50s, in cui l'interruttore risultava già acceso e
# non succedeva nulla di visibile → l'utente ripremeva, il secondo comando si accavallava al primo
# e l'auto rifiutava con A00082 (6 casi su 22 cicli). Ad auto desta si salta la sveglia e si
# attende solo questo margine breve, il tempo che l'eventuale comando precedente si esaurisca.
MACRO_WAKE_WAIT_AWAKE = 5
# durata del preset comfort (coolingControl/heatingControl usano duration/times = 15 min):
# l'auto lo spegne da sola dopo questo tempo → lo switch macro torna OFF da solo per non
# restare "acceso" a vuoto. +60s di margine.
MACRO_PRESET_S = 15 * 60 + 60
# ⚠️ LIMITE NOTO (v1.13.0, non risolto di proposito). Questi 15 minuti sono ancora una
# costante, mentre la durata spedita alle macro ora la decide la vettura (`maxAirDuration`).
# Su una vettura che ammetta solo 5′, l'auto chiude il preset dopo 5 minuti e l'interruttore
# resta acceso altri 11: sfasatura cosmetica, nessun comando sbagliato. Sull'Omoda 9 non si
# manifesta (durata dichiarata 15 = costante). Sistemarlo vuol dire derivare il timer dalla
# durata effettivamente spedita, che oggi `switch.py` non conosce — va fatto, ma non di corsa
# in una release che tocca già il corpo dei comandi comfort.
# Quanto si aspetta, dopo aver spedito una macro, prima di credere alla TELEMETRIA SPONTANEA
# che dice «preset spento». Serve perché fra il nostro invio e l'esecuzione l'auto continua a
# pubblicare lo stato di PRIMA: un 5A02 già in volo arriva con il clima ancora a zero, e senza
# questa finestra spegnerebbe l'interruttore un secondo dopo che l'utente l'ha acceso.
# ⚠️ Si applica a TUTTI i messaggi, conferme comprese, e questo ha un costo dichiarato: gli
# ack dell'auto arrivano in pochi secondi (mediana 8 s sul diario di agosto) e sono i messaggi
# che portano i campi del preset in modo più sistematico, quindi finiscono quasi tutti dentro
# la finestra e non vengono usati. Esentarli sembra ovvio ed è sbagliato finché non si sa
# correlare l'ack col PROPRIO comando (vedi `switch._spento_dall_auto`): un ack può essere la
# risposta a un comando PRECEDENTE, e in quel caso spegnerebbe un preset appena acceso.
# ⚠️ Il valore è PRUDENZIALE, non misurato: quanto possa essere «vecchio» un frame spontaneo
# che ci raggiunge dopo l'invio non è mai stato misurato, e non lo si deduce dalla latenza
# degli ack, che misura invio→conferma ed è un'altra grandezza. Sbagliare in eccesso costa un
# ritardo nella correzione; in difetto costa un comando annullato sotto gli occhi dell'utente.
# ⚠️ La sveglia NON è più coperta da questa finestra ma da una guardia esplicita: finché il
# comando non è partito la macro ignora tutto (vedi `_invio_in_corso` in `switch.py`).
# ⚠️ Vale solo DENTRO la stessa esecuzione di Home Assistant. Dopo un riavvio non c'è alcun
# invio da proteggere e la correzione si applica al primo messaggio utile: è proprio il caso
# che il riarmo della scadenza da solo non copre (l'auto può aver chiuso il preset mentre HA
# era spento, e allora l'interruttore deve nascere già spento).
MACRO_GRAZIA_S = 120

# Campo di STATO che l'auto pubblica per il climatizzatore. È il cuore di entrambe le macro
# comfort e l'unico segnale che dice se una preclimatizzazione è in corso: compare nelle
# conferme di `coolingControl`/`heatingControl` e nella telemetria 5A02, ed è lo stesso che
# alimenta la card clima. Sta qui perché lo leggono due piattaforme diverse (`switch` e
# `climate`) e nessuna delle due deve importare l'altra.
CAMPO_CLIMA = "frontHVACState"

# Durata massima dello stato ottimistico di un attuatore quando la verità non arriva mai
# (vedi `entity.Omoda9OptimisticMixin`). Serve solo come rete: nel caso normale l'ottimismo
# si chiude appena l'auto pubblica IL CAMPO di quell'entità, che ad auto desta è questione
# di secondi.
# Perché un quarto d'ora e non un valore qualsiasi: è l'orizzonte oltre il quale qualunque
# azione comfort dell'utente è comunque finita per conto suo (l'auto chiude i preset dopo
# ~15 minuti, MACRO_PRESET_S), quindi continuare a mostrare «acceso» dopo quel tempo è una
# bugia in ogni caso. Scaduto il tetto l'entità torna sul suo ripiego: per gli attuatori con
# telemetria è l'ultimo valore che l'auto ha davvero detto (vecchio, ma misurato); per quelli
# che telemetria non ne hanno — «Ricarica» — è lo stato ripristinato all'avvio di Home
# Assistant, che l'auto non ha mai confermato. In entrambi i casi è ciò che l'entità faceva
# PRIMA di questa modifica, solo molto più tardi. Il caso che il tetto evita è l'opposto:
# un'entità che resta per sempre su un valore che nessuno ha mai confermato, in silenzio.
# ⚠️ Non è una sveglia: la scadenza si valuta solo quando il coordinator notifica le entità, e
# questo coordinator non ha aggiornamenti a orologio (`update_interval=None`). Se non arriva
# NULLA — auto dormiente, MQTT muto, aggiornamento automatico spento — il tetto scatta al
# primo aggiornamento utile (in pratica il controllo di sessione), non al minuto esatto.
# Sufficiente allo scopo, che è impedire una bugia perpetua, non garantire un istante.
OPT_MAX_S = 15 * 60

# Per quanto tempo gli avvisi di un comando (durata corretta, campi saltati, rifiuto già
# annunciato) restano attaccati all'esito che l'utente legge su «Esito comando».
#
# Servono perché ogni passaggio del comando si pubblica sullo STESSO stato di Home Assistant:
# l'avviso veniva coperto dal messaggio successivo in millisecondi (misurato il 2026-08-10:
# «durata 25′ non ammessa → uso 15′» visibile 12 ms). Riattaccarli all'esito non basta però a
# farli durare, perché l'esito viene a sua volta sostituito dalla CONFERMA dell'auto qualche
# secondo dopo: gli avvisi vanno riattaccati anche a quella, ed è questa finestra a dire per
# quanto tempo una conferma può ancora essere considerata la risposta al nostro comando.
# Il valore è lo stesso di MACRO_GRAZIA_S e per la stessa ragione: la latenza misurata delle
# conferme MQTT va da 8 a 38 secondi, quindi due minuti coprono con ampio margine. Oltre, la
# conferma può benissimo essere di un comando dell'app ufficiale (che condivide il nostro
# canale di push) e appiccicarle i nostri avvisi direbbe una cosa falsa su un'azione altrui.
NOTE_COMANDO_S = 120

# Coda comandi: l'auto esegue UN comando alla volta (A00082 = "veicolo occupato"), quindi i
# comandi si serializzano. Un secondo comando (o un doppio-tap) ASPETTA il suo turno invece di
# essere rifiutato. Dopo un invio si lascia respirare l'auto fino alla sua conferma MQTT o al
# più COMMAND_SETTLE_S, così il prossimo della coda non parte mentre è ancora occupata.
# COMMAND_QUEUE_WAIT limita l'attesa in coda: oltre, il comando fallisce con un messaggio chiaro.
#
# ⚠️ Il valore va tenuto SOPRA il tempo di conferma reale, altrimenti la pausa scade prima che
# l'auto abbia risposto e il comando successivo parte comunque a vettura occupata. Misurato sui
# push di conferma di luglio 2026: 11-14s quando la macro comfort riesce, 8-10s quando riesce a
# metà — 5s (il vecchio valore) scadeva SEMPRE prima. Serve anche il taglio dall'altro lato:
# `_settle_after_command` ora aspetta la conferma VERA e non un messaggio qualsiasi (vedi lì).
COMMAND_SETTLE_S = 15
COMMAND_QUEUE_WAIT = 30

# Monitor diagnostico per lo SVILUPPATORE (vedi diag.py). Non è una funzione utente: non
# ha interruttore nell'interfaccia. Si attiva creando il file bandierina qui sotto nella
# config dir di HA (contenuto = giorni di durata) e si spegne da solo alla scadenza.
# Senza il file il codice è dormiente: `_diag`/`DIAG_HOOK` restano None → costo nullo.
DIAG_SWITCH_FILE = "omoda9_diag.on"
