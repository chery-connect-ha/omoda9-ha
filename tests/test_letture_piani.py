"""Le due «letture gratuite»: piano di partenza e piano di ricarica, letti DALL'AUTO.

Gratuite perché non aggiungono una sola chiamata verso il cloud del costruttore: sono campi che
l'auto ci manda già e che finora buttavamo via (`appointmentTravel` compariva 0 volte in tutto il
package prima del 2026-08-10).

⚠️ **Il test che conta è `test_le_date_finte_non_vengono_esposte`.** Il record del piano di
partenza porta `createTime`, `updateTime` e `id`, che sembrano dire quando il piano è stato
impostato. **Non lo dicono: il backend li rigenera a ogni interrogazione.** Misurato confrontando
due letture reali a 6 settimane e mezzo di distanza (25/06 e 10/08):

    travelTime 350 · travelDate [1,2,3,4,5] · travelAppointMainId 63372   →  IDENTICI
    id 234252577 → 295802237 · createTime/updateTime → l'istante della lettura   →  CAMBIATI

Il contenuto è un piano vero; l'involucro è rigenerato. Esporre quelle date significherebbe dire
all'utente «impostato oggi alle 09:31» di un piano che non tocca da mesi — un dato inventato con
l'autorità del «letto dall'auto», che è il modo peggiore di sbagliare.
"""
from __future__ import annotations

import pytest


# Record reale letto dall'auto il 2026-08-10 (VIN e identificativi non sensibili qui: sono id
# interni del piano, non del veicolo).
PIANO_REALE = {
    "travelTime": 350,
    "createTime": 1786347068000,
    "travelDate": [1, 2, 3, 4, 5],
    "travelAppointMainId": 63372,
    "updateTime": 1786347068000,
    "id": 295802237,
    "switcher": 0,
}


@pytest.fixture
def sensore(core):
    """Il sensore del piano di partenza, con un coordinator finto minimale."""
    from custom_components.omoda9.sensor import Omoda9DeparturePlan

    class CoordFinto:
        data: dict = {}
        config_entry = None

    s = Omoda9DeparturePlan.__new__(Omoda9DeparturePlan)
    s.coordinator = CoordFinto()
    return s


def _con(sensore, piano):
    sensore.coordinator.data = {"realtime": {"appointmentTravelSetVOS": [piano]}}
    return sensore


# ───────────────────────── piano di partenza ─────────────────────────

def test_piano_spento_dice_disattivata(sensore):
    """`switcher = 0`: c'è un piano in memoria ma non scatterà. Mostrare l'ora sarebbe
    peggio che non mostrarla — l'utente crederebbe che l'auto parta preparata."""
    assert _con(sensore, PIANO_REALE)._live_value() == "Disattivata"
    assert sensore.extra_state_attributes["attiva"] is False


def test_piano_acceso_mostra_lorario(sensore):
    """350 minuti dalla mezzanotte = 05:50."""
    attivo = dict(PIANO_REALE, switcher=1)
    assert _con(sensore, attivo)._live_value() == "05:50"
    assert sensore.extra_state_attributes["orario"] == "05:50"


def test_i_giorni_diventano_leggibili(sensore):
    """[1,2,3,4,5] = lunedì-venerdì, stessa numerazione di `cycleData`."""
    attrs = _con(sensore, PIANO_REALE).extra_state_attributes
    assert attrs["giorni"] == [1, 2, 3, 4, 5]
    assert attrs["giorni_testo"] == "lun, mar, mer, gio, ven"


def test_le_date_finte_non_vengono_esposte(sensore):
    """⚠️ Il test che protegge dall'errore peggiore: `createTime`/`updateTime`/`id` sono
    rigenerati a ogni interrogazione e NON devono comparire fra gli attributi."""
    attrs = _con(sensore, PIANO_REALE).extra_state_attributes
    for vietato in ("createTime", "updateTime", "id", "travelAppointMainId"):
        assert vietato not in attrs, (
            f"{vietato} è un valore rigenerato dal backend: esporlo racconta all'utente "
            f"una data che non è mai stata quella in cui ha impostato il piano"
        )


@pytest.mark.parametrize("rt", [
    {}, {"appointmentTravelSetVOS": None}, {"appointmentTravelSetVOS": []},
    {"appointmentTravelSetVOS": "non una lista"}, {"appointmentTravelSetVOS": [None]},
])
def test_nessun_piano_non_esplode(sensore, rt):
    """Campo assente o malformato ⇒ nessun valore e nessun attributo, mai un'eccezione."""
    sensore.coordinator.data = {"realtime": rt}
    assert sensore._live_value() is None
    assert sensore.extra_state_attributes is None


@pytest.mark.parametrize("minuti", [-1, 1440, 99999, "abc", None])
def test_orari_impossibili_non_vengono_mostrati(sensore, minuti):
    """Un orario fuori scala è un dato sbagliato, non un viaggio esotico: meglio niente."""
    attivo = dict(PIANO_REALE, switcher=1, travelTime=minuti)
    assert _con(sensore, attivo)._live_value() is None
    assert "orario" not in (sensore.extra_state_attributes or {})


# ───────────────────────── piano di ricarica programmata ─────────────────────────

@pytest.fixture
def switch_ricarica(core):
    from custom_components.omoda9.switch import Omoda9ScheduledChargeSwitch

    class CoordFinto:
        data: dict = {"fields": {}}
        config_entry = None

    s = Omoda9ScheduledChargeSwitch.__new__(Omoda9ScheduledChargeSwitch)
    s.coordinator = CoordFinto()
    return s


def test_attributi_dal_piano_dellauto(switch_ricarica):
    """Il piano che l'auto rimanda (push 110D) diventa visibile: finora l'utente poteva vedere
    solo le proprie preferenze locali, e un piano cambiato dall'app ufficiale restava invisibile."""
    switch_ricarica.coordinator.data = {"fields": {"chargeAppointPlans": [
        {"cycleData": [1, 2, 3, 4, 5, 6, 7], "startTime": "480",
         "switchStatus": "1", "timeConsuming": "360"}]}}

    attrs = switch_ricarica.extra_state_attributes
    assert attrs["orario_sull_auto"] == "08:00"
    assert attrs["durata_ore_sull_auto"] == 6.0
    assert attrs["giorni_sull_auto"] == [1, 2, 3, 4, 5, 6, 7]


def test_attributi_anche_se_il_campo_arriva_come_stringa(switch_ricarica):
    """Il 5A02 può consegnare la lista già serializzata: stessa lettura, come fa `_live_on`."""
    switch_ricarica.coordinator.data = {"fields": {"chargeAppointPlans":
        "[{'cycleData': [1, 2, 3], 'startTime': '465', 'switchStatus': '1', 'timeConsuming': '720'}]"}}

    attrs = switch_ricarica.extra_state_attributes
    assert attrs["orario_sull_auto"] == "07:45"
    assert attrs["durata_ore_sull_auto"] == 12.0


@pytest.mark.parametrize("fields", [
    {}, {"chargeAppointPlans": None}, {"chargeAppointPlans": []},
    {"chargeAppointPlans": "spazzatura {"}, {"chargeAppointPlans": [{}]},
])
def test_nessun_piano_ricarica_nessun_attributo(switch_ricarica, fields):
    """⚠️ Il 5A02 è un diario delle VARIAZIONI: il campo manca quasi sempre, ed è normale.
    Assenza di attributi ≠ assenza di piano, e non deve mai diventare un errore."""
    switch_ricarica.coordinator.data = {"fields": fields}
    assert switch_ricarica.extra_state_attributes is None
