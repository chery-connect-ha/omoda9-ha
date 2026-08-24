"""Gli avvisi di un comando devono ARRIVARE all'utente, non solo essere prodotti.

Il difetto che questi test bloccano è stato misurato dal vivo il 2026-08-10, sull'auto vera,
mentre si collaudava la lettura della scheda tecnica. Il cursore «Durata clima» era stato messo
a 25 minuti su una vettura che ammette solo 5/10/15: la correzione ha funzionato — all'auto sono
arrivati 15 — e l'avviso che doveva dirlo è comparso su «Esito comando» alle 17:49:55.326748 ed
è sparito alle 17:49:55.339270, coperto da «invio Clima acceso…». **Dodici millisecondi.**

Il changelog prometteva «lo trovi scritto nell'esito del comando». Non era falso in linea di
principio — il messaggio veniva davvero pubblicato — ma nessun utente poteva leggerlo.

⚠️ La ragione per cui la suite non se n'era accorta merita di restare scritta, perché è un modo
di sbagliare che si ripete: i test esistenti raccolgono gli `emit` in una lista e verificano che
l'avviso *sia stato detto*. È il contratto di `core/`, ed è giusto che sia quello. Ma fra «detto»
e «letto» c'è Home Assistant, dove tutti i passaggi finiscono sullo **stesso** stato e l'ultimo
vince. Questi test guardano perciò `coordinator.data["cmd_status"]` — cioè quello che l'utente
vede davvero — e non la lista dei messaggi prodotti.

Vale per l'intera famiglia degli avvisi pre-invio (durata, campi potati, categoria negata, ciclo
dei giorni non ammesso), non solo per la durata: sull'Omoda 9 si manifesta solo quello perché
gli altri non scattano su un veicolo che ha tutti i permessi.
"""
from __future__ import annotations

import json
import time

import pytest

import fixtures as FX
from custom_components.omoda9.const import DOMAIN, NOTE_COMANDO_S
from custom_components.omoda9.coordinator import _SEP_NOTE, STATO_MAX, unisci_esito_e_note

AVVISO_DURATA = "durata 30′ non ammessa"


# ───────────────────────── la composizione, in isolamento ─────────────────────────
def test_gli_avvisi_seguono_lesito():
    """L'esito viene prima (è la domanda dell'utente: «è partito o no?»), gli avvisi dopo,
    nell'ordine in cui il comando li ha incontrati."""
    out = unisci_esito_e_note("Clima acceso ✅", ["durata corretta", "campo saltato"])
    assert out == "Clima acceso ✅ · durata corretta · campo saltato"


def test_senza_avvisi_lesito_resta_identico():
    """Il rumore nuovo per chi non ha nulla da sapere dev'essere ZERO: su un'Omoda 9 con la
    durata giusta la riga non deve cambiare di un carattere."""
    assert unisci_esito_e_note("Clima acceso ✅", []) == "Clima acceso ✅"
    assert unisci_esito_e_note("Clima acceso ✅", None) == "Clima acceso ✅"
    assert unisci_esito_e_note("Clima acceso ✅", ["", "   "]) == "Clima acceso ✅"


def test_il_nome_del_comando_non_si_ripete_davanti_a_ogni_avviso():
    """Ripeterlo costa spazio dentro un budget che è il vero motivo per cui un avviso resta fuori.

    Misurato sul profilo dell'issue #1: «Sbrina lunotto» produce un esito di 146 caratteri e un
    avviso di 121 col prefisso — 270 in tutto, e l'avviso finiva nel registro. Senza il prefisso
    ripetuto sono 254 ed entra. Nel registro il prefisso resta, perché lì ogni riga si legge da
    sola; qui l'esito lo dice già come prima cosa."""
    out = unisci_esito_e_note("Sbrina lunotto: HTTP 200 A00084 — rifiutato",
                              ["Sbrina lunotto: il costruttore non autorizza questa funzione"])
    assert out == ("Sbrina lunotto: HTTP 200 A00084 — rifiutato · "
                   "il costruttore non autorizza questa funzione")


def test_si_toglie_solo_il_prefisso_IDENTICO():
    """Un avviso che parla di un'ALTRA cosa non deve perdere la sua intestazione."""
    out = unisci_esito_e_note("Clima acceso: HTTP 200 A00079 — ok",
                              ["Sbrina lunotto: negato", "durata 30′ non ammessa → uso 15′"])
    assert "Sbrina lunotto: negato" in out
    assert "durata 30′ non ammessa → uso 15′" in out


def test_non_si_supera_mai_il_limite_di_home_assistant():
    """255 caratteri è un limite di Home Assistant, non una preferenza tipografica: uno stato
    più lungo non si tronca da solo con grazia — va gestito qui."""
    out = unisci_esito_e_note("esito", ["x" * 100, "y" * 100, "z" * 100])
    assert len(out) <= STATO_MAX


def test_un_avviso_che_non_entra_si_conta_invece_di_troncarsi():
    """Un avviso tagliato a metà è peggio di un avviso assente: sembra completo.

    Chi non entra viene contato, e il registro li ha comunque tutti e interi."""
    out = unisci_esito_e_note("esito", ["a" * 200, "b" * 200, "c" * 200])
    assert "(+2 nel registro)" in out, out
    assert "b" * 20 not in out, "il secondo avviso è stato tagliato invece che contato"
    assert len(out) <= STATO_MAX


def test_un_avviso_accettato_non_viene_mozzato_dalla_coda():
    """Il caso che il test qui sopra NON copriva, e che sull'auto vera si è presentato subito.

    Il difetto: quando la coda «(+N nel registro)» non ci stava si accorciava «il testo» — che a
    quel punto conteneva **già gli avvisi accettati**, quindi a essere tagliato non era l'esito
    ma l'ULTIMO AVVISO. Sul profilo reale dell'issue #1 la macro freddo produceva esattamente
    questo: «…ricomposto in un'unica richiesta al c · (+1 nel registro)».

    La regola è la stessa dell'altro caso, applicata anche qui: un avviso c'è **per intero**
    oppure non c'è e si conta. Le lunghezze qui sotto ricalcano quelle vere (esito 135, avviso
    che entra ma non lascia spazio ai 20 caratteri della coda)."""
    esito = "Raffredda tutto: HTTP 200 A00079 — " + "x" * 100
    primo = "questa auto non autorizza il comando unico: " + "y" * 60 + " FINE"
    assert len(esito) + len(_SEP_NOTE) + len(primo) <= STATO_MAX        # entra…
    assert len(esito) + len(_SEP_NOTE) + len(primo) + 20 > STATO_MAX    # …ma senza la coda

    out = unisci_esito_e_note(esito, [primo, "z" * 200])

    assert len(out) <= STATO_MAX
    assert "FINE" in out or "non autorizza" not in out, f"avviso mozzato a metà: {out!r}"
    assert "(+2 nel registro)" in out, out


def test_non_si_sacrifica_un_avviso_che_ci_starebbe():
    """L'altra faccia: rinunciare a un avviso è l'ultima risorsa, non la prima.

    Le lunghezze sono quelle vere della macro freddo dopo l'accorciamento del messaggio di
    ricomposizione: l'avviso **e** la coda ci stanno entrambi, e devono esserci entrambi."""
    esito = "Raffredda tutto: HTTP 200 A00079 — " + "x" * 100
    primo = "questa auto non autorizza il comando unico: ricomposto nel clima"

    out = unisci_esito_e_note(esito, [primo, "z" * 200])

    assert primo in out, f"avviso sacrificato pur essendoci spazio: {out!r}"
    assert "(+1 nel registro)" in out and len(out) <= STATO_MAX


def test_la_coda_entra_anche_quando_lesito_e_gia_lunghissimo():
    """Caso estremo: nemmeno la coda «(+N nel registro)» ci sta. Non deve sforare lo stesso —
    a quel punto si sacrifica la fine dell'esito, che è l'ultima informazione in ordine di
    importanza, e il risultato resta comunque dentro il limite."""
    out = unisci_esito_e_note("e" * STATO_MAX, ["avviso"])
    assert len(out) <= STATO_MAX
    assert "nel registro" in out


# ───────────────────────── il percorso vero, dentro Home Assistant ─────────────────────────
class _Msg:
    """Il minimo che `_on_car_message` si aspetta da un messaggio paho."""

    def __init__(self, payload: dict) -> None:
        self.payload = json.dumps(payload).encode()
        self.topic = "app/1/test/account/msgCenter/msg"


def _coordinator(hass, entry):
    return hass.data[DOMAIN][entry.entry_id]


def _prepara(coord, cloud):
    """Vettura che ammette 5/10/15 minuti e backend che accetta tutto."""
    coord.ctx.caps = {"durate_aria": [5, 10, 15]}
    cloud.on("/asc/vehicleControl/", code="A00079")


async def test_lavviso_sopravvive_allesito_del_comando(hass, integrazione_avviata, cloud):
    """Il cuore della faccenda: dopo l'invio, l'avviso dev'essere ancora LEGGIBILE.

    Prima di questa correzione `cmd_status` conteneva soltanto «Clima acceso: … accettato ✅»
    e dell'avviso non restava traccia — se non nel registro, che l'utente non legge."""
    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)

    await coord.async_send_command("clima_on", {"times": "30"})
    await hass.async_block_till_done()

    stato = coord.data["cmd_status"]
    assert AVVISO_DURATA in stato, f"l'avviso non è arrivato all'utente: {stato!r}"
    assert "15" in stato, f"non si dice quale durata è stata usata davvero: {stato!r}"
    assert len(stato) <= STATO_MAX


async def test_la_conferma_dellauto_non_cancella_lavviso(hass, integrazione_avviata, cloud):
    """La seconda metà del difetto, e quella che rende insufficiente la prima correzione.

    L'esito dell'invio dura pochi secondi: poi arriva la conferma dell'auto e riscrive lo
    stato da capo. Riattaccare gli avvisi solo all'invio avrebbe portato la loro vita da 12
    millisecondi a 6 secondi — meglio, ma non abbastanza da chiamarlo risolto."""
    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)

    await coord.async_send_command("clima_on", {"times": "30"})
    coord._on_car_message(None, None, _Msg(FX.cmd_confirm(result="1")))
    await hass.async_block_till_done()

    stato = coord.data["cmd_status"]
    assert "confermato dall'auto" in stato, f"l'esito vero è sparito: {stato!r}"
    assert AVVISO_DURATA in stato, f"la conferma ha cancellato l'avviso: {stato!r}"


async def test_una_conferma_tardiva_non_si_prende_i_nostri_avvisi(hass, integrazione_avviata,
                                                                  cloud, monkeypatch):
    """Il canale dei push è condiviso con l'app ufficiale: una conferma che arriva molto dopo
    può benissimo essere di un comando dato dal telefono. Attaccarle i nostri avvisi
    direbbe una cosa falsa su un'azione di qualcun altro."""
    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)

    await coord.async_send_command("clima_on", {"times": "30"})
    # l'orologio avanza oltre la finestra: la conferma non è più attribuibile a noi
    coord._note_cmd_at = time.monotonic() - (NOTE_COMANDO_S + 1)
    coord._on_car_message(None, None, _Msg(FX.cmd_confirm(result="1")))
    await hass.async_block_till_done()

    stato = coord.data["cmd_status"]
    assert "confermato dall'auto" in stato
    assert AVVISO_DURATA not in stato, (
        f"avvisi di mezz'ora fa appiccicati a una conferma altrui: {stato!r}")


async def test_gli_avvisi_non_si_trascinano_sul_comando_successivo(hass, integrazione_avviata,
                                                                   cloud):
    """Gli avvisi appartengono a UN comando. Un secondo comando pulito non deve ereditare
    quelli del primo: sarebbe la stessa bugia di prima, nel verso opposto."""
    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)

    await coord.async_send_command("clima_on", {"times": "30"})
    assert AVVISO_DURATA in coord.data["cmd_status"]

    await coord.async_send_command("clima_on", {"times": "10"})   # durata ammessa: nulla da dire
    await hass.async_block_till_done()

    stato = coord.data["cmd_status"]
    assert "durata" not in stato, f"avviso ereditato dal comando precedente: {stato!r}"


async def test_un_comando_senza_avvisi_non_aggiunge_rumore(hass, integrazione_avviata, cloud):
    """Su un'Omoda 9 con una durata ammessa la riga dev'essere esattamente quella di prima."""
    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)

    esito = await coord.async_send_command("clima_on", {"times": "15"})
    await hass.async_block_till_done()

    assert " · " not in esito, f"separatore comparso senza avvisi: {esito!r}"
    assert coord.data["cmd_status"] == esito


async def test_una_conferma_arrivata_mentre_il_comando_e_in_volo(hass, integrazione_avviata,
                                                                 cloud, monkeypatch):
    """Perché gli avvisi si azzerano all'INIZIO del comando e non alla fine.

    Azzerarli alla fine sembra equivalente e non lo è: fra la pressione e l'esito ci sono
    secondi in cui il comando è in volo, e una conferma che arriva proprio lì dentro si
    porterebbe dietro gli avvisi del comando PRECEDENTE — che parlano di un'altra azione.
    ⚠️ Si misura la **composizione** della riga (`_esito_con_note`) nell'istante in cui il
    comando è in volo, non lo stato dell'entità: `_on_car_message` compone subito ma applica
    l'aggiornamento sul loop, quindi `data["cmd_status"]` letto da dentro l'invio contiene
    ancora la riga di PRIMA e mostrerebbe verde qualunque cosa. Due stesure precedenti di
    questo test sono cadute in quella trappola — restavano verdi col difetto reintrodotto —
    ed è la ragione per cui è scritto così."""
    from custom_components.omoda9.core import commands as CMD

    coord = _coordinator(hass, integrazione_avviata)
    _prepara(coord, cloud)
    await coord.async_send_command("clima_on", {"times": "30"})     # comando 1: con avviso
    assert AVVISO_DURATA in coord.data["cmd_status"]

    visto = {}

    def invio_in_volo(ctx, key, emit=lambda m: None, params=None, avvisa=None):
        # com'è composta, proprio ora, la riga di una conferma dell'auto
        visto["conferma"] = coord._esito_con_note("Comando eseguito e confermato dall'auto ✅")
        emit("invio Clima acceso (taskId:cache)…")

    monkeypatch.setattr(CMD, "send", invio_in_volo)
    coord._send_command("clima_on", {"times": "10"})                # comando 2: nulla da dire
    await hass.async_block_till_done()

    assert AVVISO_DURATA not in visto["conferma"], (
        f"la conferma si è presa gli avvisi del comando precedente: {visto['conferma']!r}")


async def test_gli_avvisi_restano_anche_se_il_comando_fallisce(hass, integrazione_avviata,
                                                              cloud):
    """È quando il comando fallisce che l'avviso serve di più: spiega PERCHÉ.

    Il backend rifiuta, la `send` solleva, e gli avvisi prodotti prima dell'invio devono
    essere comunque conservati — è la ragione del `finally` in `_send_command`."""
    coord = _coordinator(hass, integrazione_avviata)
    coord.ctx.caps = {"durate_aria": [5, 10, 15]}
    cloud.on("/asc/vehicleControl/", code="A00084")   # rifiutato dal backend

    with pytest.raises(Exception):
        await coord.async_send_command("clima_on", {"times": "30"})
    await hass.async_block_till_done()

    assert any(AVVISO_DURATA in n for n in coord._note_cmd), (
        f"gli avvisi di un comando fallito sono andati persi: {coord._note_cmd}")


async def test_il_comando_fallito_mostra_gli_avvisi_NELLO_STATO(hass, integrazione_avviata,
                                                                cloud):
    """E devono arrivare all'ENTITÀ, non solo restare in memoria.

    ⚠️ Questo test esiste perché il suo gemello qui sopra è rimasto verde mentre il difetto era
    presente, e la ragione è istruttiva: asseriva su `coord._note_cmd`, cioè sulla lista che il
    `finally` conserva per la conferma dell'auto. Ma su un comando **rifiutato** la conferma non
    arriva mai, quindi quella lista non veniva letta da nessuno: la ricomposizione dell'esito
    stava DOPO il `try`, `commands.send()` sollevava, e sullo stato restava l'esito nudo.

    È lo stesso errore di prospettiva descritto in cima al file — verificare che l'avviso sia
    stato *prodotto* invece che *letto* — ripetuto un livello più in là. Sul veicolo dell'issue
    #1 riguardava i quattro comandi che gli importano davvero: tutti rifiutati, tutti muti."""
    coord = _coordinator(hass, integrazione_avviata)
    coord.ctx.caps = {"durate_aria": [5, 10, 15]}
    cloud.on("/asc/vehicleControl/", code="A00084")   # rifiutato dal backend

    with pytest.raises(Exception):
        await coord.async_send_command("clima_on", {"times": "30"})
    await hass.async_block_till_done()

    stato = coord.data["cmd_status"]
    assert AVVISO_DURATA in stato, (
        f"il comando è stato rifiutato e l'avviso non è arrivato all'utente: {stato!r}")
    assert "A00084" in stato, (
        f"gli avvisi hanno coperto l'esito, che resta la prima cosa da leggere: {stato!r}")
    assert len(stato) <= STATO_MAX
