"""Entity naming: the Italian keys this integration grew with, and their English names.

Why this table exists instead of 110 edited declarations. The keys were derived from
Italian entity names, so they ended up in two places at once: the translation lookup
and the `entity_id`. Renaming them at the declaration sites would spread the change
over thirteen files and make it unreviewable; here it is one table, one line per
entity, readable next to the old name it replaces.

The English names are not invented. Every one of them was already written and
reviewed in `translations/en.json`; this is that file's own wording, slugified.

Two English names appear twice - "Cool everything" and "Heat everything" - because a
button and a switch carry each. That is not a collision: entity ids are separated by
the entity type (`button.` vs `switch.`) and Home Assistant namespaces translation
keys per type as well. It looks like a bug in review, so it is said here.
"""
from __future__ import annotations

# Prefix of the object_id, kept out of the domain on purpose: the domain is `omoda9`
# and stays there (see docs/design/naming-and-migration.md), while what the user reads
# in an entity id is this.
ID_PREFIX = "chery_connect"

# old translation key (Italian, derived from the entity name) -> new key (English).
# The `entity_id` follows: f"{ID_PREFIX}_{new key}".
ENGLISH_KEYS: dict[str, str] = {
    # --- binary_sensor ---
    "a_casa":                         "at_home",              # At home
    "alta_tensione_attiva":           "high_voltage_active",  # High voltage active
    "auto_sveglia":                   "car_awake",            # Car awake
    "avviso_carburante_basso":        "low_fuel_warning",     # Low fuel warning
    "avviso_gomma_ant_dx":            "tire_warning_front_right",# Tire warning front right
    "avviso_gomma_ant_sx":            "tire_warning_front_left",# Tire warning front left
    "avviso_gomma_post_dx":           "tire_warning_rear_right",# Tire warning rear right
    "avviso_gomma_post_sx":           "tire_warning_rear_left",# Tire warning rear left
    "avviso_ricarica_necessaria":     "charge_needed_warning",# Charge needed warning
    "batteria_scarica":               "low_battery",          # Low battery
    "cofano":                         "hood",                 # Hood
    "connessa":                       "connection",           # Connection
    "finestrino_anteriore_dx":        "front_right_window",   # Front right window
    "finestrino_anteriore_sx":        "front_left_window",    # Front left window
    "finestrino_posteriore_dx":       "rear_right_window",    # Rear right window
    "finestrino_posteriore_sx":       "rear_left_window",     # Rear left window
    "motore":                         "engine",               # Engine
    "porta_anteriore_dx":             "front_right_door",     # Front right door
    "porta_anteriore_sx":             "front_left_door",      # Front left door
    "porta_posteriore_dx":            "rear_right_door",      # Rear right door
    "porta_posteriore_sx":            "rear_left_door",       # Rear left door
    "portellone_in_movimento":        "tailgate_moving",      # Tailgate moving
    "purificazione_aria":             "air_purification",     # Air purification
    "riscaldamento_parabrezza":       "windshield_heating",   # Windshield heating
    "sessione":                       "session",              # Session
    "spina_ricarica":                 "charging_cable",       # Charging cable
    "tendina_tetto":                  "sunroof_blind",        # Sunroof blind
    # --- button ---
    "aggiorna_posizione":             "refresh_location",     # Refresh location
    "aggiorna_stato_completo":        "refresh_full_status",  # Refresh full status
    "antifurto_off":                  "alarm_off",            # Alarm off
    "antifurto_on":                   "alarm_on",             # Alarm on
    "clima_raffredda_off":            "cool_everything_off",  # Cool everything off
    "clima_raffredda_on":             "cool_everything",      # Cool everything
    "clima_riscalda_off":             "heat_everything_off",  # Heat everything off
    "clima_riscalda_on":              "heat_everything",      # Heat everything
    "conferma_otp":                   "confirm_otp",          # Confirm OTP
    "finestrini_ventila":             "vent_windows",         # Vent windows
    "tetto_ventila":                  "vent_sunroof",         # Vent sunroof
    "localizza":                      "locate_car_gps",       # Locate car (GPS)
    "richiedi_codice_otp":            "request_otp_code",     # Request OTP code
    "sveglia_auto":                   "wake_car",             # Wake car
    "trova_auto":                     "find_car_flash_lights",# Find car (flash lights)
    # --- climate ---
    "clima":                          "climate",              # Climate
    # --- cover ---
    "baule":                          "trunk",                # Trunk
    "finestrini":                     "windows",              # Windows
    "tetto":                          "sunroof",              # Sunroof
    # --- device_tracker ---
    "posizione":                      "location",             # Location
    # --- lock ---
    "serratura":                      "lock",                 # Lock
    # --- number ---
    "durata_clima":                   "climate_duration",     # Climate duration
    "ricarica_durata":                "charge_duration",      # Charge duration
    # --- sensor ---
    # Solo su BEV confermata: nascono dopo, quando le capability sono state sondate,
    # quindi non c'erano nel registro da cui questa tabella e' stata generata. Il primo
    # rapporto da un'auto elettrica vera li ha trovati ancora in italiano.
    "potenza_di_ricarica":            "charging_power",             # Charging power
    "autonomia_wltp":                 "wltp_range",                 # WLTP range
    "efficienza_elettrica_mi_kwh":    "electric_efficiency_mi_kwh", # Electric efficiency (mi/kWh)
    "autonomia_benzina":              "fuel_range",           # Fuel range
    "autonomia_benzina_miglia":       "petrol_range_miles",   # Petrol range (miles)
    "autonomia_elettrica":            "electric_range",       # Electric range
    "autonomia_totale":               "total_range",          # Total range
    "batteria":                       "battery",              # Battery
    "carburante_residuo":             "fuel_remaining",       # Fuel remaining
    "chilometraggio_ibrido":          "hybrid_mileage",       # Hybrid mileage
    "consumo_medio_carburante":       "average_fuel_consumption",# Average fuel consumption
    "consumo_medio_elettrico":        "average_energy_consumption",# Average energy consumption
    "corrente_batteria_hv":           "hv_battery_current",   # HV battery current
    "dati_auto_aggiornati":           "car_data_updated",     # Car data updated
    "energia_ricarica_a_casa":        "home_charging_energy", # Home charging energy
    "energia_ricarica_fuori_casa":    "away_charging_energy", # Away charging energy
    "esito_comando":                  "command_result",       # Command result
    "esito_sonda_posizione":          "location_probe_result",# Location probe result
    "esito_sveglia":                  "wake_up_result",       # Wake-up result
    "odometro":                       "odometer",             # Odometer
    "partenza_programmata":           "scheduled_departure",  # Scheduled departure
    "presa_ricarica_rapida":          "fast_charging_port",   # Fast charging port
    "pressione_gomma_ant_dx":         "tire_pressure_front_right",# Tire pressure front right
    "pressione_gomma_ant_sx":         "tire_pressure_front_left",# Tire pressure front left
    "pressione_gomma_post_dx":        "tire_pressure_rear_right",# Tire pressure rear right
    "pressione_gomma_post_sx":        "tire_pressure_rear_left",# Tire pressure rear left
    "ricarica_programmata_stato":     "scheduled_charging_status",# Scheduled charging status
    "riscaldamento_sedile_post_centrale": "rear_center_seat_heating",# Rear center seat heating
    "stato_ricarica":                 "charging_status",      # Charging status
    "stato_sessione":                 "session_status",       # Session status
    "temperatura_gomma_ant_dx":       "tire_temperature_front_right",# Tire temperature front right
    "temperatura_gomma_ant_sx":       "tire_temperature_front_left",# Tire temperature front left
    "temperatura_gomma_post_dx":      "tire_temperature_rear_right",# Tire temperature rear right
    "temperatura_gomma_post_sx":      "tire_temperature_rear_left",# Tire temperature rear left
    "temperatura_impostata_dx":       "set_temperature_right",# Set temperature right
    "temperatura_impostata_sx":       "set_temperature_left", # Set temperature left
    "tempo_di_ricarica_residuo":      "remaining_charge_time",# Remaining charge time
    "tensione_batteria_hv":           "hv_battery_voltage",   # HV battery voltage
    "tetto_stato_movimento":          "sunroof_movement_state",# Sunroof movement state
    "ultima_posizione":               "last_position",        # Last position
    "ultima_sveglia":                 "last_wake_up",         # Last wake-up
    "ultimo_contatto":                "last_seen",            # Last seen
    "velocita":                       "speed",                # Speed
    "ventilazione_sedile_post_centrale": "rear_center_seat_ventilation",# Rear center seat ventilation
    # --- switch ---
    "aggiornamento_automatico":       "automatic_updates",    # Automatic updates
    "antifurto":                      "alarm",                # Alarm
    "disappannamento_parabrezza":     "windshield_defog",     # Windshield defog
    "raffredda_tutto":                "cool_everything",      # Cool everything
    "ricarica":                       "charging",             # Charging
    "ricarica_programmata":           "scheduled_charging",   # Scheduled charging
    "riscalda_tutto":                 "heat_everything",      # Heat everything
    "riscaldamento_lunotto":          "rear_window_heating",  # Rear window heating
    "riscaldamento_sedile_guida":     "driver_seat_heating",  # Driver seat heating
    "riscaldamento_sedile_passeggero": "passenger_seat_heating",# Passenger seat heating
    "riscaldamento_sedile_post_dx":   "rear_right_seat_heating",# Rear right seat heating
    "riscaldamento_sedile_post_sx":   "rear_left_seat_heating",# Rear left seat heating
    "riscaldamento_volante":          "steering_wheel_heating",# Steering wheel heating
    "sbrinamento_parabrezza":         "windshield_defrost",   # Windshield defrost
    "ventilazione_sedile_guida":      "driver_seat_ventilation",# Driver seat ventilation
    "ventilazione_sedile_passeggero": "passenger_seat_ventilation",# Passenger seat ventilation
    "ventilazione_sedile_post_dx":    "rear_right_seat_ventilation",# Rear right seat ventilation
    "ventilazione_sedile_post_sx":    "rear_left_seat_ventilation",# Rear left seat ventilation
    # --- text ---
    "codice_otp":                     "otp_code",             # OTP code
    # --- time ---
    "ricarica_orario_di_inizio":      "charge_start_time",    # Charge start time
}

