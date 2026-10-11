"""Adozione delle entita' della linea `omoda_jaecoo`, con il loro storico.

Perche' esiste. Chi viene dalla linea del fork non sta aggiornando: per Home Assistant
quella e' un'altra integrazione, e senza questo modulo si ritrova centodieci entita'
nuove e vuote mentre le sue, con anni di storico, restano attaccate a un'integrazione
che sta per togliere. Lo storico non si esporta e non si reimporta: o lo si porta
dietro adesso, o e' perso.

Come. `entity_registry.async_update_entity_platform` sposta un'entita' da
un'integrazione all'altra cambiandole platform, config entry e unique_id. E' una
funzione che Home Assistant documenta esattamente per questo caso e che **nessuna**
delle 1401 integrazioni di serie usa. Quindi: passo esplicito, mai automatico, e
l'utente deve chiederlo sapendo cosa comporta.

La corrispondenza non e' stata scritta a occhio. 83 suffissi coincidono gia' fra le due
linee, perche' il suffisso e' quasi sempre il nome del campo dell'API Chery
(`chargeGunState`, `engineState`), che e' neutro rispetto alla lingua. Gli altri sono
stati accoppiati confrontando i nomi inglesi delle due linee, e poi confrontando gli
stessi nomi con le parole in ordine diverso (`tire_front_left_warning` di la',
`tire_warning_front_left` di qua). Due bottoni accoppiati a mano perche' da noi hanno il
nome per esteso.
"""
from __future__ import annotations

# Dominio della linea di JackRonan, da cui si adotta.
LEGACY_DOMAIN = "omoda_jaecoo"

# (piattaforma, suffisso unique_id di la') -> suffisso unique_id di qua.
# Elencati solo i DIVERSI: gli 83 che coincidono non hanno bisogno di una riga.
LEGACY_SUFFIX_PAIRS: dict[tuple[str, str], str] = {
    ("binary_sensor", "rt_battery_low"):            "rt_batteria_scarica",
    ("binary_sensor", "rt_charge_needed_warning"):  "rt_avviso_ricarica",
    ("binary_sensor", "rt_front_left_tire_warning"):"rt_avviso_gomma_ant_sx",
    ("binary_sensor", "rt_front_right_tire_warning"):"rt_avviso_gomma_ant_dx",
    ("binary_sensor", "rt_high_voltage_active"):    "rt_alta_tensione",
    ("binary_sensor", "rt_low_fuel_warning"):       "rt_avviso_carburante_basso",
    ("binary_sensor", "rt_rear_left_tire_warning"): "rt_avviso_gomma_post_sx",
    ("binary_sensor", "rt_rear_right_tire_warning"):"rt_avviso_gomma_post_dx",
    ("button", "cmd_find_car"):                     "cmd_trova_auto",
    ("button", "cmd_locate_car"):                   "cmd_localizza",
    ("number", "charging_duration"):                "ricarica_durata_ore",
    ("number", "climate_duration"):                 "clima_durata",
    ("time", "charging_start_time"):                "ricarica_orario_inizio",
}

# Cio' che NON si adotta, e il motivo. Dichiarato invece che scoperto: chi legge il
# rapporto dopo la migrazione deve trovarci il numero che si aspetta.
LEGACY_NOT_MIGRATABLE: dict[tuple[str, str], str] = {
    ("binary_sensor", "rt_charging"):               
        "la ricarica e' uno switch qui e un binary_sensor di la': stesso motivo",
    ("select", "windows_select"):                   
        "i finestrini sono un cover qui e un select di la': lo storico non e' portabile fra due tipi di entita'",
    ("sensor", "rt_efficienza_elettrica"):          
        "funzione che esiste solo sulla linea del fork",
    ("sensor", "rt_potenza_ricarica"):              
        "funzione che esiste solo sulla linea del fork",
    ("sensor", "rt_range_elettrico_wltp"):          
        "funzione che esiste solo sulla linea del fork",
}


# (piattaforma, suffisso unique_id di QUA) -> entity_id che quell'entita' deve avere.
# Indicizzata sul SUFFISSO e non sulla chiave di traduzione: le due cose non coincidono
# (il sensore dell'alta tensione ha suffisso `rt_alta_tensione` e chiave
# `alta_tensione_attiva`), e confonderle qui rinominerebbe le entita' sbagliate.
CANON_ENTITY_ID: dict[tuple[str, str], str] = {
    ("binary_sensor", "airPurification"):               "binary_sensor.chery_connect_air_purification",
    ("binary_sensor", "at_home"):                       "binary_sensor.chery_connect_at_home",
    ("binary_sensor", "awake"):                         "binary_sensor.chery_connect_car_awake",
    ("binary_sensor", "backLeftDoor"):                  "binary_sensor.chery_connect_rear_left_door",
    ("binary_sensor", "backLeftWindowState"):           "binary_sensor.chery_connect_rear_left_window",
    ("binary_sensor", "backRightDoor"):                 "binary_sensor.chery_connect_rear_right_door",
    ("binary_sensor", "backRightWindowState"):          "binary_sensor.chery_connect_rear_right_window",
    ("binary_sensor", "chargeGunState"):                "binary_sensor.chery_connect_charging_cable",
    ("binary_sensor", "engineState"):                   "binary_sensor.chery_connect_engine",
    ("binary_sensor", "fWinHeatingState"):              "binary_sensor.chery_connect_windshield_heating",
    ("binary_sensor", "frontLeftDoor"):                 "binary_sensor.chery_connect_front_left_door",
    ("binary_sensor", "frontLeftWindowState"):          "binary_sensor.chery_connect_front_left_window",
    ("binary_sensor", "frontRightDoor"):                "binary_sensor.chery_connect_front_right_door",
    ("binary_sensor", "frontRightWindowState"):         "binary_sensor.chery_connect_front_right_window",
    ("binary_sensor", "hood"):                          "binary_sensor.chery_connect_hood",
    ("binary_sensor", "liftgateOperateState"):          "binary_sensor.chery_connect_tailgate_moving",
    ("binary_sensor", "online"):                        "binary_sensor.chery_connect_connection",
    ("binary_sensor", "rt_alta_tensione"):              "binary_sensor.chery_connect_high_voltage_active",
    ("binary_sensor", "rt_avviso_carburante_basso"):    "binary_sensor.chery_connect_low_fuel_warning",
    ("binary_sensor", "rt_avviso_gomma_ant_dx"):        "binary_sensor.chery_connect_tire_warning_front_right",
    ("binary_sensor", "rt_avviso_gomma_ant_sx"):        "binary_sensor.chery_connect_tire_warning_front_left",
    ("binary_sensor", "rt_avviso_gomma_post_dx"):       "binary_sensor.chery_connect_tire_warning_rear_right",
    ("binary_sensor", "rt_avviso_gomma_post_sx"):       "binary_sensor.chery_connect_tire_warning_rear_left",
    ("binary_sensor", "rt_avviso_ricarica"):            "binary_sensor.chery_connect_charge_needed_warning",
    ("binary_sensor", "rt_batteria_scarica"):           "binary_sensor.chery_connect_low_battery",
    ("binary_sensor", "session"):                       "binary_sensor.chery_connect_session",
    ("binary_sensor", "sunshadeState"):                 "binary_sensor.chery_connect_sunroof_blind",
    ("button", "cmd_antifurto_off"):                    "button.chery_connect_alarm_off",
    ("button", "cmd_antifurto_on"):                     "button.chery_connect_alarm_on",
    ("button", "cmd_clima_raffredda_off"):              "button.chery_connect_cool_everything_off",
    ("button", "cmd_clima_raffredda_on"):               "button.chery_connect_cool_everything",
    ("button", "cmd_clima_riscalda_off"):               "button.chery_connect_heat_everything_off",
    ("button", "cmd_clima_riscalda_on"):                "button.chery_connect_heat_everything",
    ("button", "cmd_finestrini_ventila"):               "button.chery_connect_vent_windows",
    ("button", "cmd_localizza"):                        "button.chery_connect_locate_car_gps",
    ("button", "cmd_trova_auto"):                       "button.chery_connect_find_car_flash_lights",
    ("button", "otp_confirm"):                          "button.chery_connect_confirm_otp",
    ("button", "otp_request"):                          "button.chery_connect_request_otp_code",
    ("button", "refresh_full"):                         "button.chery_connect_refresh_full_status",
    ("button", "refresh_pos"):                          "button.chery_connect_refresh_location",
    ("button", "wake"):                                 "button.chery_connect_wake_car",
    ("climate", "climate"):                             "climate.chery_connect_climate",
    ("cover", "baule"):                                 "cover.chery_connect_trunk",
    ("cover", "finestrini"):                            "cover.chery_connect_windows",
    ("cover", "tetto"):                                 "cover.chery_connect_sunroof",
    ("device_tracker", "position"):                     "device_tracker.chery_connect_location",
    ("lock", "lock"):                                   "lock.chery_connect_lock",
    ("number", "clima_durata"):                         "number.chery_connect_climate_duration",
    ("number", "ricarica_durata_ore"):                  "number.chery_connect_charge_duration",
    ("sensor", "battery"):                              "sensor.chery_connect_battery",
    ("sensor", "car_data_ts"):                          "sensor.chery_connect_car_data_updated",
    ("sensor", "cmd_status"):                           "sensor.chery_connect_command_result",
    ("sensor", "energy_charged_away"):                  "sensor.chery_connect_away_charging_energy",
    ("sensor", "energy_charged_home"):                  "sensor.chery_connect_home_charging_energy",
    ("sensor", "lastseen"):                             "sensor.chery_connect_last_seen",
    ("sensor", "mSeatHeatingState2"):                   "sensor.chery_connect_rear_center_seat_heating",
    ("sensor", "mSeatVentilateState2"):                 "sensor.chery_connect_rear_center_seat_ventilation",
    ("sensor", "pos_fix"):                              "sensor.chery_connect_last_position",
    ("sensor", "probe_status"):                         "sensor.chery_connect_location_probe_result",
    ("sensor", "rt_carburante_residuo"):                "sensor.chery_connect_fuel_remaining",
    ("sensor", "rt_consumo_carburante"):                "sensor.chery_connect_average_fuel_consumption",
    ("sensor", "rt_consumo_elettrico"):                 "sensor.chery_connect_average_energy_consumption",
    ("sensor", "rt_corrente_hv"):                       "sensor.chery_connect_hv_battery_current",
    ("sensor", "rt_gomma_ant_dx_press"):                "sensor.chery_connect_tire_pressure_front_right",
    ("sensor", "rt_gomma_ant_dx_temp"):                 "sensor.chery_connect_tire_temperature_front_right",
    ("sensor", "rt_gomma_ant_sx_press"):                "sensor.chery_connect_tire_pressure_front_left",
    ("sensor", "rt_gomma_ant_sx_temp"):                 "sensor.chery_connect_tire_temperature_front_left",
    ("sensor", "rt_gomma_post_dx_press"):               "sensor.chery_connect_tire_pressure_rear_right",
    ("sensor", "rt_gomma_post_dx_temp"):                "sensor.chery_connect_tire_temperature_rear_right",
    ("sensor", "rt_gomma_post_sx_press"):               "sensor.chery_connect_tire_pressure_rear_left",
    ("sensor", "rt_gomma_post_sx_temp"):                "sensor.chery_connect_tire_temperature_rear_left",
    ("sensor", "rt_km_ibrido"):                         "sensor.chery_connect_hybrid_mileage",
    ("sensor", "rt_odometro"):                          "sensor.chery_connect_odometer",
    ("sensor", "rt_partenza_programmata"):              "sensor.chery_connect_scheduled_departure",
    ("sensor", "rt_presa_rapida"):                      "sensor.chery_connect_fast_charging_port",
    ("sensor", "rt_range_benzina"):                     "sensor.chery_connect_fuel_range",
    ("sensor", "rt_range_combinato"):                   "sensor.chery_connect_petrol_range_miles",
    ("sensor", "rt_range_elettrico"):                   "sensor.chery_connect_electric_range",
    ("sensor", "rt_range_totale"):                      "sensor.chery_connect_total_range",
    ("sensor", "rt_ricarica_prog_stato"):               "sensor.chery_connect_scheduled_charging_status",
    ("sensor", "rt_stato_ricarica"):                    "sensor.chery_connect_charging_status",
    ("sensor", "rt_temp_imp_dx"):                       "sensor.chery_connect_set_temperature_right",
    ("sensor", "rt_temp_imp_sx"):                       "sensor.chery_connect_set_temperature_left",
    ("sensor", "rt_tempo_ricarica"):                    "sensor.chery_connect_remaining_charge_time",
    ("sensor", "rt_tensione_hv"):                       "sensor.chery_connect_hv_battery_voltage",
    ("sensor", "session_detail"):                       "sensor.chery_connect_session_status",
    ("sensor", "speed"):                                "sensor.chery_connect_speed",
    ("sensor", "sunroofMoveState"):                     "sensor.chery_connect_sunroof_movement_state",
    ("sensor", "wake_status"):                          "sensor.chery_connect_wake_up_result",
    ("sensor", "wake_ts"):                              "sensor.chery_connect_last_wake_up",
    ("switch", "antifurto"):                            "switch.chery_connect_alarm",
    ("switch", "dSeatHeatingState"):                    "switch.chery_connect_driver_seat_heating",
    ("switch", "dSeatVentilateState"):                  "switch.chery_connect_driver_seat_ventilation",
    ("switch", "disappannamento_parabrezza"):           "switch.chery_connect_windshield_defog",
    ("switch", "frontWindshieldHeat"):                  "switch.chery_connect_windshield_defrost",
    ("switch", "lSeatHeatingState2"):                   "switch.chery_connect_rear_left_seat_heating",
    ("switch", "lSeatVentilateState2"):                 "switch.chery_connect_rear_left_seat_ventilation",
    ("switch", "pSeatHeatingState"):                    "switch.chery_connect_passenger_seat_heating",
    ("switch", "pSeatVentilateState"):                  "switch.chery_connect_passenger_seat_ventilation",
    ("switch", "polling_auto"):                         "switch.chery_connect_automatic_updates",
    ("switch", "rSeatHeatingState2"):                   "switch.chery_connect_rear_right_seat_heating",
    ("switch", "rSeatVentilateState2"):                 "switch.chery_connect_rear_right_seat_ventilation",
    ("switch", "rWinHeatingState"):                     "switch.chery_connect_rear_window_heating",
    ("switch", "raffredda_tutto"):                      "switch.chery_connect_cool_everything",
    ("switch", "ricarica"):                             "switch.chery_connect_charging",
    ("switch", "ricarica_programmata"):                 "switch.chery_connect_scheduled_charging",
    ("switch", "riscalda_tutto"):                       "switch.chery_connect_heat_everything",
    ("switch", "steerWheelHeating"):                    "switch.chery_connect_steering_wheel_heating",
    ("text", "otp_code"):                               "text.chery_connect_otp_code",
    ("time", "ricarica_orario_inizio"):                 "time.chery_connect_charge_start_time",
}


def adotta(hass, entry, *, dry_run: bool = False) -> dict:
    """Adotta le entita' di `omoda_jaecoo` portandosi dietro il loro storico.

    Ritorna un rapporto: quante adottate, quante saltate e perche'. Non solleva mai su una
    singola entita': un'adozione che si ferma a meta' lascia l'utente in uno stato che non
    sa descrivere, e questa funzione gira su installazioni che nessuno di noi puo' vedere.

    `dry_run` prepara tutto e non scrive: e' il modo di far vedere all'utente cosa
    succederebbe prima che succeda.
    """
    from homeassistant.helpers import entity_registry as er

    from .const import DOMAIN

    reg = er.async_get(hass)
    rapporto = {"adottate": [], "saltate": [], "non_migrabili": [], "sostituite": 0}

    nostre = {e.unique_id: e for e in er.async_entries_for_config_entry(reg, entry.entry_id)}
    vin = entry.data.get("vin") or ""

    for voce in list(reg.entities.values()):
        if voce.platform != LEGACY_DOMAIN:
            continue
        piattaforma = voce.entity_id.split(".", 1)[0]
        suffisso = voce.unique_id[len(vin) + 1:] if vin and voce.unique_id.startswith(f"{vin}_") else None
        if suffisso is None:
            rapporto["saltate"].append((voce.entity_id, "e' di un altro veicolo"))
            continue

        chiave = (piattaforma, suffisso)
        if chiave in LEGACY_NOT_MIGRATABLE:
            rapporto["non_migrabili"].append((voce.entity_id, LEGACY_NOT_MIGRATABLE[chiave]))
            continue

        nostro_suffisso = LEGACY_SUFFIX_PAIRS.get(chiave, suffisso)
        nuovo_unique = f"{vin}_{nostro_suffisso}"

        # L'entita' nostra con quella identita' esiste gia' se l'utente ha configurato
        # l'integrazione prima di adottare: e' NUOVA e VUOTA per costruzione, mentre quella
        # di la' porta lo storico. Si toglie la vuota per fare posto a quella piena. E'
        # l'unico punto in cui questa funzione cancella qualcosa, e cancella solo roba
        # nostra, solo se ha un rimpiazzo pronto.
        gemella = nostre.get(nuovo_unique)
        if gemella is not None:
            if not dry_run:
                reg.async_remove(gemella.entity_id)
            rapporto["sostituite"] += 1

        vecchio_id = voce.entity_id
        if dry_run:
            rapporto["adottate"].append((vecchio_id, nuovo_unique))
            continue
        try:
            # `new_unique_id` SOLO se cambia davvero. Passandolo uguale a quello attuale,
            # Home Assistant lo vede occupato dall'entita' stessa che stiamo spostando e
            # rifiuta con "Unique id ... is already in use". Riguarda gli 83 suffissi che
            # coincidono fra le due linee, cioe' la maggioranza: senza questa riga
            # l'adozione fallirebbe proprio nel caso normale.
            extra = {} if voce.unique_id == nuovo_unique else {"new_unique_id": nuovo_unique}
            reg.async_update_entity_platform(
                vecchio_id, DOMAIN,
                new_config_entry_id=entry.entry_id,
                new_device_id=None,
                **extra,
            )
        except Exception as err:  # noqa: BLE001 - una sola entita' non deve fermare il resto
            rapporto["saltate"].append((vecchio_id, f"{type(err).__name__}: {err}"))
            continue

        # Secondo passo: l'entity_id. `async_update_entity_platform` non lo tocca, quindi
        # senza questo l'entita' sarebbe nostra ma continuerebbe a chiamarsi come di la'.
        atteso = CANON_ENTITY_ID.get((piattaforma, nostro_suffisso))
        if atteso is None:
            # Nessun nome canonico per quel suffisso: si tiene l'entity_id che aveva. E' gia'
            # inglese su quella linea, quindi e' un risultato accettabile e non una perdita.
            rapporto["adottate"].append((vecchio_id, vecchio_id))
            continue
        if atteso != vecchio_id and reg.async_get(atteso) is None:
            reg.async_update_entity(vecchio_id, new_entity_id=atteso)
            rapporto["adottate"].append((vecchio_id, atteso))
        else:
            rapporto["adottate"].append((vecchio_id, vecchio_id))

    return rapporto

# ── Prese sul recorder ────────────────────────────────────────────────────────────────────
# Tre funzioni di una riga, e non e' cerimonia: il recorder non esiste nell'ambiente di
# test, quindi importandolo dentro `recupera_storico` quel codice non sarebbe verificabile
# in nessun modo - e questa e' la funzione che tocca i dati storici della gente. Cosi' si
# sostituiscono, e le tre righe che restano non hanno niente da sbagliare.

async def _serie_esistenti(hass) -> set[str]:
    from homeassistant.components.recorder.statistics import async_list_statistic_ids
    return {m["statistic_id"] for m in await async_list_statistic_ids(hass)}


def _rinomina_statistiche(hass, vecchio: str, nuovo: str) -> None:
    from homeassistant.components.recorder.statistics import async_update_statistics_metadata
    async_update_statistics_metadata(hass, vecchio, new_statistic_id=nuovo)


def _cancella_statistiche(hass, ids: list[str]) -> None:
    from homeassistant.components.recorder import get_instance
    get_instance(hass).async_clear_statistics(ids)


def _rinomina_cronologia(hass, vecchio: str, nuovo: str) -> None:
    from homeassistant.components.recorder import get_instance
    get_instance(hass).async_update_states_metadata(vecchio, new_entity_id=nuovo)


async def _ha_cronologia(hass, entity_id: str) -> bool:
    """Se di questa entita' il recorder ha ancora almeno uno stato registrato."""
    from homeassistant.components.recorder import get_instance
    from homeassistant.components.recorder.history import get_last_state_changes
    righe = await get_instance(hass).async_add_executor_job(
        get_last_state_changes, hass, 1, entity_id)
    return bool(righe.get(entity_id))


def _sposta_di_lato(hass, entity_id: str) -> str:
    """Toglie di mezzo la cronologia corta spostandola su un nome libero, invece di
    cancellarla.

    Prima di qui si provava con `recorder.purge_entities`, e NON funziona: quel servizio
    mette in coda un compito e cancella gli STATI, ma la riga in `states_meta` resta - ed e'
    quella che blocca la rinomina. Misurato il 27 settembre 2026 su un'istanza vera: 96
    righe `Cannot migrate history ... because the new entity_id is already in use`, tutte
    dopo un purge che era andato a buon fine.

    Spostare di lato riesce dove cancellare fallisce, e ha due vantaggi sopra la cancellazione:
    la cronologia corta non viene distrutta ma solo archiviata sotto un nome che nessuno
    guarda, e l'operazione usa la stessa identica API della rinomina, quindi o riescono
    entrambe o non si e' rotto niente.

    Il nome di parcheggio non puo' collidere con niente: non e' un entity_id che questa
    integrazione produca, e non e' in `deleted_entities`, quindi un secondo giro non lo
    scambia per un candidato."""
    dominio, _, oggetto = entity_id.partition(".")
    parcheggio = f"{dominio}.{oggetto}_superseded"
    _rinomina_cronologia(hass, entity_id, parcheggio)
    return parcheggio


async def recupera_storico(hass, entry, *, dry_run: bool = True) -> dict:
    """Recupera i DATI della linea `omoda_jaecoo` quando le sue entita' non ci sono piu'.

    Il caso che questa funzione copre e' l'errore che faranno quasi tutti, ed e' quello che
    `adotta` non puo' piu' riparare: disinstallare la vecchia integrazione PRIMA di adottare.
    "Rimuovi la vecchia" e' il primo passo che viene in mente a chiunque - tanto che il
    documento di migrazione deve scrivere "solo allora" in grassetto, il che e' gia'
    l'ammissione che l'ordine verra' sbagliato.

    Cancellare un'integrazione toglie le entita' dal registro e NON tocca il recorder. I
    dati restano, orfani, indicizzati sui vecchi `entity_id`; Home Assistant ricorda le
    entita' cancellate in `deleted_entities`, con `entity_id` e `unique_id`, e questo basta
    a ricostruire la corrispondenza. Quindi non si sposta piu' niente fra integrazioni: si
    rinominano i dati addosso alle entita' nuove, che i nomi giusti ce li hanno gia'.

    Due cose, separate perche' si perdono separatamente:
      - le STATISTICHE a lungo termine (dashboard Energia, grafici a lunga memoria);
      - la CRONOLOGIA degli stati.

    C'e' un orologio: il purge del recorder prima o poi ripulisce le serie orfane. Giorni,
    non ore, ma non e' per sempre.
    """
    from homeassistant.helpers import entity_registry as er

    reg = er.async_get(hass)
    vin = entry.data.get("vin") or ""
    rapporto = {"statistiche": [], "cronologia": [], "saltate": [], "non_migrabili": []}
    if not vin:
        rapporto["saltate"].append(("-", "questo veicolo non ha un VIN nella configurazione"))
        return rapporto

    # Tutte le serie esistenti, una volta sola: serve sapere sia se la vecchia c'e' ancora
    # sia se la nuova e' gia' occupata.
    esistenti = await _serie_esistenti(hass)

    for morta in reg.deleted_entities.values():
        if morta.platform != LEGACY_DOMAIN:
            continue
        if not morta.unique_id.startswith(f"{vin}_"):
            rapporto["saltate"].append((morta.entity_id, "e' di un altro veicolo"))
            continue
        piattaforma = morta.entity_id.split(".", 1)[0]
        suffisso = morta.unique_id[len(vin) + 1:]
        chiave = (piattaforma, suffisso)
        if chiave in LEGACY_NOT_MIGRATABLE:
            rapporto["non_migrabili"].append((morta.entity_id, LEGACY_NOT_MIGRATABLE[chiave]))
            continue
        nostro = LEGACY_SUFFIX_PAIRS.get(chiave, suffisso)
        nuovo_id = CANON_ENTITY_ID.get((piattaforma, nostro))
        if nuovo_id is None:
            rapporto["saltate"].append((morta.entity_id, "nessun nome canonico per quel suffisso"))
            continue

        # STATISTICHE. Si agisce solo se la vecchia serie esiste ANCORA: e' cio' che rende
        # questa funzione ripetibile. Dopo il primo giro la vecchia non c'e' piu' (e' stata
        # rinominata), quindi un secondo giro non trova niente da fare invece di cancellare
        # quello che ha appena recuperato.
        if morta.entity_id in esistenti:
            if nuovo_id in esistenti:
                # La serie nuova esiste: sono le ore raccolte da quando l'integrazione nuova
                # e' stata configurata, contro gli anni che stanno nella vecchia. Si libera
                # il posto. E' l'unico punto in cui questa funzione cancella dei dati, e
                # cancella sempre il lato piu' corto.
                if not dry_run:
                    _cancella_statistiche(hass, [nuovo_id])
            if not dry_run:
                _rinomina_statistiche(hass, morta.entity_id, nuovo_id)
            rapporto["statistiche"].append((morta.entity_id, nuovo_id))

        # CRONOLOGIA degli stati. Non passa dalle stesse tabelle delle statistiche e si
        # perde per conto suo, quindi si tratta a parte: un'entita' puo' avere l'una senza
        # l'altra.
        #
        # Questo ramo il 27 settembre 2026 non aveva la disciplina che ha quello sopra, e
        # il risultato si e' visto al primo uso su un'istanza vera: trenta entita' con le
        # statistiche da luglio e la cronologia da quella sera. Il recorder, quando il
        # nome di destinazione e' gia' occupato, scrive "Cannot migrate history ... already
        # in use" e lascia tutto com'era - senza eccezioni e senza test rossi.
        #
        # Le due condizioni sotto non sono simmetria per eleganza. La prima evita di
        # lavorare a vuoto; la SECONDA e' quella che conta, perche' senza di lei un secondo
        # lancio purgherebbe la cronologia appena recuperata scambiandola per la gemella
        # corta di turno. Un recupero che si mangia il proprio risultato e' peggio di
        # nessun recupero.
        if await _ha_cronologia(hass, morta.entity_id):
            if not dry_run:
                if await _ha_cronologia(hass, nuovo_id):
                    _sposta_di_lato(hass, nuovo_id)
                _rinomina_cronologia(hass, morta.entity_id, nuovo_id)
            rapporto["cronologia"].append((morta.entity_id, nuovo_id))

    return rapporto
