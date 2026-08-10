"""Sensor: serratura (lock), livelli sedili (level) + batteria/velocità/sessione
+ sensori diagnostici del ponte (esiti comando/sveglia/sonda, timestamp).

Gli entity_id riproducono 1:1 quelli del bridge (omoda9_*) per continuità storico.
Tutti i sensori sono RestoreSensor: al riavvio di HA ripristinano l'ultimo valore
noto come fallback (parità col bridge, che persisteva via MQTT retained) finché non
arriva un dato live dall'auto.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    RestoreSensor,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, FIELDS_AS_RICH_ENTITY
from .coordinator import SENSORS
from .entity import Omoda9Entity


# ───────────────────────── sensori "realtime" (Round B) ─────────────────────────
# Campi del canale REST /asr/manager/realtime (in coordinator.data["realtime"]),
# aggiornati al RISVEGLIO dell'auto (probe read-only). A differenza del 5A02 (MQTT),
# qui i VALORI reali di autonomia/odometro/gomme/consumi/ricarica ci sono davvero
# (sul 5A02 erano solo flag di unità "1"). Validati 1:1 contro il bean ufficiale
# CVRealtimeResBean dell'SDK Chery. Una tabella di spec evita 20+ classi gemelle.
#
# Valori/unità CONFERMATI dal vivo ad auto sveglia (2026-06-21, 84 campi):
#   pureElectricRange=60 km · mileageSurplus=215 km (benzina) · cruiseRange=134 (=215 km in miglia)
#   lFrontTyreKpa=292 (=42 psi) → kPa · gomme temp 34-35 °C · *TyreCall/socLowCall=0=ok
#   oilSurplus=23 → LITRI (215−60=155 km a benzina /23 L ≈ 15 L/100km) · averageFuel=0.0
#   avgHkPowerKwh50km=20.6 → kWh/100km · totalVoltage=323.1 V · totalCurrent=0.0 A (HV reali!)
#   remainChargeTime ASSENTE ad auto non in carica (comparirà sotto carica).

C = UnitOfTemperature.CELSIUS
KM = UnitOfLength.KILOMETERS
MIGLIA = UnitOfLength.MILES   # unità NATIVA di cruiseRange (vedi _RT_SENSORS)
KPA = UnitOfPressure.KPA
BAR = UnitOfPressure.BAR
MIN = UnitOfTime.MINUTES
VOLT = UnitOfElectricPotential.VOLT
AMP = UnitOfElectricCurrent.AMPERE
DIST = SensorDeviceClass.DISTANCE
TEMP = SensorDeviceClass.TEMPERATURE
PRESS = SensorDeviceClass.PRESSURE
DUR = SensorDeviceClass.DURATION
VOLTAGE = SensorDeviceClass.VOLTAGE
CURRENT = SensorDeviceClass.CURRENT
KW = UnitOfPower.KILO_WATT
POWER = SensorDeviceClass.POWER
MEAS = SensorStateClass.MEASUREMENT
TOTAL = SensorStateClass.TOTAL_INCREASING


@dataclass(frozen=True)
class _RtSpec:
    """Spec di un sensore realtime. `numeric=False` → valore grezzo (stato/enum)."""

    suffix: str           # unique_id suffix (stabile): f"{vin}_rt_<suffix>"
    name: str             # nome → "Omoda9 <name>" → entity_id slugificato
    # chiave nel dict realtime. Una TUPLA elenca nomi alternativi per la stessa grandezza,
    # e vince il primo presente nel frame: modelli diversi la chiamano in modo diverso
    # (una BEV manda `dynamicPureElectricRange` dove la PHEV manda `pureElectricRange`).
    # Su Omoda 9 il primo nome è quello che arriva già oggi → nessun cambiamento.
    field: str | tuple[str, ...]
    device_class: SensorDeviceClass | None = None
    unit: str | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None
    diag: bool = False
    numeric: bool = True
    vmap: dict | None = None  # codice grezzo → testo leggibile (campi enum)
    invalid: tuple = ()       # valori (float) = segnaposto "nessuna lettura" (HV spenta) → tieni l'ultimo noto
    compute: Callable | None = None  # valore CALCOLATO da più campi realtime (ignora `field`)
    scale: float | None = None  # fattore moltiplicativo sul valore grezzo (es. kPa→bar = 0.01)
    precision: int | None = None  # cifre decimali suggerite per la UI
    # VOLATILE: campo che ha senso SOLO in una condizione precisa (es. remainChargeTime
    # esiste solo mentre l'auto carica). Assente = la condizione è finita → il valore va
    # a "sconosciuto", NON si tiene l'ultimo noto. Senza questo flag «Tempo di ricarica
    # residuo» restava a 120 min per ore ad auto scollegata (fuorviante).
    volatile: bool = False


# ── Mappe codice→testo per i campi enum di ricarica ──
# I valori sono enum a 3 stati ("0"/"1"/"2", confermati dai confronti nel codice
# dell'app `rus_car_state_model.dart`). `0` = stato a riposo verificato dal vivo
# (auto parcheggiata non in carica). La semantica di 1/2 segue la convenzione EV;
# qualunque codice non previsto resta leggibile come "Sconosciuto (N)" (vedi
# Omoda9RealtimeSensor._live_value) → nessuna informazione persa, nessun valore inventato.
CHARGE_STATE_MAP = {"0": "Non in ricarica", "1": "In ricarica", "2": "Ricarica completata"}
APPT_CHARGE_STATE_MAP = {"0": "Disattivata", "1": "Attiva", "2": "In esecuzione"}
FAST_GUN_MAP = {"0": "Scollegata", "1": "Collegata", "2": "Collegata (ricarica rapida)"}


# Nomi alternativi dell'autonomia elettrica: la PHEV manda `pureElectricRange`, una BEV
# (Omoda E5) manda `dynamicPureElectricRange`. Un unico elenco, usato sia dalle spec sia
# dai calcoli qui sotto, così non si sfilano fra loro.
ELEC_RANGE_FIELDS = ("pureElectricRange", "dynamicPureElectricRange")


def _primo(rt: dict, *nomi: str):
    """Primo dei `nomi` presente nel frame, convertito a float. None se nessuno c'è."""
    for n in nomi:
        if n in rt:
            try:
                return float(rt[n])
            except (TypeError, ValueError):
                return None
    return None


def _frame_batteria_degradato(rt: dict) -> bool:
    """True se il frame realtime porta `pureElectricRange = 0`: NON è una lettura, è un
    segnaposto → in quel frame anche la percentuale batteria è da buttare.

    Trovato in campo il 2026-07-31. Alle 01:31 la ricarica si chiude a 100% (150 km); due
    minuti dopo, spenta l'alta tensione, il cloud serve un frame con `dumpEnergy` 97 e
    `pureElectricRange` 0 — e ci resta inchiodato **7 ore**, finché l'auto non si risveglia
    e torna a dire 100%. Non è un valore vecchio "quasi giusto": nello storico dei 10 giorni
    precedenti tutti e 5 i frame con 0 km sono degradati, e la percentuale che portavano era
    sbagliata in 3 casi su 5 (97% contro 82% reale il 26/07, 97% contro 47% il 29/07,
    34% contro 100% il 25/07). Il valore del segnaposto cambia nel tempo (34, poi 97),
    quindi non si può riconoscere dalla percentuale: l'unico indizio affidabile è lo 0 km.

    Perché lo 0 km si può usare come sentinella senza rischi: l'autonomia elettrica scala
    con la carica a ~1,5 km per punto (100% = 150 km, 45% = 69 km, 16% = 12 km), quindi uno
    zero VERO vorrebbe dire scendere sotto l'~8%. Questa vettura non è mai andata sotto il
    16% (minimo assoluto in 5 settimane di storico) perché tiene una riserva per l'ibrido.

    ⚠️ Quel ragionamento vale per QUESTA vettura (riserva per l'ibrido). Su una BEV uno zero
    potrebbe in teoria essere vero; l'effetto peggiore però è tenere l'ultimo valore noto per
    un frame, quindi la sentinella resta accettabile anche lì.
    """
    v = _primo(rt, *ELEC_RANGE_FIELDS)
    return v == 0.0


def _range_totale(rt: dict):
    """Autonomia totale REALE = elettrica (`pureElectricRange`) + benzina (`mileageSurplus`).
    None se manca un pezzo → resta l'ultimo valore noto (RestoreSensor).

    ⚠️ NON usare `cruiseRange` come totale: il dump head unit lo dava per il combinato del
    cruscotto (ID_DISPLAY_MILEAGE), ma è falso. Sembrava "statico" perché non seguiva
    l'autonomia elettrica; il 2026-07-22 si è capito il perché — è l'autonomia BENZINA in
    miglia (182 km/1,609 = 113 e 215 km/1,609 = 134, due campioni a un mese di distanza).
    Quindi non contiene affatto la parte elettrica. La somma elettrica+benzina segue lo
    stato batteria → è la scelta corretta."""
    # 0 km = segnaposto, non una lettura: sommarlo farebbe crollare il totale di ~150 km
    # (visto il 30/07: 251 → 125 km per tutta la notte). Vedi _frame_batteria_degradato.
    if _frame_batteria_degradato(rt):
        return None
    elec = _primo(rt, *ELEC_RANGE_FIELDS)
    fuel = _primo(rt, "mileageSurplus")
    if elec is None or fuel is None:
        return None
    return elec + fuel


def _range_totale_bev(rt: dict):
    """Autonomia totale su BEV CONFERMATO = solo la parte elettrica (non c'è serbatoio).

    Sostituisce `_range_totale` unicamente quando il backend dichiara `powerType == 0`.
    ⚠️ Non si ottiene lo stesso effetto trattando la benzina mancante come 0: su una PHEV
    un `mileageSurplus` assente per un frame farebbe crollare il totale di ~150 km — è
    esattamente il difetto corretto in v1.7.1. Qui la differenza la fa la capability
    dichiarata, non l'assenza del campo."""
    if _frame_batteria_degradato(rt):
        return None
    return _primo(rt, *ELEC_RANGE_FIELDS)


_RT_SENSORS: list[_RtSpec] = [
    # ── P1 · autonomia / chilometri (valori km confermati dal vivo) ──
    # 0 km = segnaposto "alta tensione spenta", NON autonomia esaurita → tieni l'ultimo noto
    # invece di mostrare 0 km per ore ad auto carica (vedi _frame_batteria_degradato).
    _RtSpec("range_elettrico", "Autonomia elettrica", ELEC_RANGE_FIELDS,
            DIST, KM, MEAS, "mdi:map-marker-distance", invalid=(0.0,)),
    # mileageSurplus = autonomia a BENZINA (motore termico), NON il totale: verificato dal
    # vivo 2026-06-23 che resta 215 km mentre l'autonomia elettrica scende (60→27 km) e il
    # carburante è invariato (oilSurplus 23 L) → segue il serbatoio, non la batteria.
    _RtSpec("range_benzina", "Autonomia benzina", "mileageSurplus",
            DIST, KM, MEAS, "mdi:gas-station"),
    # Autonomia TOTALE = elettrica + benzina (campo CALCOLATO). Vedi _range_totale.
    # (cruiseRange NON usato come totale: è l'autonomia benzina in miglia — vedi sotto.)
    _RtSpec("range_totale", "Autonomia totale", "",
            DIST, KM, MEAS, "mdi:map-marker-distance", compute=_range_totale),
    # cruiseRange = `mileageSurplus` (autonomia benzina) espresso in MIGLIA. RISOLTO il
    # 2026-07-22 confrontando due campioni a un mese di distanza:
    #     182 km / 1,609344 = 113,09  →  cruiseRange 113   (22/07)
    #     215 km / 1,609344 = 133,59  →  cruiseRange 134   (21/06)
    # Ecco perché sembrava "statico": non lo era, si muoveva in lockstep con l'autonomia
    # benzina. Non è quindi una stima combinata e NON va usato per l'autonomia totale — è
    # lo stesso dato in un'altra unità (di qui il campo `rangeUnit` che l'auto invia).
    # Tenuto come diagnostico: conferma dal vivo l'unità di misura scelta dal cloud.
    # Dichiarare l'unità VERA (miglia) non è un dettaglio: con `device_class`
    # distanza è Home Assistant a convertire per l'utente, quindi il sensore
    # mostrerà ~182 km invece di un "113 km" che sarebbe semplicemente falso.
    # precision=0: la conversione miglia→km produce 181,855872, sei decimali di
    # falsa precisione su un dato che l'auto manda arrotondato all'unità.
    _RtSpec("range_combinato", "Autonomia benzina (miglia)", "cruiseRange",
            DIST, MIGLIA, MEAS, "mdi:map-marker-distance", diag=True, precision=0),
    _RtSpec("odometro", "Odometro", "odometer",
            DIST, KM, TOTAL, "mdi:counter"),
    _RtSpec("km_ibrido", "Chilometraggio ibrido", "hybridMileage",
            DIST, KM, TOTAL, "mdi:counter", diag=True),
    # ── P1 · TPMS pressione (campo auto in kPa → mostrata in BAR come nell'app: ÷100) ──
    _RtSpec("gomma_ant_sx_press", "Pressione gomma ant. SX", "lFrontTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_ant_dx_press", "Pressione gomma ant. DX", "rFrontTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_post_sx_press", "Pressione gomma post. SX", "lRearTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    _RtSpec("gomma_post_dx_press", "Pressione gomma post. DX", "rRearTyreKpa",
            PRESS, BAR, MEAS, "mdi:car-tire-alert", scale=0.01, precision=2),
    # ── P1 · TPMS temperatura (°C, diagnostica) ──
    _RtSpec("gomma_ant_sx_temp", "Temperatura gomma ant. SX", "lFrontTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_ant_dx_temp", "Temperatura gomma ant. DX", "rFrontTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_post_sx_temp", "Temperatura gomma post. SX", "lRearTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("gomma_post_dx_temp", "Temperatura gomma post. DX", "rRearTyreTemp",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    # ── P2 · consumi e residui (unità confermate dal vivo) ──
    _RtSpec("consumo_carburante", "Consumo medio carburante", "averageFuel",
            None, "L/100 km", MEAS, "mdi:gas-station"),
    # avgHkPowerKwh50km=20.6 dal vivo → kWh/100km (il nome "50km" è fuorviante).
    # -100 = segnaposto "nessun dato" ad auto ferma (HV spenta) → tieni l'ultimo noto.
    # `avgHkPower` è il nome che usano le BEV per la stessa grandezza (es. 17.7 = 177 Wh/km).
    _RtSpec("consumo_elettrico", "Consumo medio elettrico",
            ("avgHkPowerKwh50km", "avgHkPower"),
            None, "kWh/100 km", MEAS, "mdi:lightning-bolt", invalid=(-100.0,)),
    # oilSurplus=23 dal vivo → LITRI (confermato dal calcolo autonomia benzina).
    _RtSpec("carburante_residuo", "Carburante residuo", "oilSurplus",
            None, "L", MEAS, "mdi:fuel"),
    # ── P2 · batteria alta tensione (valide SOLO ad auto in marcia/ricarica) ──
    # Da ferma l'auto manda 0 V / -1000 A = segnaposto "HV spenta", non letture reali:
    # marcati invalidi → il sensore tiene l'ultimo valore noto invece di azzerarsi.
    _RtSpec("tensione_hv", "Tensione batteria HV", "totalVoltage",
            VOLTAGE, VOLT, MEAS, "mdi:flash", diag=True, invalid=(0.0,)),
    _RtSpec("corrente_hv", "Corrente batteria HV", "totalCurrent",
            CURRENT, AMP, MEAS, "mdi:current-dc", diag=True, invalid=(-1000.0,)),
    # ── P2 · ricarica ──
    # remainChargeTime: ASSENTE ad auto non in carica (comparirà sotto carica). Assunto
    # in MINUTI — da riconfermare a vettura in carica. chargeState/appointmentChargeState/
    # fastChargingGunStatus = codici (tutti 0 = a riposo dal vivo) → grezzi da decodificare.
    _RtSpec("tempo_ricarica", "Tempo di ricarica residuo", "remainChargeTime",
            DUR, MIN, None, "mdi:timer-sand", volatile=True),
    _RtSpec("stato_ricarica", "Stato ricarica", "chargeState",
            None, None, None, "mdi:ev-station", diag=True, numeric=False,
            vmap=CHARGE_STATE_MAP),
    _RtSpec("ricarica_prog_stato", "Ricarica programmata · stato", "appointmentChargeState",
            None, None, None, "mdi:calendar-clock", diag=True, numeric=False,
            vmap=APPT_CHARGE_STATE_MAP),
    _RtSpec("presa_rapida", "Presa ricarica rapida", "fastChargingGunStatus",
            None, None, None, "mdi:ev-plug-ccs2", diag=True, numeric=False,
            vmap=FAST_GUN_MAP),
    # ── P2 · clima target ──
    _RtSpec("temp_imp_sx", "Temperatura impostata SX", "frontSetTempLeft",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    _RtSpec("temp_imp_dx", "Temperatura impostata DX", "frontSetTempRight",
            TEMP, C, MEAS, "mdi:thermometer", diag=True),
    # NB (2026-06-25): la cattura live del payload realtime (91 campi) ha SMENTITO i campi
    # del bean SDK che NON sono inviati da questa vettura (inCarTemperature, a/bOdoMeter,
    # chargingPower, averageSpeed, insFuelConsum, fastRemainChargeTime, tmpParkCountdown):
    # rimossi perché restavano `unknown` per sempre. Le novità verificate (oilCall/
    # electricityCall/engineState/hVoltageState) sono binary_sensor → vedi binary_sensor.py.
]

# ── Adattamento ai modelli SOLO ELETTRICI ────────────────────────────────────────────────
# Regola: si cambia qualcosa SOLO con `powerType == 0` dichiarato dal backend. Capability
# sconosciuta ⇒ tutto come su Omoda 9 / Jaecoo, entità comprese.

# Sensori che parlano del motore termico: su una BEV confermata non vengono proprio creati,
# invece di restare `unknown` per sempre. `range_combinato` è qui perché è `mileageSurplus`
# in miglia — cioè benzina anche lui.
_SENSORI_SOLO_TERMICO = frozenset({
    "range_benzina", "range_combinato", "consumo_carburante", "carburante_residuo",
    "km_ibrido",
})

# Campi che ESISTONO solo sulle BEV: la cattura live dei 91 campi del 2026-06-25 ha
# dimostrato che questa vettura NON li manda, quindi si creano soltanto a BEV confermata
# (altrimenti sarebbero tre entità `unknown` a vita).
_RT_SENSORI_BEV: list[_RtSpec] = [
    # potenza di ricarica istantanea: la mandano le BEV, la PHEV no
    _RtSpec("potenza_ricarica", "Potenza di ricarica", "chargingPower",
            POWER, KW, MEAS, "mdi:ev-station", volatile=True),
    # autonomia omologata WLTP (valore fisso di targa, non una lettura) → diagnostica
    _RtSpec("range_wltp", "Autonomia WLTP", "wltcPureElectricRange",
            DIST, KM, MEAS, "mdi:map-marker-distance", diag=True),
    # efficienza dichiarata dall'auto in miglia/kWh: serve a chi ha HA in unità imperiali,
    # perché HA non sa convertire kWh/100 km (energia-per-distanza).
    _RtSpec("efficienza_mi_kwh", "Efficienza elettrica (mi/kWh)", "avgHkPowerMikwh",
            None, "mi/kWh", MEAS, "mdi:lightning-bolt", diag=True),
]


def _rt(coord, field: str | tuple[str, ...]) -> str | None:
    """Valore grezzo del campo realtime, o None se assente/vuoto.

    Con una tupla di nomi alternativi vince il PRIMO presente e valorizzato: serve ai
    modelli che chiamano la stessa grandezza in modo diverso (BEV vs PHEV)."""
    rt = coord.data.get("realtime") or {}
    for nome in ((field,) if isinstance(field, str) else field):
        v = rt.get(nome)
        if v is not None and str(v).strip() not in ("", "None"):
            return str(v)
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    ents: list = [
        Omoda9FieldSensor(coord, s)
        for s in SENSORS
        if s["comp"] == "sensor" and s["key"] not in FIELDS_AS_RICH_ENTITY
    ]
    ents.append(Omoda9Battery(coord))
    ents.append(Omoda9Speed(coord))
    # Piano di partenza programmata: dato che l'auto ci manda già a ogni sonda e che finora
    # buttavamo via. Sola lettura — il comando `appointmentTravel` non è implementato.
    ents.append(Omoda9DeparturePlan(coord))
    # — sensori "ricchi" dal canale realtime (Round B): autonomia, odometro, gomme,
    #   consumi, ricarica, clima target —
    # Su BEV CONFERMATA (powerType == 0) si tolgono i sensori del motore termico e si
    # aggiungono i campi che mandano solo le elettriche. Capability sconosciuta ⇒ elenco
    # invariato: su Omoda 9 / Jaecoo esce esattamente ciò che usciva prima.
    bev = coord.is_pure_electric()
    specs = [s for s in _RT_SENSORS if not (bev and s.suffix in _SENSORI_SOLO_TERMICO)]
    if bev:
        # senza serbatoio l'autonomia totale è quella elettrica: il calcolo a due addendi
        # resterebbe a None per sempre (manca `mileageSurplus`).
        specs = [replace(s, compute=_range_totale_bev) if s.suffix == "range_totale" else s
                 for s in specs]
        specs += _RT_SENSORI_BEV
    ents += [Omoda9RealtimeSensor(coord, s) for s in specs]
    ents.append(Omoda9SessionStatus(coord))
    # — sensori diagnostici (parità col bridge) —
    ents.append(Omoda9TextSensor(coord, "Omoda9 Esito comando", "cmd_status", "cmd_status", "mdi:car-cog"))
    ents.append(Omoda9TextSensor(coord, "Omoda9 Esito sveglia", "wake_status", "wake_status", "mdi:car-connected"))
    ents.append(Omoda9TextSensor(coord, "Omoda9 Esito sonda posizione", "probe_status", "probe_status", "mdi:crosshairs-gps"))
    ents.append(Omoda9TimestampSensor(coord, "Omoda9 Ultimo contatto", "lastseen", "last_seen", "mdi:car-clock"))
    ents.append(Omoda9TimestampSensor(coord, "Omoda9 Ultima sveglia", "wake_ts", "last_wake", "mdi:car-clock"))
    ents.append(Omoda9TimestampSensor(coord, "Omoda9 Ultima posizione", "pos_fix", "last_pos_fix", "mdi:map-marker-clock"))
    # [2.0] freschezza del frame auto (resultTime del realtime): quanto è vecchio il dato
    #       batteria/odometro mostrato — utile ad auto ferma per sapere se è recente o stantio.
    ents.append(Omoda9TimestampSensor(coord, "Omoda9 Dati auto aggiornati", "car_data_ts", "car_data_ts", "mdi:database-clock"))
    add(ents)


class _Omoda9RestoreSensor(Omoda9Entity, RestoreSensor):
    """Base sensore Omoda 9 che sopravvive al riavvio di HA.

    Lo stato (telemetria 5A02, realtime, diagnostica) è in-memory nel coordinator
    → dopo un restart torna `unknown`. Qui ripristiniamo l'ultimo valore noto e lo
    usiamo come fallback finché non arriva un dato live. Le sottoclassi forniscono
    `_live_value()` (valore corrente dal coordinator, o None se assente)."""

    def __init__(self, coord, name: str, unique_suffix: str) -> None:
        super().__init__(coord, name, unique_suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._restored = None
        self._ultimo_noto = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        if last is not None:
            self._restored = last.native_value

    def _live_value(self):
        """Sottoclassi: valore corrente dal coordinator, o None se assente."""
        raise NotImplementedError

    @property
    def native_value(self):
        # ⚠️ «ultimo valore noto» = l'ultimo LETTO DAVVERO, non quello ripristinato all'avvio.
        # Prima il fallback era il solo `_restored`, che è fotografato una volta sola quando
        # HA parte e non si muove più: un segnaposto (HV spenta, 0 V, 0 km…) non riportava
        # all'ultima lettura buona ma a quella di giorni prima. Con HA riavviato di rado la
        # differenza è enorme — è la stessa classe di errore del 97% del 31/07, e senza
        # questo la protezione sul frame degradato non avrebbe niente di sensato a cui
        # ripiegare. `_restored` resta la rete di sicurezza per il primo dato dopo l'avvio.
        live = self._live_value()
        if live is not None:
            self._ultimo_noto = live
            return live
        return self._ultimo_noto if self._ultimo_noto is not None else self._restored


class Omoda9FieldSensor(_Omoda9RestoreSensor):
    """serratura (0=Bloccata/1=Sbloccata), livello sedile (Livello N) o valore grezzo."""

    def __init__(self, coord, spec: dict) -> None:
        super().__init__(coord, f"Omoda9 {spec['name']}", spec["key"])
        self._key = spec["key"]
        self._kind = spec["kind"]
        if spec.get("icon"):
            self._attr_icon = spec["icon"]
        # campi tecnici (es. codice di fase del tetto) → tra i dettagli diagnostici
        if spec.get("diag"):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _live_value(self):
        v = self.coordinator.data.get("fields", {}).get(self._key)
        if v is None:
            return None
        if self._kind == "lock":
            return "Bloccata" if str(v) in ("0", "0.0") else "Sbloccata"
        if self._kind == "level":
            return f"Livello {v}"
        return str(v)


class Omoda9Battery(_Omoda9RestoreSensor):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Batteria", "battery")

    def _live_value(self):
        rt = self.coordinator.data.get("realtime") or {}
        if "dumpEnergy" not in rt:
            return None
        # frame degradato (0 km di autonomia elettrica): la percentuale che porta non è una
        # lettura → tieni l'ultimo valore noto. Vedi _frame_batteria_degradato.
        if _frame_batteria_degradato(rt):
            return None
        try:
            soc = float(rt["dumpEnergy"])
        except (TypeError, ValueError):
            return None
        # dumpEnergy=0 = segnaposto "alta tensione spenta" (auto ferma), NON una carica
        # reale dello 0%: torna None così resta l'ultimo SOC noto (come fa l'app ufficiale).
        if soc <= 0:
            return None
        return soc

    @property
    def native_value(self):
        val = super().native_value
        # non riproporre uno "0%" stantio salvato prima del fix dei segnaposto: 0 non è un
        # ultimo-valore-noto valido per la batteria → meglio "sconosciuto" finché non arriva
        # una lettura vera (primo viaggio/ricarica o pulsante "Aggiorna stato completo").
        if val in (0, 0.0, "0", "0.0"):
            return None
        return val


class Omoda9Speed(_Omoda9RestoreSensor):
    # device_class SPEED: senza, l'unità resta inchiodata a km/h. Con, Home Assistant
    # converte secondo il sistema di unità dell'utente (mph per chi ha HA in imperiale) e
    # permette l'override per-entità. Il valore nativo resta km/h → in Italia non cambia nulla.
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:speedometer"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Velocità", "speed")

    def _live_value(self):
        rt = self.coordinator.data.get("realtime") or {}
        try:
            return float(rt["vehicleSpeed"]) if "vehicleSpeed" in rt else None
        except (TypeError, ValueError):
            return None


class Omoda9RealtimeSensor(_Omoda9RestoreSensor):
    """Sensore generico su un campo del canale realtime (vedi `_RT_SENSORS`).

    Stesso pattern di `Omoda9Battery`/`Omoda9Speed` ma parametrico: device_class,
    unità e state_class arrivano dalla spec. `numeric=True` converte a float (None
    se non parsabile → emerge l'ultimo valore noto del RestoreSensor); `numeric=False`
    tiene il valore grezzo (codici di stato ricarica da decodificare)."""

    def __init__(self, coord, spec: _RtSpec) -> None:
        super().__init__(coord, f"Omoda9 {spec.name}", f"rt_{spec.suffix}")
        self._spec = spec
        if spec.device_class:
            self._attr_device_class = spec.device_class
        if spec.unit:
            self._attr_native_unit_of_measurement = spec.unit
        if spec.state_class:
            self._attr_state_class = spec.state_class
        if spec.icon:
            self._attr_icon = spec.icon
        if spec.precision is not None:
            self._attr_suggested_display_precision = spec.precision
        if spec.diag:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        # VOLATILE: nessun fallback all'ultimo valore noto. Se il campo è assente ora, la
        # sua condizione è finita (es. carica terminata → remainChargeTime sparisce dal
        # payload) e il valore corretto è "sconosciuto", non l'ultimo letto. Per gli altri
        # sensori vale invece la regola normale del RestoreSensor (tieni l'ultimo noto).
        if self._spec.volatile:
            return self._live_value()
        return super().native_value

    def _live_value(self):
        # campo CALCOLATO da più field realtime (es. autonomia totale = elettrica + benzina)
        if self._spec.compute is not None:
            rt = self.coordinator.data.get("realtime") or {}
            val = self._spec.compute(rt)
            return None if (val is None or val in self._spec.invalid) else val
        raw = _rt(self.coordinator, self._spec.field)
        if raw is None:
            return None
        if self._spec.vmap is not None:
            key = raw[:-2] if raw.endswith(".0") else raw  # "0.0" → "0"
            return self._spec.vmap.get(key, f"Sconosciuto ({raw})")
        if not self._spec.numeric:
            return raw
        try:
            val = float(raw)
        except (TypeError, ValueError):
            return None
        # segnaposto "nessuna lettura" (es. HV spenta) → None ⇒ resta l'ultimo valore noto
        if val in self._spec.invalid:
            return None
        return val * self._spec.scale if self._spec.scale is not None else val


class Omoda9SessionStatus(_Omoda9RestoreSensor):
    _attr_icon = "mdi:key-chain"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Stato sessione", "session_detail")

    def _live_value(self):
        return self.coordinator.data.get("session_detail") or None


class Omoda9TextSensor(_Omoda9RestoreSensor):
    """Sensore testuale diagnostico (esito ultimo comando/sveglia/sonda)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, name: str, suffix: str, data_key: str, icon: str) -> None:
        super().__init__(coord, name, suffix)
        self._data_key = data_key
        self._attr_icon = icon

    def _live_value(self):
        return self.coordinator.data.get(self._data_key) or None

    @property
    def native_value(self):
        # [H9] gli esiti diagnostici (comando/sveglia/sonda) NON si ripristinano: un
        # esito vecchio dopo un restart sarebbe fuorviante (sembrerebbe l'ultima azione
        # appena eseguita). Solo il valore live; in assenza → unknown.
        return self._live_value()


class Omoda9TimestampSensor(_Omoda9RestoreSensor):
    """Timestamp diagnostico (ultimo contatto/sveglia/posizione)."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coord, name: str, suffix: str, data_key: str, icon: str) -> None:
        super().__init__(coord, name, suffix)
        self._data_key = data_key
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # [H10] device_class TIMESTAMP esige un datetime tz-aware: valida il valore
        # ripristinato (stringa ISO → parse), altrimenti None, per non emettere il
        # warning HA "Invalid datetime" e non mostrare un timestamp malformato.
        r = self._restored
        if isinstance(r, str):
            r = dt_util.parse_datetime(r)
        if not (isinstance(r, datetime) and r.tzinfo is not None):
            r = None
        self._restored = r

    def _live_value(self):
        return self.coordinator.data.get(self._data_key)


# Giorni della settimana come li numera il backend (1 = lunedì … 7 = domenica), stessa
# convenzione di `cycleData` nella ricarica programmata.
GIORNI = {1: "lun", 2: "mar", 3: "mer", 4: "gio", 5: "ven", 6: "sab", 7: "dom"}


def _orario(minuti) -> str | None:
    """`minuti dalla mezzanotte` → "HH:MM", o None se il valore non è un orario valido."""
    try:
        m = int(minuti)
    except (TypeError, ValueError):
        return None
    if not 0 <= m < 1440:
        return None
    return f"{m // 60:02d}:{m % 60:02d}"


class Omoda9DeparturePlan(_Omoda9RestoreSensor):
    """Piano di partenza programmata, letto dall'auto (`appointmentTravelSetVOS`).

    **Non costa nulla:** il campo arriva già dentro il canale realtime a ogni sonda; finora lo
    buttavamo via (0 occorrenze di `appointmentTravel` in tutto il package). Questa entità è
    di sola LETTURA: il comando `appointmentTravel` non è implementato, quindi il piano si
    imposta ancora dall'app ufficiale.

    ⚠️ **`createTime`/`updateTime`/`id` NON vengono esposti, di proposito.** Sembrano dire
    quando il piano è stato impostato e invece **il backend li rigenera a ogni interrogazione**:
    misurato il 2026-08-10 confrontando due letture a 6 settimane e mezzo di distanza — il
    contenuto (`travelTime` 350, `travelDate` [1-5], `travelAppointMainId` 63372) è rimasto
    identico mentre `id`, `createTime` e `updateTime` erano cambiati e valevano l'istante
    esatto della lettura. Mostrarli significherebbe dire all'utente «impostato oggi alle 09:31»
    di un piano che non tocca da mesi.

    ⚠️ `travelTime` è in minuti dalla mezzanotte **locale**, come `startTime` della ricarica
    programmata (misurato il 2026-08-10: un piano scritto con `startTime = 0` l'app lo mostra
    come 00:00, non 02:00). È l'unico anello dedotto per analogia fra le due funzioni, ed è
    per questo che il collaudo prevede il confronto con l'ora mostrata dall'app."""

    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Partenza programmata", "rt_partenza_programmata")

    def _piano(self) -> dict | None:
        rt = self.coordinator.data.get("realtime") or {}
        piani = rt.get("appointmentTravelSetVOS")
        if isinstance(piani, list) and piani and isinstance(piani[0], dict):
            return piani[0]
        return None

    def _live_value(self):
        piano = self._piano()
        if piano is None:
            return None
        # `switcher` 0 = piano memorizzato ma spento. Si dice "Disattivata" invece dell'orario:
        # mostrare un'ora per un piano che non scatterà è peggio che non mostrarla.
        # Stessa parola già usata da `APPT_CHARGE_STATE_MAP`, per non avere due vocabolari.
        if str(piano.get("switcher", "0")).strip() in ("", "0", "None", "False"):
            return "Disattivata"
        return _orario(piano.get("travelTime"))

    @property
    def extra_state_attributes(self) -> dict | None:
        piano = self._piano()
        if piano is None:
            return None
        giorni = piano.get("travelDate")
        giorni = giorni if isinstance(giorni, list) else []
        attrs: dict = {"attiva": str(piano.get("switcher", "0")).strip() not in ("", "0", "None", "False")}
        orario = _orario(piano.get("travelTime"))
        if orario:
            attrs["orario"] = orario
        if giorni:
            attrs["giorni"] = giorni
            attrs["giorni_testo"] = ", ".join(GIORNI.get(g, str(g)) for g in giorni)
        return attrs
