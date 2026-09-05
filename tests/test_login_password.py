"""Login con password (ROPC): la password è cifrata, va nel body, e non trapela.

Il login diretto conia il token con `grant_type=password`: la password è cifrata AES-128-CBC
(`omoda_auth.aes_cbc_password`) e mandata nel BODY, che il server decifra (`needDecode=1`).
Scelte non ovvie, verificate dal vivo il 2026-08-24, che questi test presidiano:

  * la password è AES-CBC (NON SM4, che cifra il codice OTP): in chiaro nel body il server dà
    `IllegalBlockSizeException`, cifrata SM4 dà `BadPaddingException`, cifrata AES-CBC conia;
  * i parametri vanno nel BODY: la stessa password cifrata mandata in QUERY viene rifiutata,
    perché la query non decifra affatto;
  * la password NON compare MAI in chiaro — né nei parametri costruiti, né nell'output stampato
    (che Home Assistant logga e che l'utente allega alle issue pubbliche), né nella URL.

Perché ci teniamo: è la stessa classe di bug dell'ordine-campi SMS su #14 — codice che «sembra
funzionare» e che solo un test guarda quando nessuno lo fa. Qui in più c'è una credenziale che,
a differenza di un OTP, non scade mai.
"""
from __future__ import annotations

import base64
import json


# password sintetica: NON è reale, serve solo a verificare che non trapeli.
PWD = "S3cr3t-Pa55phrase!"


def test_la_password_e_cifrata_aes_cbc_nei_parametri(core):
    """Nei parametri la password non è in chiaro: è AES-128-CBC, e si decifra al valore atteso
    (il giro completo che fa il server con `needDecode=1`)."""
    pt, A = core["prova_token"], core["omoda_auth"]
    p = pt.build_params_password("mario@rossi.it", PWD)

    assert p["password"] != PWD, "password in chiaro nei parametri"
    assert PWD not in json.dumps(p, ensure_ascii=False), "password in chiaro nei parametri"
    assert p["needDecode"] == "1" and p["grant_type"] == "password"

    from Crypto.Cipher import AES
    from Crypto.Util.Padding import unpad
    c = AES.new(A.AES_PWD_KEY, AES.MODE_CBC, A.AES_PWD_KEY)
    dec = unpad(c.decrypt(base64.b64decode(p["password"])), AES.block_size).decode("utf-8")
    assert dec == PWD, "il round-trip AES-CBC non torna alla password"


def test_la_password_va_nel_body_non_in_query(core, monkeypatch):
    """I parametri vanno nel BODY (`data=`), non in query: è ciò che il server accetta per
    decifrare, ed è anche ciò che tiene la password fuori dalla URL."""
    pt = core["prova_token"]
    visti: list[dict] = []

    class _Risposta:
        status_code = 200
        text = "{}"
        def json(self):
            return {"access_token": "x" * 128}

    monkeypatch.setattr(pt.requests, "post", lambda url, **kw: (visti.append(kw) or _Risposta()))
    pt.call_password("mario@rossi.it", PWD, verbose=False)

    assert "data" in visti[-1] and "params" not in visti[-1], "la password deve viaggiare nel body"
    assert PWD not in json.dumps(visti[-1].get("data"), ensure_ascii=False), "password in chiaro nel body"


def test_la_password_non_finisce_nei_log(core, monkeypatch, capsys):
    """Lo stdout di `prova_token` viene loggato da Home Assistant (e finisce nelle issue
    pubbliche): può uscire la FORMA del tentativo, mai la password — solo la sua lunghezza."""
    pt = core["prova_token"]

    class _Risposta:
        status_code = 200
        text = "{}"
        def json(self):
            return {"access_token": "x" * 128}

    monkeypatch.setattr(pt.requests, "post", lambda url, **kw: _Risposta())
    pt.call_password("mario@rossi.it", PWD, verbose=True)

    stampato = capsys.readouterr().out
    assert PWD not in stampato, "password in chiaro nell'output loggato da HA"
    assert "x" * 128 not in stampato, "access_token in chiaro nell'output"
    assert f"pwd_len={len(PWD)}" in stampato, "si perde perfino la lunghezza mascherata"


def test_errore_di_rete_non_espone_la_password_ne_un_traceback(core, monkeypatch, capsys):
    """Su un errore di rete `requests` solleva e `urllib3` mette la URL nel messaggio.
    `call_password` intercetta e non ne lascia uscire il testo: niente traceback, solo la CLASSE
    dell'eccezione, e comunque la password è nel body e cifrata, non nella URL."""
    pt = core["prova_token"]

    def _post(url, **kw):
        raise pt.requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: {url}")

    monkeypatch.setattr(pt.requests, "post", _post)
    sc, j, tok = pt.call_password("mario@rossi.it", PWD, verbose=True)

    stampato = capsys.readouterr().out
    assert tok is None and sc == 0
    assert PWD not in stampato, "password nell'output su errore di rete"
    assert PWD not in json.dumps(j, ensure_ascii=False), "password nel dettaglio restituito"
    assert "Traceback" not in stampato, "traceback grezzo mostrato all'utente"
