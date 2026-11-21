# Entity id rename: old to new

Every entity in this integration was renamed once, from an Italian id to an English
one. **Your history and your long term statistics came with it** - Home Assistant moves
them when an entity is renamed through the registry, and the integration does the rename
for you at first start. Nothing to click.

**What did not come with it: references you wrote by hand.** Automations, scripts,
dashboard cards and template sensors that name an entity in text. Find the old id in the
left column and replace it with the right one. Search and replace on your YAML works, and
in the UI the automation editor will show the old id as unknown.

The English names are not new: they are the names this integration has been showing to
English speaking users all along, taken from its own translation file.

| old | new |
|---|---|
| **binary_sensor** | |
| `binary_sensor.omoda9_a_casa` | `binary_sensor.chery_connect_at_home` |
| `binary_sensor.omoda9_alta_tensione_attiva` | `binary_sensor.chery_connect_high_voltage_active` |
| `binary_sensor.omoda9_auto_sveglia` | `binary_sensor.chery_connect_car_awake` |
| `binary_sensor.omoda9_avviso_carburante_basso` | `binary_sensor.chery_connect_low_fuel_warning` |
| `binary_sensor.omoda9_avviso_gomma_ant_dx` | `binary_sensor.chery_connect_tire_warning_front_right` |
| `binary_sensor.omoda9_avviso_gomma_ant_sx` | `binary_sensor.chery_connect_tire_warning_front_left` |
| `binary_sensor.omoda9_avviso_gomma_post_dx` | `binary_sensor.chery_connect_tire_warning_rear_right` |
| `binary_sensor.omoda9_avviso_gomma_post_sx` | `binary_sensor.chery_connect_tire_warning_rear_left` |
| `binary_sensor.omoda9_avviso_ricarica_necessaria` | `binary_sensor.chery_connect_charge_needed_warning` |
| `binary_sensor.omoda9_batteria_scarica` | `binary_sensor.chery_connect_low_battery` |
| `binary_sensor.omoda9_cofano` | `binary_sensor.chery_connect_hood` |
| `binary_sensor.omoda9_connessa` | `binary_sensor.chery_connect_connection` |
| `binary_sensor.omoda9_finestrino_anteriore_dx` | `binary_sensor.chery_connect_front_right_window` |
| `binary_sensor.omoda9_finestrino_anteriore_sx` | `binary_sensor.chery_connect_front_left_window` |
| `binary_sensor.omoda9_finestrino_posteriore_dx` | `binary_sensor.chery_connect_rear_right_window` |
| `binary_sensor.omoda9_finestrino_posteriore_sx` | `binary_sensor.chery_connect_rear_left_window` |
| `binary_sensor.omoda9_motore` | `binary_sensor.chery_connect_engine` |
| `binary_sensor.omoda9_porta_anteriore_dx` | `binary_sensor.chery_connect_front_right_door` |
| `binary_sensor.omoda9_porta_anteriore_sx` | `binary_sensor.chery_connect_front_left_door` |
| `binary_sensor.omoda9_porta_posteriore_dx` | `binary_sensor.chery_connect_rear_right_door` |
| `binary_sensor.omoda9_porta_posteriore_sx` | `binary_sensor.chery_connect_rear_left_door` |
| `binary_sensor.omoda9_portellone_in_movimento` | `binary_sensor.chery_connect_tailgate_moving` |
| `binary_sensor.omoda9_purificazione_aria` | `binary_sensor.chery_connect_air_purification` |
| `binary_sensor.omoda9_riscaldamento_parabrezza` | `binary_sensor.chery_connect_windshield_heating` |
| `binary_sensor.omoda9_sessione` | `binary_sensor.chery_connect_session` |
| `binary_sensor.omoda9_spina_ricarica` | `binary_sensor.chery_connect_charging_cable` |
| `binary_sensor.omoda9_tendina_tetto` | `binary_sensor.chery_connect_sunroof_blind` |
| **button** | |
| `button.omoda9_aggiorna_posizione` | `button.chery_connect_refresh_location` |
| `button.omoda9_aggiorna_stato_completo` | `button.chery_connect_refresh_full_status` |
| `button.omoda9_antifurto_off` | `button.chery_connect_alarm_off` |
| `button.omoda9_antifurto_on` | `button.chery_connect_alarm_on` |
| `button.omoda9_clima_raffredda_off` | `button.chery_connect_cool_everything_off` |
| `button.omoda9_clima_raffredda_on` | `button.chery_connect_cool_everything` |
| `button.omoda9_clima_riscalda_off` | `button.chery_connect_heat_everything_off` |
| `button.omoda9_clima_riscalda_on` | `button.chery_connect_heat_everything` |
| `button.omoda9_conferma_otp` | `button.chery_connect_confirm_otp` |
| `button.omoda9_finestrini_ventila` | `button.chery_connect_vent_windows` |
| `button.omoda9_localizza` | `button.chery_connect_locate_car_gps` |
| `button.omoda9_richiedi_codice_otp` | `button.chery_connect_request_otp_code` |
| `button.omoda9_sveglia_auto` | `button.chery_connect_wake_car` |
| `button.omoda9_trova_auto` | `button.chery_connect_find_car_flash_lights` |
| **climate** | |
| `climate.omoda9_clima` | `climate.chery_connect_climate` |
| **cover** | |
| `cover.omoda9_baule` | `cover.chery_connect_trunk` |
| `cover.omoda9_finestrini` | `cover.chery_connect_windows` |
| `cover.omoda9_tetto` | `cover.chery_connect_sunroof` |
| **device_tracker** | |
| `device_tracker.omoda9_posizione` | `device_tracker.chery_connect_location` |
| **lock** | |
| `lock.omoda9_serratura` | `lock.chery_connect_lock` |
| **number** | |
| `number.omoda9_durata_clima` | `number.chery_connect_climate_duration` |
| `number.omoda9_ricarica_durata` | `number.chery_connect_charge_duration` |
| **sensor** | |
| `sensor.omoda9_autonomia_benzina` | `sensor.chery_connect_fuel_range` |
| `sensor.omoda9_autonomia_benzina_miglia` | `sensor.chery_connect_petrol_range_miles` |
| `sensor.omoda9_autonomia_elettrica` | `sensor.chery_connect_electric_range` |
| `sensor.omoda9_autonomia_totale` | `sensor.chery_connect_total_range` |
| `sensor.omoda9_batteria` | `sensor.chery_connect_battery` |
| `sensor.omoda9_carburante_residuo` | `sensor.chery_connect_fuel_remaining` |
| `sensor.omoda9_chilometraggio_ibrido` | `sensor.chery_connect_hybrid_mileage` |
| `sensor.omoda9_consumo_medio_carburante` | `sensor.chery_connect_average_fuel_consumption` |
| `sensor.omoda9_consumo_medio_elettrico` | `sensor.chery_connect_average_energy_consumption` |
| `sensor.omoda9_corrente_batteria_hv` | `sensor.chery_connect_hv_battery_current` |
| `sensor.omoda9_dati_auto_aggiornati` | `sensor.chery_connect_car_data_updated` |
| `sensor.omoda9_energia_ricarica_a_casa` | `sensor.chery_connect_home_charging_energy` |
| `sensor.omoda9_energia_ricarica_fuori_casa` | `sensor.chery_connect_away_charging_energy` |
| `sensor.omoda9_esito_comando` | `sensor.chery_connect_command_result` |
| `sensor.omoda9_esito_sonda_posizione` | `sensor.chery_connect_location_probe_result` |
| `sensor.omoda9_esito_sveglia` | `sensor.chery_connect_wake_up_result` |
| `sensor.omoda9_odometro` | `sensor.chery_connect_odometer` |
| `sensor.omoda9_partenza_programmata` | `sensor.chery_connect_scheduled_departure` |
| `sensor.omoda9_presa_ricarica_rapida` | `sensor.chery_connect_fast_charging_port` |
| `sensor.omoda9_pressione_gomma_ant_dx` | `sensor.chery_connect_tire_pressure_front_right` |
| `sensor.omoda9_pressione_gomma_ant_sx` | `sensor.chery_connect_tire_pressure_front_left` |
| `sensor.omoda9_pressione_gomma_post_dx` | `sensor.chery_connect_tire_pressure_rear_right` |
| `sensor.omoda9_pressione_gomma_post_sx` | `sensor.chery_connect_tire_pressure_rear_left` |
| `sensor.omoda9_ricarica_programmata_stato` | `sensor.chery_connect_scheduled_charging_status` |
| `sensor.omoda9_riscaldamento_sedile_post_centrale` | `sensor.chery_connect_rear_center_seat_heating` |
| `sensor.omoda9_stato_ricarica` | `sensor.chery_connect_charging_status` |
| `sensor.omoda9_stato_sessione` | `sensor.chery_connect_session_status` |
| `sensor.omoda9_temperatura_gomma_ant_dx` | `sensor.chery_connect_tire_temperature_front_right` |
| `sensor.omoda9_temperatura_gomma_ant_sx` | `sensor.chery_connect_tire_temperature_front_left` |
| `sensor.omoda9_temperatura_gomma_post_dx` | `sensor.chery_connect_tire_temperature_rear_right` |
| `sensor.omoda9_temperatura_gomma_post_sx` | `sensor.chery_connect_tire_temperature_rear_left` |
| `sensor.omoda9_temperatura_impostata_dx` | `sensor.chery_connect_set_temperature_right` |
| `sensor.omoda9_temperatura_impostata_sx` | `sensor.chery_connect_set_temperature_left` |
| `sensor.omoda9_tempo_di_ricarica_residuo` | `sensor.chery_connect_remaining_charge_time` |
| `sensor.omoda9_tensione_batteria_hv` | `sensor.chery_connect_hv_battery_voltage` |
| `sensor.omoda9_tetto_stato_movimento` | `sensor.chery_connect_sunroof_movement_state` |
| `sensor.omoda9_ultima_posizione` | `sensor.chery_connect_last_position` |
| `sensor.omoda9_ultima_sveglia` | `sensor.chery_connect_last_wake_up` |
| `sensor.omoda9_ultimo_contatto` | `sensor.chery_connect_last_seen` |
| `sensor.omoda9_velocita` | `sensor.chery_connect_speed` |
| `sensor.omoda9_ventilazione_sedile_post_centrale` | `sensor.chery_connect_rear_center_seat_ventilation` |
| **switch** | |
| `switch.omoda9_aggiornamento_automatico` | `switch.chery_connect_automatic_updates` |
| `switch.omoda9_antifurto` | `switch.chery_connect_alarm` |
| `switch.omoda9_disappannamento_parabrezza` | `switch.chery_connect_windshield_defog` |
| `switch.omoda9_raffredda_tutto` | `switch.chery_connect_cool_everything` |
| `switch.omoda9_ricarica` | `switch.chery_connect_charging` |
| `switch.omoda9_ricarica_programmata` | `switch.chery_connect_scheduled_charging` |
| `switch.omoda9_riscalda_tutto` | `switch.chery_connect_heat_everything` |
| `switch.omoda9_riscaldamento_lunotto` | `switch.chery_connect_rear_window_heating` |
| `switch.omoda9_riscaldamento_sedile_guida` | `switch.chery_connect_driver_seat_heating` |
| `switch.omoda9_riscaldamento_sedile_passeggero` | `switch.chery_connect_passenger_seat_heating` |
| `switch.omoda9_riscaldamento_sedile_post_dx` | `switch.chery_connect_rear_right_seat_heating` |
| `switch.omoda9_riscaldamento_sedile_post_sx` | `switch.chery_connect_rear_left_seat_heating` |
| `switch.omoda9_riscaldamento_volante` | `switch.chery_connect_steering_wheel_heating` |
| `switch.omoda9_sbrinamento_parabrezza` | `switch.chery_connect_windshield_defrost` |
| `switch.omoda9_ventilazione_sedile_guida` | `switch.chery_connect_driver_seat_ventilation` |
| `switch.omoda9_ventilazione_sedile_passeggero` | `switch.chery_connect_passenger_seat_ventilation` |
| `switch.omoda9_ventilazione_sedile_post_dx` | `switch.chery_connect_rear_right_seat_ventilation` |
| `switch.omoda9_ventilazione_sedile_post_sx` | `switch.chery_connect_rear_left_seat_ventilation` |
| **text** | |
| `text.omoda9_codice_otp` | `text.chery_connect_otp_code` |
| **time** | |
| `time.omoda9_ricarica_orario_di_inizio` | `time.chery_connect_charge_start_time` |

110 entities.
