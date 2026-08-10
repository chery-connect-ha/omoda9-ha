"""Switch: clima + comfort (sbrinamenti, volante, sedili).

Ogni interruttore fonde lo stato di sola lettura (un campo telemetria 5A02) con i due
comandi ON/OFF del catalogo in un'unica card: ON via app = funzione attivata (clima a
21°/sbrinamenti/sedili per ~15 min con timer auto-spegnimento dell'auto), OFF = comando
di spegnimento manuale. Il toggle ATTUA sull'auto (= consenso esplicito dell'utente).

I due sedili (riscaldamento / ventilazione guida) sono MUTUAMENTE ESCLUSIVI lato auto:
accendere l'aria spegne il caldo e viceversa (verificato in telemetria) → lo riflettiamo
subito anche nello stato ottimistico, oltre che dai campi reali quando arrivano.
"""
from __future__ import annotations

import ast
import asyncio
import time

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from homeassistant.helpers.event import async_call_later
from homeassistant.util import dt as dt_util

from .const import (CAMPO_CLIMA, DOMAIN, MACRO_GRAZIA_S, MACRO_WAKE_WAIT,
                    MACRO_WAKE_WAIT_AWAKE, MACRO_PRESET_S)
from .entity import Omoda9Entity, Omoda9OptimisticMixin, field_on


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    coord = hass.data[DOMAIN][entry.entry_id]
    # NB: il clima NON è più qui → è una climate entity (climate.py) con temperatura
    # impostabile. Restano comfort/sedili/sbrinamenti + i due switch ricarica EV.
    ricarica = Omoda9ChargeSwitch(coord)
    ricarica_prog = Omoda9ScheduledChargeSwitch(coord)
    parabrezza = Omoda9ComfortSwitch(
        coord, "Omoda9 Sbrinamento parabrezza", "frontWindshieldHeat", "frontWindshieldHeat",
        "defrost_parabrezza", "defrost_parabrezza_off", "mdi:car-defrost-front")
    # Disappannamento dal clima: funzione DIVERSA dallo sbrinamento elettrico qui sopra, e l'auto
    # le distingue (campo di stato `fWinHeatingState` contro `frontWindshieldHeat`).
    # ⚠️ Il suffisso NON è il nome del campo — è l'unica differenza dal modello degli altri
    # comfort, ed è voluta: se `fWinHeatingState` diventasse un "campo ricco" sparirebbe
    # `binary_sensor.omoda9_riscaldamento_parabrezza`, che esiste da giugno, lasciando un orfano
    # `unavailable` nel registro e spezzandone lo storico. Meglio un'entità in più (105 → 106)
    # che un'entità rotta.
    disappanna = Omoda9ComfortSwitch(
        coord, "Omoda9 Disappannamento parabrezza", "disappannamento_parabrezza", "fWinHeatingState",
        "disappanna_parabrezza", "disappanna_parabrezza_off", "mdi:car-defrost-front")
    lunotto = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento lunotto", "rWinHeatingState", "rWinHeatingState",
        "defrost_lunotto", "defrost_lunotto_off", "mdi:car-defrost-rear")
    volante = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento volante", "steerWheelHeating", "steerWheelHeating",
        "volante_caldo", "volante_caldo_off", "mdi:steering")
    sedile_caldo = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento sedile guida", "dSeatHeatingState", "dSeatHeatingState",
        "sedile_guida_caldo", "sedile_guida_caldo_off", "mdi:car-seat-heater")
    sedile_aria = Omoda9ComfortSwitch(
        coord, "Omoda9 Ventilazione sedile guida", "dSeatVentilateState", "dSeatVentilateState",
        "sedile_guida_aria", "sedile_guida_aria_off", "mdi:car-seat-cooler")
    # sedili passeggero e posteriori SX/DX: stesso modello del guida (telemetria *State*
    # ↔ comando seatControl). Posteriore centrale escluso (nessun comando dedicato).
    pass_caldo = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento sedile passeggero", "pSeatHeatingState", "pSeatHeatingState",
        "sedile_passeggero_caldo", "sedile_passeggero_caldo_off", "mdi:car-seat-heater")
    pass_aria = Omoda9ComfortSwitch(
        coord, "Omoda9 Ventilazione sedile passeggero", "pSeatVentilateState", "pSeatVentilateState",
        "sedile_passeggero_aria", "sedile_passeggero_aria_off", "mdi:car-seat-cooler")
    psx_caldo = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento sedile post. SX", "lSeatHeatingState2", "lSeatHeatingState2",
        "sedile_post_sx_caldo", "sedile_post_sx_caldo_off", "mdi:car-seat-heater")
    psx_aria = Omoda9ComfortSwitch(
        coord, "Omoda9 Ventilazione sedile post. SX", "lSeatVentilateState2", "lSeatVentilateState2",
        "sedile_post_sx_aria", "sedile_post_sx_aria_off", "mdi:car-seat-cooler")
    pdx_caldo = Omoda9ComfortSwitch(
        coord, "Omoda9 Riscaldamento sedile post. DX", "rSeatHeatingState2", "rSeatHeatingState2",
        "sedile_post_dx_caldo", "sedile_post_dx_caldo_off", "mdi:car-seat-heater")
    pdx_aria = Omoda9ComfortSwitch(
        coord, "Omoda9 Ventilazione sedile post. DX", "rSeatVentilateState2", "rSeatVentilateState2",
        "sedile_post_dx_aria", "sedile_post_dx_aria_off", "mdi:car-seat-cooler")
    # caldo e aria si escludono a vicenda su OGNI sedile → wiring reciproco per coppia
    for caldo, aria in ((sedile_caldo, sedile_aria), (pass_caldo, pass_aria),
                        (psx_caldo, psx_aria), (pdx_caldo, pdx_aria)):
        caldo._exclusive = aria
        aria._exclusive = caldo
    # macro comfort "tutto" (coolingControl/heatingControl): clima + tutti i sedili (+ volante
    # e sbrinatori per il caldo) in un unico comando, come l'app. Funzionano a auto SPENTA.
    # Raffredda e riscalda si escludono a vicenda.
    # Una sola generazione per veicolo, condivisa: le due macro agiscono sullo STESSO bus
    # comfort dell'auto e si escludono a vicenda, quindi «l'ultima pressione» è l'ultima
    # fra tutte e due, non l'ultima di ciascuna.
    generazione = _GenerazioneMacro()
    raffredda = Omoda9ClimaMacroSwitch(
        coord, "Omoda9 Raffredda tutto", "raffredda_tutto",
        "clima_raffredda_on", "clima_raffredda_off", "mdi:snowflake", generazione)
    riscalda = Omoda9ClimaMacroSwitch(
        coord, "Omoda9 Riscalda tutto", "riscalda_tutto",
        "clima_riscalda_on", "clima_riscalda_off", "mdi:heat-wave", generazione)
    raffredda._exclusive = riscalda
    riscalda._exclusive = raffredda
    antifurto = Omoda9TheftAlarmSwitch(coord)
    polling = Omoda9PollingSwitch(coord)
    add([ricarica, ricarica_prog, parabrezza, disappanna, lunotto, volante,
         sedile_caldo, sedile_aria, pass_caldo, pass_aria,
         psx_caldo, psx_aria, pdx_caldo, pdx_aria,
         raffredda, riscalda, antifurto, polling])


class Omoda9ComfortSwitch(Omoda9OptimisticMixin, Omoda9Entity, SwitchEntity, RestoreEntity):
    """Interruttore comfort: ON se il campo 5A02 associato è != 0.

    Lo stato reale arriva via MQTT solo ad auto sveglia → dopo un comando si mostra
    subito lo stato target (ottimistico, vedi Omoda9OptimisticMixin) e al riavvio di
    HA si ripristina l'ultimo stato noto."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coord, name: str, suffix: str, field: str,
                 on_cmd: str, off_cmd: str, icon: str) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._field = field
        # il campo che questa entità legge: è ciò che chiude l'ottimismo (vedi il mixin)
        self._opt_keys = (field,)
        self._on_cmd = on_cmd
        self._off_cmd = off_cmd
        self._attr_icon = icon
        self._restored: bool | None = None
        self._exclusive: "Omoda9ComfortSwitch | None" = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._restored = last.state == "on"

    def _live_on(self) -> bool | None:
        return field_on(self.coordinator.data.get("fields", {}).get(self._field))

    @property
    def is_on(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        live = self._live_on()
        return live if live is not None else self._restored

    async def async_turn_on(self, **kwargs) -> None:
        # mutua esclusione: accendere questo spegne subito il gemello (es. aria↔caldo sedile)
        if self._exclusive is not None:
            self._exclusive._set_optimistic(False)
        await self._run_command(self._on_cmd, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._run_command(self._off_cmd, False)


class Omoda9ChargeSwitch(Omoda9OptimisticMixin, Omoda9Entity, SwitchEntity, RestoreEntity):
    """Ricarica IMMEDIATA on/off (chargeStartStopControl, controlType 1/0).

    Su questo canale l'auto NON pubblica uno stato "in ricarica" → lo switch è
    ottimistico: dopo il comando mostra subito il target e al riavvio ripristina
    l'ultimo stato noto. La spina collegata è il binary_sensor `Spina ricarica`."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:battery-charging"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Ricarica", "ricarica", entity_id_format=ENTITY_ID_FORMAT)
        self._restored: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._restored = last.state == "on"

    @property
    def is_on(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        return self._restored

    async def async_turn_on(self, **kwargs) -> None:
        await self._run_command("ricarica_start", True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._run_command("ricarica_stop", False)


# Per ogni macro, i campi di STATO che l'auto pubblica quando il preset è attivo.
# ⚠️ Sono i nomi dello STATO, NON quelli del corpo del comando: il comando spedisce `mSeatAiry`,
# l'auto risponde `dSeatVentilateState`. Dedurre gli uni dagli altri è impossibile e la mappa va
# tenuta a mano; sono tutti in `META` (coordinator.py), cioè sono gli stessi campi che fanno
# funzionare i singoli interruttori sedile.
# Il freddo è MISURATO: 22 ack `110C` su 31 portano tutti e cinque i campi (riconteggio
# della validazione avversariale del 10/08; gli altri 9 sono preset riusciti a metà, con il
# solo `frontHVACState`). Il caldo è in parte dedotto: dei
# suoi ack ne abbiamo osservati due, con `frontHVACState` e `rWinHeatingState`. Elencare in più
# un campo che l'auto non manda è innocuo — si guardano solo i campi PRESENTI nel messaggio.
CAMPI_PRESET = {
    "clima_raffredda_on": (CAMPO_CLIMA, "dSeatVentilateState", "pSeatVentilateState",
                           "lSeatVentilateState2", "rSeatVentilateState2"),
    "clima_riscalda_on": (CAMPO_CLIMA, "rWinHeatingState", "frontWindshieldHeat",
                          "steerWheelHeating", "dSeatHeatingState", "pSeatHeatingState",
                          "lSeatHeatingState2", "rSeatHeatingState2"),
}


class _GenerazioneMacro:
    """Numero di sequenza condiviso dalle due macro comfort: vince l'ultima pressione.

    Vive qui e non sul coordinator perché è stato dell'INTERFACCIA (quale tocco è il più
    recente), non del veicolo. Una istanza per config entry → due veicoli non si disturbano.
    """

    def __init__(self) -> None:
        self.n = 0

    def avanza(self) -> int:
        self.n += 1
        return self.n


class Omoda9ClimaMacroSwitch(Omoda9OptimisticMixin, Omoda9Entity, SwitchEntity, RestoreEntity):
    """Macro clima "tutto" (coolingControl/heatingControl): un preset che accende clima +
    TUTTI i sedili (+ sbrinatori parabrezza/lunotto e volante per il caldo) in un colpo solo,
    con un unico comando — esattamente come l'app ufficiale.

    ⚠️ I moduli comfort (clima+sedili) rispondono SOLO a vettura desta e con i sistemi
    alimentati. Premendo la macro a auto dormiente (parcheggiata da poco) tutti i moduli vanno
    in timeout. Perciò la macro SVEGLIA prima l'auto (localizza/vehicleLocation) e ATTENDE
    MACRO_WAKE_WAIT secondi che la TBOX alimenti il bus comfort, POI invia il comando — su
    ENTRAMBE le direzioni (anche lo spegnimento sveglia, così "tutto OFF" arriva ai sedili
    posteriori, che sono indipendenti dal clima). Verificato dal vivo 2026-06-21.
    Se però l'auto è GIÀ desta la sveglia si salta (vedi `_wake_then`): il bus comfort è già
    alimentato e quei 35 secondi sarebbero solo attesa a vuoto.

    Stato: l'auto non pubblica un campo "preset attivo" dedicato → interruttore a stato
    proprio (ottimistico PERSISTENTE: non viene azzerato dai messaggi telemetria, altrimenti
    non si potrebbe spegnere). ⚠️ Questo NON vuol dire che l'auto taccia: le conferme della
    macro riportano `frontHVACState` e i campi delle ventilazioni/riscaldamenti sedile, che
    sono gli stessi che fanno funzionare la card clima e i singoli interruttori sedile.
    Quei campi vengono usati per SPEGNERE l'interruttore — mai per accenderlo (vedi
    `_spento_dall_auto`), e guardando i campi presenti nel MESSAGGIO appena arrivato, non lo
    stato accumulato in `fields`, che è cumulativo e si porta dietro valori vecchi di giorni.
    Prima di questa correzione ogni disallineamento fra interruttore e auto era permanente.

    Ci sono quindi tre uscite, e ognuna copre ciò che le altre non vedono: la telemetria
    (l'auto dice che il clima è spento), la scadenza MACRO_PRESET_S (l'auto chiude il preset
    dopo ~15 min e potrebbe non pubblicare nulla mentre si riaddormenta) e, dopo un riavvio di
    Home Assistant, il riarmo della scadenza sul tempo residuo (`async_added_to_hass`): prima
    viveva solo in memoria, quindi un riavvio durante un preset lasciava l'interruttore acceso
    per sempre. Raffredda e Riscalda si escludono a vicenda."""

    _attr_device_class = SwitchDeviceClass.SWITCH

    def __init__(self, coord, name: str, suffix: str,
                 on_cmd: str, off_cmd: str, icon: str,
                 generazione: _GenerazioneMacro) -> None:
        super().__init__(coord, name, suffix, entity_id_format=ENTITY_ID_FORMAT)
        self._on_cmd = on_cmd
        self._off_cmd = off_cmd
        self._attr_icon = icon
        self._restored: bool | None = None
        self._expire_unsub = None
        self._expire_at: float | None = None   # scadenza monotona del preset in corso
        self._msg_visto = None                 # `last_seen` dell'ultimo messaggio già valutato
        self._inviato_a: float | None = None   # quando è partito l'ultimo comando di questa macro
        self._invio_in_corso = False           # pressione accolta, comando non ancora spedito
        self._gen = generazione
        self._exclusive: "Omoda9ClimaMacroSwitch | None" = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is None or last.state not in ("on", "off"):
            return
        self._restored = last.state == "on"
        if not self._restored:
            return
        # Il preset ha una fine, e quella fine non deve morire col riavvio. Ripristinare lo
        # stato senza ripristinare il TEMPO era un mezzo ripristino: l'unico meccanismo che
        # riporta la macro a OFF è la scadenza, e prima non veniva riarmata → dopo un riavvio
        # (o un aggiornamento HACS) l'interruttore restava acceso a tempo indeterminato,
        # annunciando un preset finito da un pezzo. `last_changed` è già in RestoreEntity.
        # NB: `last_changed` è l'ultimo cambio di STATO, non l'ultimo invio — chi ripreme ON
        # su una macro già accesa non lo fa avanzare, quindi la scadenza ripristinata può
        # essere più corta del vero. L'errore è nella direzione sicura (si spegne prima).
        resto = MACRO_PRESET_S - (dt_util.utcnow() - last.last_changed).total_seconds()
        if resto <= 0:
            self._restored = False      # il preset è finito mentre HA era spento
        else:
            self._arma_scadenza(resto)

    async def async_will_remove_from_hass(self) -> None:
        self._cancel_expire()
        await super().async_will_remove_from_hass()

    @property
    def is_on(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        return bool(self._restored)

    def _handle_coordinator_update(self) -> None:
        # NON si azzera lo stato sui messaggi telemetria (il mixin lo farebbe, ancorandosi a
        # `last_seen`, che avanza a OGNI messaggio anche quando non contiene nulla di
        # attinente): lo stato impostato si mantiene. Ciò che si guarda sono i campi del
        # preset, e solo per SPEGNERE — vedi `_spento_dall_auto`.
        self._spento_dall_auto()
        self.async_write_ha_state()

    def _preset_finito(self, msg: dict) -> bool:
        """Vero se QUESTO messaggio dell'auto dice che il preset non è più attivo.

        Si guarda il messaggio appena arrivato e mai `fields`, che è cumulativo: lì dentro un
        `frontWindshieldHeat` acceso settimane fa da un altro interruttore basterebbe a
        impedire per sempre lo spegnimento della macro calda.

        Due condizioni, non una. La prima è che il messaggio parli del clima e lo dia SPENTO:
        è il cuore di entrambi i preset e senza di lui non si conclude niente (un messaggio
        che porta solo un sedile a zero non dice che il preset è finito — dice che è finito
        un sedile, e spegnere la macro per quello sarebbe una bugia nell'altro verso). La
        seconda è che nessun altro campo del preset presente nel messaggio risulti acceso.

        Su una vettura che non pubblichi `frontHVACState` questa funzione è sempre falsa:
        nessuna correzione, comportamento identico a prima. È voluto — non sapere non deve
        mai produrre un'azione."""
        if field_on(msg.get(CAMPO_CLIMA)) is not False:
            return False        # campo assente, o clima ancora acceso
        return not any(field_on(msg.get(k)) is True
                       for k in CAMPI_PRESET.get(self._on_cmd, ()))

    @callback
    def _spento_dall_auto(self) -> None:
        """Correzione dalla telemetria, **a senso unico**: può solo SPEGNERE la macro.

        Perché a senso unico: `frontHVACState=1` non distingue «preset macro» da «clima acceso
        dalla card o dall'app», quindi accendere la macro da qui farebbe comparire un
        «Raffredda tutto» che nessuno ha chiesto. Spegnere, invece, è sempre difendibile: se
        il clima è spento il preset non è in corso, qualunque cosa l'abbia chiuso — la
        scadenza dei 15 minuti, il guidatore dal cruscotto, l'app ufficiale, o un nostro
        comando andato in porto mentre l'interruttore era rimasto indietro.

        Senza questa correzione ogni disallineamento era PERMANENTE: nulla poteva riportare
        l'interruttore sulla realtà prima della scadenza in memoria, e il valore lo si vedeva
        proprio nel caso in cui l'auto pubblicava la verità (2026-08-10, 16:55:17,8: telemetria
        tutto spento, interruttore acceso ancora per un quarto d'ora)."""
        dati = self.coordinator.data or {}
        marcatore = dati.get("last_seen")
        # `last_seen` avanza SOLO all'arrivo di un messaggio dell'auto, mentre le entità
        # vengono notificate anche per aggiornamenti nostri (esito comando, sonda realtime,
        # stato sessione). Senza questo confronto lo stesso messaggio verrebbe rivalutato a
        # ogni notifica.
        if marcatore is None or marcatore == self._msg_visto:
            return
        # ⚠️ Il messaggio si consuma SEMPRE, anche a macro spenta. Consumarlo solo da accesa
        # sembra un'ottimizzazione e invece è un difetto: `msg_fields` resta in `data` finché
        # non arriva il messaggio successivo, quindi alla PRIMA accensione ci si troverebbe
        # davanti un messaggio vecchio — con il clima a zero, ovviamente, visto che l'auto era
        # ferma — e lo si leggerebbe come appena arrivato, spegnendo la macro un istante dopo
        # che l'utente l'ha accesa. E basta pochissimo a scatenarlo: il nostro stesso
        # «Sveglio l'auto…» è un aggiornamento del coordinator e fa rileggere tutto.
        self._msg_visto = marcatore
        if not self.is_on:
            return
        # Finché il nostro comando non è partito, nessun messaggio può parlare del preset che
        # stiamo per chiedere: la pressione dell'utente è più recente di qualunque cosa l'auto
        # abbia detto finora. Vale soprattutto durante i 35 secondi di sveglia, che è proprio
        # quando l'auto si sveglia e pubblica il suo stato di PRIMA.
        if self._invio_in_corso:
            return
        # Dopo l'invio si aspetta prima di credere alla telemetria: l'auto continua a
        # pubblicare lo stato vecchio finché non esegue.
        #
        # ⚠️ Qui c'era un'eccezione per le CONFERME dell'auto — «una conferma è la risposta a
        # un comando già ricevuto, quindi non può essere anteriore all'esecuzione» — ed è
        # stata TOLTA perché è vera per il comando che l'ha generata e falsa per il NOSTRO
        # ultimo comando. Sequenza reale: si preme OFF ad auto dormiente (parte a +35 s), poi
        # ON pochi secondi dopo (parte subito, l'auto ormai è desta); l'ack dell'OFF arriva
        # dopo — la latenza misurata va da 8 a 38 secondi — con tutti i campi a zero, e
        # spegnerebbe l'interruttore mentre l'auto sta raffreddando per via dell'ON. Cioè
        # esattamente il sintomo da cui è nata questa release, per una strada nuova. Lo stesso
        # vale per gli ack dei comandi dell'app ufficiale, che condivide il nostro flusso di
        # push, e per il `clima_off` che manda «Aggiorna stato completo».
        # Distinguere «l'ack del MIO comando» dagli altri richiede di correlare il `seq`, che
        # spediamo e che l'auto rimanda indietro, ma non è ancora stato misurato che sia lo
        # STESSO `seq` (nella diagnostica il valore è redatto). Finché non lo è, non sapere
        # non deve produrre un'azione: si aspetta, e il caso «l'auto conferma tutto spento e
        # poi si riaddormenta» resta coperto dalla scadenza, come prima.
        if self._entro_la_grazia():
            return
        if not self._preset_finito(dati.get("msg_fields") or {}):
            return
        self._cancel_expire()
        self._set_state(False)

    def _entro_la_grazia(self) -> bool:
        """Vero se il nostro ultimo comando è troppo recente perché l'auto abbia già agito."""
        return (self._inviato_a is not None
                and (time.monotonic() - self._inviato_a) < MACRO_GRAZIA_S)

    def _cancel_expire(self) -> None:
        if self._expire_unsub is not None:
            self._expire_unsub()
            self._expire_unsub = None
        self._expire_at = None

    @callback
    def _arma_scadenza(self, durata: float) -> None:
        """Programma l'auto-spegnimento fra `durata` secondi, SOSTITUENDO il precedente.

        Sostituire e non affiancare: due `async_call_later` sulla stessa entità sono due
        spegnimenti, e il più vecchio scatta a metà del preset nuovo — succedeva con due
        accensioni ravvicinate, dove il primo ciclo armava la scadenza e il secondo la
        sovrascriveva senza cancellarla, lasciando in volo un timer che nessuno poteva più
        fermare (nemmeno lo smontaggio dell'entità, che ne cancella uno solo)."""
        self._cancel_expire()
        self._expire_at = time.monotonic() + durata
        self._expire_unsub = async_call_later(self.hass, durata, self._scaduto)

    @callback
    def _scaduto(self, _now) -> None:
        """L'auto ha chiuso il preset da sola: l'interruttore la segue."""
        self._expire_unsub = None
        self._expire_at = None
        self._set_state(False)

    def _resto_scadenza(self) -> float | None:
        """Secondi che mancano all'auto-spegnimento, o None se nessun preset è in corso."""
        if self._expire_at is None:
            return None
        return max(0.0, self._expire_at - time.monotonic())

    def _annuncia_attesa(self, secondi: float) -> None:
        """Dice all'utente che l'attesa è voluta, mentre la macro sveglia l'auto.

        È la parte che mancava: per ~35 secondi l'interfaccia non dava alcun segno di vita
        (a differenza di ogni altro comando, che scrive i suoi passaggi su «Esito comando»),
        e il silenzio faceva ripremere il tasto — cioè l'innesco della corsa fra due cicli.
        Testo corto e bilingue di proposito: finisce nello stato di
        `sensor.omoda9_esito_comando`, che Home Assistant tronca a 255 caratteri."""
        s = int(secondi)
        self.coordinator._update({
            "cmd_status": f"Sveglio l'auto: il comando parte fra ~{s} s · "
                          f"Waking the car: command goes out in ~{s} s"})

    @callback
    def _set_state(self, value: bool) -> None:
        self._set_optimistic(value)
        self._restored = value

    async def _wake_then(self, cmd: str, target: bool) -> None:
        """Sveglia l'auto SE dorme, attende che i moduli comfort siano alimentati, poi invia
        il comando. I due invii passano dalla coda comandi del coordinator (uno alla volta,
        in ordine).

        La sveglia si salta a vettura già desta: se sta pubblicando su MQTT il bus comfort è
        già alimentato, quindi il `localizza` non serve a nulla e i 35 secondi di attesa sono
        solo ritardo. Erano il vero motivo per cui la macro «non partiva»: 45-50 secondi fra
        il tocco e la conferma, con l'interruttore già acceso e nessun segno di vita → si
        ripremeva, i due cicli si accavallavano e l'auto rifiutava il secondo (A00082).
        Ad auto desta il ciclo scende a ~10-15 secondi.

        ⚠️ **Vince l'ULTIMA pressione.** Proprio perché l'attesa qui sotto dura 35 secondi o
        5 a seconda di come sta l'auto — e la scelta si fa al momento della pressione — due
        tocchi ravvicinati producono due cicli concorrenti che possono raggiungere la coda
        in ordine INVERTITO. E non è una coincidenza rara: è la prima pressione a svegliare
        l'auto, quindi è lei stessa a spingere la seconda sul ramo corto. Riprodotto dal
        vivo il 2026-08-10 con l'auto ferma: «spegni» premuto alle 16:54:38,8 (auto
        dormiente → +35 s) è partito alle 16:55:15,8, mentre «accendi» premuto dieci secondi
        dopo (auto ormai desta → +5 s) era già partito alle 16:54:54,2 — l'auto ha
        raffreddato e poi si è spenta, l'interruttore è rimasto acceso. Con 30 secondi fra i
        due comandi, invece, l'auto riparte regolarmente: non è lei a rifiutare.
        Il rimedio è una generazione condivisa: chi si risveglia dall'attesa e scopre di
        essere stato sorpassato NON spedisce. Così l'interfaccia e l'auto convergono sempre
        sullo stesso tocco, ed è anche la cancellazione del ciclo della macro gemella."""
        mia = self._gen.avanza()
        # Da qui il ciclo è «in volo»: la telemetria che arriva parla ancora di PRIMA della
        # pressione, e non deve correggere niente (vedi `_spento_dall_auto`).
        self._invio_in_corso = True
        # Stato da cui ripartire se il comando non parte: NON si assume «spento» (vedi il
        # `finally` in fondo).
        prima_on = bool(self.is_on)
        prima_resto = self._resto_scadenza()
        self._cancel_expire()
        self._set_state(target)
        spedito = False
        try:
            if self.coordinator.auto_sveglia:
                attesa = MACRO_WAKE_WAIT_AWAKE
            else:
                attesa = MACRO_WAKE_WAIT
                # sveglia CONDIVISA con il ciclo di poll: se ce n'è già una in volo si aspetta
                # quella invece di spedirne un'altra (che si prenderebbe un «veicolo occupato»).
                # Non blocca la macro se fallisce — la decisione di proseguire comunque è la
                # stessa di prima, solo che ora sta dentro al metodo condiviso.
                await self.coordinator.async_assicura_sveglia()
                self._annuncia_attesa(attesa)   # ← la finestra muta che faceva ripremere il tasto
            await asyncio.sleep(attesa)  # lascia accendere il bus comfort
            if mia != self._gen.n:
                return      # sorpassata da una pressione più recente: non si spedisce nulla
            try:
                await self.coordinator.async_send_command(cmd)
            except Exception as err:  # noqa: BLE001
                raise HomeAssistantError(f"Comando «{cmd}» non riuscito: {err}") from err
            spedito = True
            # Da qui parte la finestra in cui la telemetria non viene creduta: l'auto continua
            # a pubblicare lo stato di PRIMA finché non esegue (vedi `_spento_dall_auto`).
            self._inviato_a = time.monotonic()
            if target:
                # l'auto chiude il preset dopo ~15 min → riporta lo switch a OFF da solo
                self._arma_scadenza(MACRO_PRESET_S)
        finally:
            # ⚠️ `finally` e non tre `return`: fra la pressione e l'invio ci sono fino a 35
            # secondi di attesa, ed è la finestra più larga del componente. Un task annullato
            # lì dentro (automazione in `mode: restart`, chiamata di servizio interrotta,
            # reload dell'entry) solleva `CancelledError`, che deriva da `BaseException` e non
            # passa né da `except Exception` né da un `return`. Lasciava l'interruttore
            # ACCESO, senza scadenza (già disarmata a inizio ciclo) e con `_invio_in_corso`
            # alzato, cioè con la correzione dalla telemetria disattivata: tutte e tre le
            # uscite spente insieme, che è esattamente il difetto da cui è nata questa
            # release. È lo stesso buco già tappato in `coordinator.async_send_command` e in
            # `entity._run_command`, ed è la ragione per cui lì si usa una bandiera.
            #
            # Il ripristino si fa solo se il ciclo è ancora l'ULTIMO: se una pressione più
            # recente ha preso il comando, lo stato è cosa sua e riscriverlo lo corromperebbe.
            if mia == self._gen.n:
                self._invio_in_corso = False
                if not spedito:
                    # comando mai partito → si torna a com'era PRIMA della pressione. Metterlo
                    # sempre a «spento» sbagliava in entrambi i versi: uno spegnimento fallito
                    # lasciava l'interruttore su OFF mentre l'auto continuava il preset, e
                    # un'accensione fallita su una macro già accesa la spegneva in Home
                    # Assistant senza che l'auto ne sapesse nulla.
                    self._set_state(prima_on)
                    if prima_on and prima_resto:
                        self._arma_scadenza(prima_resto)

    async def async_turn_on(self, **kwargs) -> None:
        if self._exclusive is not None:
            # Il ciclo del gemello eventualmente in volo è già annullato dalla generazione
            # condivisa (`_wake_then` qui sotto la fa avanzare): qui resta solo da spegnerne
            # la carta nell'interfaccia.
            self._exclusive._cancel_expire()
            self._exclusive._set_state(False)
        await self._wake_then(self._on_cmd, True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._wake_then(self._off_cmd, False)


class Omoda9ScheduledChargeSwitch(Omoda9OptimisticMixin, Omoda9Entity, SwitchEntity, RestoreEntity):
    """Ricarica PROGRAMMATA on/off (chargeAppointControl, body con array annidato).

    Quando si accende, costruisce il piano dalle preferenze (entità time "orario di
    inizio" + number "durata", tutti i giorni) e invia mainSwitch=1 + piano attivo;
    spegnendo invia mainSwitch=0. Lo stato reale arriva dalla telemetria `chargeAppointPlans`.

    `startTime` è in MINUTI dalla mezzanotte. ⚠️ Il commento precedente diceva «verificato dal
    vivo: 465 = 07:45»: non lo era — 07:45 è 465/60, un'aritmetica, e nessuno aveva mai
    confrontato quel numero con l'ora mostrata dall'app. Quella falsa sicurezza è costata una
    notte di indagine sul sospetto (poi smentito) che spedissimo l'ora sfasata del fuso.
    Il riferimento è l'ora LOCALE — misurato il 2026-08-10 leggendo nell'app il piano che
    avevamo scritto noi con `startTime = 0`: mostra 00:00, non 02:00."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Ricarica programmata", "ricarica_programmata",
                         entity_id_format=ENTITY_ID_FORMAT)
        # ⚠️ Questo interruttore uno stato reale CE L'HA, a differenza di «Ricarica»: il piano
        # arriva in telemetria dentro `chargeAppointPlans` (vedi `_live_on`). Dimenticarlo qui
        # significherebbe tenere lo stato ottimistico per tutti i 15 minuti del tetto anche
        # quando l'auto ha già detto che il piano è spento.
        self._opt_keys = ("chargeAppointPlans",)
        self._restored: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._restored = last.state == "on"

    def _live_on(self) -> bool | None:
        raw = self.coordinator.data.get("fields", {}).get("chargeAppointPlans")
        if not raw:
            return None
        try:
            plans = ast.literal_eval(raw) if isinstance(raw, str) else raw
            if plans:
                return field_on(plans[0].get("switchStatus"))
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            return None
        return None

    @property
    def is_on(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        live = self._live_on()
        return live if live is not None else self._restored

    def _piano_auto(self) -> dict | None:
        """Il piano come lo riporta l'AUTO, non come l'abbiamo scelto noi."""
        raw = self.coordinator.data.get("fields", {}).get("chargeAppointPlans")
        if not raw:
            return None
        try:
            plans = ast.literal_eval(raw) if isinstance(raw, str) else raw
            return plans[0] if plans and isinstance(plans[0], dict) else None
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict | None:
        """Orario, durata e giorni **letti dall'auto**, quando li manda.

        Finora l'interruttore mostrava solo acceso/spento e l'utente poteva vedere soltanto le
        proprie preferenze locali (entità `time` e `number`): se il piano fosse stato cambiato
        dall'app ufficiale, Home Assistant non l'avrebbe mai saputo.

        ⚠️ Il canale 5A02 è un diario delle VARIAZIONI: questi attributi compaiono quando il
        piano cambia e non a ogni giro. Assenti ≠ nessun piano. Il piano completo su richiesta
        richiederebbe una chiamata nuova (`/asd/chargeAppointManage/chargeAppointQuery`), che
        oggi non facciamo di proposito: sarebbe traffico verso il cloud del costruttore, e va
        deciso, non aggiunto di nascosto."""
        piano = self._piano_auto()
        if piano is None:
            return None
        attrs: dict = {}
        try:
            minuti = int(piano["startTime"])
            if 0 <= minuti < 1440:
                attrs["orario_sull_auto"] = f"{minuti // 60:02d}:{minuti % 60:02d}"
        except (KeyError, TypeError, ValueError):
            pass
        try:
            attrs["durata_ore_sull_auto"] = round(int(piano["timeConsuming"]) / 60, 1)
        except (KeyError, TypeError, ValueError):
            pass
        giorni = piano.get("cycleData")
        if isinstance(giorni, list) and giorni:
            attrs["giorni_sull_auto"] = giorni
        return attrs or None

    def _plan(self, switch_status: int) -> dict:
        # orario di inizio in minuti-da-mezzanotte dall'entità time; fallback al vecchio
        # cursore ore (compat) e infine 08:00 se nessuna preferenza è ancora disponibile.
        mins = getattr(self.coordinator, "charge_start_minutes", None)
        if mins is None:
            mins = int(getattr(self.coordinator, "charge_start_hour", 8) or 8) * 60
        dur_h = int(getattr(self.coordinator, "charge_duration_hours", 6) or 6)
        return {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": int(mins),
                "switchStatus": switch_status, "timeConsuming": dur_h * 60}

    async def async_turn_on(self, **kwargs) -> None:
        await self._run_command("ricarica_prog_on", True,
                                {"mainSwitch": 1, "chargeAppointPlans": [self._plan(1)]})

    async def async_turn_off(self, **kwargs) -> None:
        await self._run_command("ricarica_prog_off", False,
                                {"mainSwitch": 0, "chargeAppointPlans": [self._plan(0)]})


class Omoda9PollingSwitch(Omoda9Entity, SwitchEntity, RestoreEntity):
    """Interruttore "Aggiornamento automatico": attiva/disattiva il poll periodico
    (sveglia + lettura) senza toccare le opzioni. NON è un comando all'auto: agisce solo
    sul timer locale. ON di default; lo stato si ripristina al riavvio di HA.

    Quando è OFF l'auto non viene più svegliata automaticamente: i sensori restano
    sull'ultimo valore noto (aggiornabili a mano col pulsante "Aggiorna posizione")."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:autorenew"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Aggiornamento automatico", "polling_auto",
                         entity_id_format=ENTITY_ID_FORMAT)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # ripristina l'ultima scelta: se era OFF, ferma il poll avviato di default nel setup.
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self.coordinator.set_poll_enabled(last.state == "on")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.poll_enabled)

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.set_poll_enabled(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.set_poll_enabled(False)
        self.async_write_ha_state()


class Omoda9TheftAlarmSwitch(Omoda9OptimisticMixin, Omoda9Entity, SwitchEntity, RestoreEntity):
    """Antifurto dell'auto (theftAlarm setSwitch, endpoint /act).

    ON = l'auto fa scattare l'allarme e invia avvisi in caso di movimento non autorizzato,
    scasso porte, rottura finestrini o altre effrazioni (descrizione ufficiale dell'app).
    A differenza dei comfort, lo stato NON è in telemetria MQTT: si legge via REST
    (querySwitch). Strategia: seed iniziale dalla lettura reale, poi stato ottimistico dopo
    il toggle (il setSwitch ATTUA e vuole un tasko l'auto sveglia), e ripristino dell'ultimo
    stato noto al riavvio di HA."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:shield-car"

    def __init__(self, coord) -> None:
        super().__init__(coord, "Omoda9 Antifurto", "antifurto", entity_id_format=ENTITY_ID_FORMAT)
        self._restored: bool | None = None
        self._real: bool | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None and last.state in ("on", "off"):
            self._restored = last.state == "on"
        # seed dello stato reale dal backend (read-only, best-effort: non deve rompere il setup)
        try:
            v = await self.coordinator.async_query_theft()
            if v is not None:
                self._real = v != 0
                self.async_write_ha_state()
        except Exception:  # noqa: BLE001
            pass

    @property
    def is_on(self) -> bool | None:
        if self._opt_value is not None:
            return self._opt_value
        if self._real is not None:
            return self._real
        return self._restored

    async def _rileggi_stato_reale(self) -> None:
        """Ricontrolla col backend com'è messo davvero l'antifurto (REST, sola lettura).

        ⚠️ Serve perché questa entità NON ha telemetria: senza una rilettura, `_real` resterebbe
        il valore letto all'avvio di Home Assistant e l'unica altra fonte sarebbe lo stato
        ottimistico, che decade da solo dopo `OPT_MAX_S`. Su una funzione di SICUREZZA
        significherebbe passare da «mente dopo il primo messaggio» a «mente per un quarto d'ora
        e poi ricade su un valore di stamattina»: entrambe brutte, la seconda pure silenziosa.
        È una lettura gratuita (nessun PIN, nessun taskId) e si fa solo dopo un comando andato
        a buon fine, non a ogni aggiornamento.

        ⚠️ **NON annulla lo stato ottimistico**, e non è una dimenticanza. `async_send_command`
        torna quando il backend ha ACCETTATO il comando, non quando l'auto l'ha eseguito: sul
        canale MQTT la conferma arriva fra 8 e 38 secondi. Se `querySwitch` rispecchiasse lo
        stato del veicolo e non l'intenzione registrata, leggere subito dopo restituirebbe il
        valore VECCHIO — e renderlo autoritativo farebbe tornare indietro l'interruttore un
        istante dopo la pressione, che è il difetto che questa release toglie a tutti gli
        altri. Non sappiamo quale dei due sia (misurarlo vorrebbe dire attuare sull'auto),
        quindi si aggiorna il ripiego senza agire su ciò che l'utente vede: se i due
        coincidono non cambia nulla, se divergono la verità emerge allo scadere del tetto,
        molto più fresca del valore letto all'avvio.

        ⚠️ Gira in un task di sfondo: allungare la chiamata di servizio di un giro di rete
        lascerebbe la card in attesa per una lettura che non le serve subito."""
        try:
            v = await self.coordinator.async_query_theft()
        except Exception:  # noqa: BLE001 — non deve mai far fallire un comando riuscito
            return
        if v is not None:
            self._real = v != 0
            self.async_write_ha_state()

    def _programma_rilettura(self) -> None:
        self.hass.async_create_background_task(
            self._rileggi_stato_reale(), f"{DOMAIN}_antifurto_rilettura")

    async def async_turn_on(self, **kwargs) -> None:
        await self._run_command("antifurto_on", True)
        self._programma_rilettura()

    async def async_turn_off(self, **kwargs) -> None:
        await self._run_command("antifurto_off", False)
        self._programma_rilettura()
