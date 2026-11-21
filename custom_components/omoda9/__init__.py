"""Custom component Omoda 9 / Jaecoo — bootstrap.

Sostituisce il bridge standalone (`ha_bridge.py`): la logica MQTT/REST vive in
`coordinator.py`, le entità sono native (niente più MQTT Discovery). Il "cuore di
protocollo" (auth, firma, comandi, sonda) è riusato da `core/` senza riscrivere
la logica già verificata sul campo.

⚠️ SCAFFOLD in costruzione: il config flow (OTP) è attivo; coordinator e platform
entità sono in via di completamento (vedi SHARING_TODO.md → roadmap component).
"""
from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

# Custom Lovelace card: static-served from this package and auto-loaded on the frontend so it
# appears in the card picker without the user adding a dashboard resource by hand. Il percorso
# URL è legato al DOMINIO (`/omoda9_card`), non al marchio: così non collide con la card di
# un'altra integrazione della piattaforma (es. `omoda_jaecoo`) installata sulla stessa macchina.
# L'elemento invece è `chery-card` (marchio), distinto da `omoda-card`.
_CARD_PATH = f"/{DOMAIN}_card"
_CARD_URL = f"{_CARD_PATH}/chery-card.js"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve e auto-carica la card Lovelace, UNA volta per istanza di Home Assistant.

    Guardato con `hass.data[f"{DOMAIN}_card"]` perché con due veicoli configurati
    `async_setup_entry` gira due volte, e registrare lo stesso static path / URL JS due volte
    fa rumore (o errore). Se il frontend non è caricato (headless) la card resta comunque
    usabile aggiungendo la risorsa a mano — quindi il fallimento non deve rompere il setup."""
    if getattr(hass, "http", None) is None or hass.data.get(f"{DOMAIN}_card"):
        return
    from homeassistant.components.http import StaticPathConfig

    lovelace_dir = os.path.join(os.path.dirname(__file__), "lovelace")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(_CARD_PATH, lovelace_dir, False)]
    )
    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.loader import async_get_integration

        # La query di versione invalida la cache del browser sulla card a ogni aggiornamento:
        # senza, si continua a vedere la VECCHIA card (il modulo è cachato duro dal frontend).
        try:
            version = (await async_get_integration(hass, DOMAIN)).version
        except Exception:  # noqa: BLE001
            version = ""
        add_extra_js_url(hass, f"{_CARD_URL}?v={version}" if version else _CARD_URL)
    except Exception:  # noqa: BLE001 — frontend non caricato (headless) → card usabile a mano
        pass
    hass.data[f"{DOMAIN}_card"] = True

# P2-2: il "cuore di protocollo" è ora il sotto-pacchetto `.core`, importato normalmente
# (`from .core import commands`). Sono spariti — e con loro un'intera classe di problemi:
#
#   * `sys.path.insert(core/)`: inquinava il path dell'intero processo Home Assistant,
#     esponendo nomi generici (`commands`, `session`, `wake`) alle collisioni con altre
#     integrazioni;
#   * la cancellazione del `__pycache__` a ogni import e il ricaricamento da disco a ogni
#     setup: servivano solo perché i nomi nudi rendevano ambiguo QUALE modulo si stesse
#     caricando. Con gli import di pacchetto è Python a garantirlo, e l'aggiornamento
#     HACS invalida la cache da sé (i .pyc sono indicizzati per percorso completo).
#
# Effetto collaterale utile: i logger dei moduli core/ ora rispondono a `manifest.loggers`.


async def _async_register_adoption_service(hass: HomeAssistant) -> None:
    """Registra il servizio di adozione delle entita' della linea `omoda_jaecoo`.

    E' un SERVIZIO e non un passo automatico del setup, di proposito. Un'integrazione che
    si prende le entita' di un'altra senza che nessuno l'abbia chiesto e' inaccettabile
    anche quando ha ragione, e questa gira su un'API che nessuna delle 1401 integrazioni di
    serie usa. Lo deve chiedere una persona, sapendo cosa comporta.
    """
    from .legacy import LEGACY_DOMAIN, adotta, recupera_storico

    if hass.services.has_service(DOMAIN, "adopt_legacy_entities"):
        return

    async def _esegui(call) -> None:
        dry = call.data.get("dry_run", True)
        # L'integrazione vecchia deve essere SCARICATA: Home Assistant rifiuta di spostare
        # un'entita' gia' montata ("Only entities that haven't been loaded can be migrated").
        # Meglio dirlo prima che fallire cinquanta volte di fila.
        caricate = [e for e in hass.config_entries.async_entries(LEGACY_DOMAIN)
                    if e.state == ConfigEntryState.LOADED]
        if caricate:
            raise HomeAssistantError(
                f"L'integrazione {LEGACY_DOMAIN} e' ancora attiva. Disattivala "
                "(Impostazioni, Dispositivi e servizi, menu della vecchia, Disattiva), "
                "poi rilancia questo servizio.")

        for entry in hass.config_entries.async_entries(DOMAIN):
            rapporto = await hass.async_add_executor_job(adotta, hass, entry, dry)
            _LOGGER.warning(
                "Omoda9 adozione%s: %d adottate, %d sostituite, %d non migrabili, %d saltate",
                " (prova a vuoto)" if dry else "",
                len(rapporto["adottate"]), rapporto["sostituite"],
                len(rapporto["non_migrabili"]), len(rapporto["saltate"]))
            for vecchio, motivo in rapporto["non_migrabili"]:
                _LOGGER.warning("Omoda9 adozione: %s non migrabile - %s", vecchio, motivo)
            for vecchio, motivo in rapporto["saltate"]:
                _LOGGER.warning("Omoda9 adozione: %s saltata - %s", vecchio, motivo)

    hass.services.async_register(DOMAIN, "adopt_legacy_entities", _esegui)

    async def _recupera(call) -> None:
        """Il caso di chi ha gia' disinstallato la vecchia: le entita' non ci sono piu', i
        dati si'. Non serve che l'integrazione vecchia esista, ne' che sia spenta."""
        dry = call.data.get("dry_run", True)
        for entry in hass.config_entries.async_entries(DOMAIN):
            r = await recupera_storico(hass, entry, dry_run=dry)
            _LOGGER.warning(
                "Omoda9 recupero storico%s: %d serie statistiche, %d cronologie, "
                "%d non migrabili, %d saltate",
                " (prova a vuoto)" if dry else "",
                len(r["statistiche"]), len(r["cronologia"]),
                len(r["non_migrabili"]), len(r["saltate"]))
            for vecchio, nuovo in r["statistiche"]:
                _LOGGER.warning("Omoda9 recupero: statistiche %s -> %s", vecchio, nuovo)
            for vecchio, motivo in r["non_migrabili"] + r["saltate"]:
                _LOGGER.warning("Omoda9 recupero: %s non recuperata - %s", vecchio, motivo)

    hass.services.async_register(DOMAIN, "recover_legacy_history", _recupera)


async def _async_migrate_entity_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Porta gli entity_id gia' registrati ai nomi inglesi, una volta sola e in silenzio.

    Perche' serve, e perche' il codice da solo non basta. Home Assistant ritrova un'entita'
    dal suo `unique_id` e riusa l'`entity_id` che ha gia' in registro: l'`entity_id` che il
    codice calcola vale solo alla PRIMA registrazione. Senza questa funzione chi e' gia'
    installato terrebbe `sensor.omoda9_batteria` per sempre e solo le installazioni nuove
    avrebbero i nomi inglesi - il peggiore dei due mondi, perche' una issue aperta da due
    utenti diversi parlerebbe di due entita' con nomi diversi.

    Cosa NON si perde: lo storico. Rinominando attraverso il registro, il recorder sposta da
    solo le statistiche a lungo termine e la cronologia degli stati (vedi
    `recorder/entity_registry.py`). Grafici e dashboard Energia continuano.

    Cosa si perde comunque, e nessuna migrazione puo' evitarlo: i riferimenti scritti a mano
    in automazioni, script e dashboard. Sono elencati nelle note di rilascio con la tabella
    vecchio -> nuovo.

    L'unico modo in cui il recorder fallisce e' silenzioso: se l'`entity_id` di destinazione
    esiste gia', logga "Cannot migrate history ... already in use" e lo storico resta
    indietro. Per questo qui si salta invece di sovrascrivere, e lo si dice a WARNING.
    """
    from homeassistant.helpers import entity_registry as er

    from .naming import ENGLISH_KEYS, ID_PREFIX

    reg = er.async_get(hass)
    esistenti = {e.entity_id for e in reg.entities.values()}
    fatti = 0
    for voce in er.async_entries_for_config_entry(reg, entry.entry_id):
        piattaforma, _, object_id = voce.entity_id.partition(".")
        if not object_id.startswith(f"{DOMAIN}_"):
            continue
        inglese = ENGLISH_KEYS.get(object_id[len(DOMAIN) + 1:])
        if inglese is None:
            continue
        nuovo = f"{piattaforma}.{ID_PREFIX}_{inglese}"
        if nuovo == voce.entity_id:
            continue
        if nuovo in esistenti:
            _LOGGER.warning(
                "Omoda9: %s non rinominata in %s perche' quel nome e' gia' in uso. "
                "Lo storico resterebbe indietro, quindi non si tocca niente.",
                voce.entity_id, nuovo)
            continue
        reg.async_update_entity(voce.entity_id, new_entity_id=nuovo)
        esistenti.discard(voce.entity_id)
        esistenti.add(nuovo)
        fatti += 1
    if not fatti:
        return
    _LOGGER.info(
        "Omoda9: %d entita' rinominate ai nomi inglesi. Storico e statistiche seguono; "
        "i riferimenti scritti a mano in automazioni e dashboard vanno aggiornati.", fatti)

    # Un elenco dentro un file del repository non lo apre nessuno, e la domanda che l'utente
    # si fa e' "quali sono le mie?". Home Assistant ha il posto giusto per rispondere: un
    # avviso di riparazione, che compare in Impostazioni e resta finche' non lo si chiude.
    # Non e' "fixabile" perche' non c'e' niente che possiamo riparare al posto suo: le sue
    # automazioni le conosce solo lui. Serve a dire COSA e' successo e DOVE guardare.
    from homeassistant.helpers import issue_registry as ir
    ir.async_create_issue(
        hass, DOMAIN, f"entity_ids_rinominati_{entry.entry_id}",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="entity_ids_renamed",
        translation_placeholders={
            "count": str(fatti),
            "url": ("https://github.com/chery-connect-ha/omoda9-ha/blob/master/"
                    "docs/entity-id-rename.md"),
        },
    )


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Inizializza l'integrazione da un config entry."""
    from .coordinator import Omoda9Coordinator

    # PRIMA di costruire qualunque entita': il rename tocca il registro, e il registro va
    # sistemato mentre nessuna entita' e' ancora montata.
    await _async_migrate_entity_ids(hass, entry)

    coordinator = Omoda9Coordinator(hass, entry)

    # FASE 3c: i cert mutual-TLS devono esserci PRIMA di connettere l'MQTT auto.
    ok, detail = await coordinator.async_provision_certs()
    if not ok:
        raise ConfigEntryNotReady(detail)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Card Lovelace: registrata una volta sola (no-op dal secondo veicolo in poi).
    await _async_register_card(hass)

    # Servizio di adozione: disponibile sempre, eseguito solo se qualcuno lo chiama.
    await _async_register_adoption_service(hass)

    # Il monitor diagnostico va armato PRIMA del primo controllo sessione. È quel
    # controllo a decidere se aprire la riautenticazione, ed è esattamente l'evento che si
    # vuole rileggere dopo un riavvio. Armandolo dopo (com'era) il controllo d'avvio non
    # veniva mai registrato: verificato su 5 riavvii consecutivi, nel file diagnostico
    # restava un buco proprio nel momento più interessante.
    await coordinator.async_setup_diag()

    # stato sessione iniziale + avvio connessione MQTT all'auto
    await coordinator.async_check_session()
    # [H4] se QUALSIASI passo dell'avvio fallisce (connect MQTT, avvio timer, forward
    #      delle piattaforme) ripuliamo TUTTE le risorse già avviate — client paho e
    #      timer keepalive/poll — e togliamo il coordinator da hass.data, così non
    #      restano thread/timer orfani; poi rilanciamo → HA ritenta il setup.
    try:
        await coordinator.async_start()
        # keep-alive: refresh sessione periodico per non far scadere il token da fermi
        coordinator.async_start_keepalive()
        # poll telemetria periodico (sveglia + lettura); intervalli dalle opzioni
        coordinator.async_start_telemetry_poll()
        # battito di rilevamento marcia (sola lettura): fa partire il refresh automatico durante un
        # viaggio. No-op se l'interruttore "Aggiornamento automatico" è spento (lo riavvia lo switch).
        coordinator.async_start_drive_watch()
        # ricarica l'entry quando l'utente cambia le opzioni (es. intervalli di poll)
        entry.async_on_unload(entry.add_update_listener(_async_options_updated))
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        # backfill identità veicolo (nome device dinamico) per gli entry creati prima che il
        # config flow la salvasse: in background, così un eventuale reload avviene a setup finito.
        hass.async_create_background_task(
            coordinator.async_ensure_vehicle_identity(), "omoda9_vehicle_identity")
    except Exception:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        await hass.async_add_executor_job(coordinator.async_stop)
        raise
    return True


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ricarica l'entry SOLO se sono cambiate davvero le opzioni.

    `add_update_listener` scatta a ogni `async_update_entry`, anche quando a cambiare è
    `entry.data` e non le opzioni. Due conseguenze, entrambe reali:

    * il backfill dell'identità veicolo (task in background avviato dal setup) scrive in
      `entry.data` → l'entry appena avviata veniva **subito ricaricata**. Al primo avvio
      HA la caricava due volte, e se lo spegnimento arrivava mentre il reload era in volo
      il task restava appeso oltre la fase di chiusura (HA lo segnala: «Integrations
      should cancel non-critical tasks … to prevent delaying shutdown») lasciando l'entry
      in UNLOAD_IN_PROGRESS;
    * i percorsi che cambiano il PIN (Repair e riconfigura) si ricaricano **già da soli**
      in modo esplicito → il listener aggiungeva un secondo reload inutile.

    Chi ha davvero bisogno del reload è solo l'options flow (intervalli di poll, override
    del nome), che non ricarica per conto suo. Si confronta quindi con la fotografia delle
    opzioni applicate dal coordinator vivo. Se il coordinator non c'è (entry non ancora in
    `hass.data`) si ricarica, che è il comportamento prudente di prima.

    Si usa `async_schedule_reload` invece di attendere `async_reload`: il listener non
    resta appeso ad attendere il reload di se stesso, ed è HA a possedere e cancellare il
    task allo spegnimento.
    """
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator is not None and dict(entry.options or {}) == coordinator.applied_options:
        return
    hass.config_entries.async_schedule_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Scarica l'integrazione."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # [MED] solo se l'unload delle piattaforme è riuscito smontiamo il coordinator: se
    #       una piattaforma rifiuta l'unload (ok=False) HA considera l'entry ancora
    #       caricato → non distruggiamo il coordinator sotto entità ancora vive (stato
    #       coerente; HA ritenterà l'unload).
    if ok:
        coordinator = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if coordinator is not None:
            # async_stop è bloccante (loop_stop fa join del thread paho) → executor.
            await hass.async_add_executor_job(coordinator.async_stop)
        # P1-4/P2-6: qui si ripulivano `OMODA_PIN` e `OMODA_EMAIL` da `os.environ`, dove il
        # config flow li scriveva per passarli ai moduli core/. Non serve più — ed è la
        # garanzia più forte: con il contesto per-chiamata quei segreti nell'ambiente del
        # processo Home Assistant **non ci finiscono mai**, quindi non c'è nulla da
        # ripulire. (L'unico uso legittimo dell'ambiente resta quello EFFIMERO dei
        # sottoprocessi di login, che vive e muore con la singola chiamata.)
    return ok
