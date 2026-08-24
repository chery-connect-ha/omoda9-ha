"""
prova_token.py — chiama auth/oauth2/token replicando l'app.

  python3 prova_token.py <email> <code> [secret] [emailfmt] [codefmt]

  secret:   prod (default) | test | h5md5   (h5md5 = vecchio schema MD5/5c7af05e)
  emailfmt: module (default, "APP-LOGIN@<email>") | plain
  codefmt:  plain (default) | padRight32 | padLeft32 | raw  (raw = code non cifrato)

Per testare la FIRMA senza consumare OTP: usa un <code> finto (es. 000000).
Se la firma e' giusta l'errore NON sara' piu' "Authorization authentication failed".
"""
import os, sys, json, requests
# Eseguito COME SCRIPT in sottoprocesso (session.confirm_otp): import relativo con
# ripiego su quello nudo, così funziona sia importato sia lanciato da riga di comando.
try:
    from . import omoda_auth as A
    from . import mask
except ImportError:
    import omoda_auth as A
    import mask

# dove salvare il token coniato (per-account); il bridge/coordinator legge lo stesso path
_TOKEN_OUT = os.environ.get("OMODA_TOKEN_PATH", "token.json")

TOKEN_PATH = "/auth/oauth2/token"

def build_params(email, code, emailfmt, codefmt):
    em = f"APP-LOGIN@{email}" if emailfmt=="module" else email
    cv = code if codefmt=="raw" else A.sm4_code(code, codefmt)
    # ordine come nel builder app: email, code, needDecode, grant_type, scope, loginType, loginAction
    return {
        "email": em,
        "code": cv,
        "needDecode": "0",
        "grant_type": "email",
        "scope": "server",
        "loginType": "email",
        "loginAction": "1",
    }

def _dept(area):
    """`DEPT-ID` da mandare nelle intestazioni, ricavato dal prefisso internazionale.

    Quel campo è il prefisso del Paese (Italia 39, Francia 33, Germania 49) e qui veniva
    lasciato al default italiano anche per chi accede con un numero straniero. Questo modulo
    gira come sottoprocesso senza `CoreCtx`, quindi il valore va passato a mano: il prefisso
    ce l'ha già, ed è il momento in cui conta di più — il conio del token.
    Dizionario vuoto se non c'è nulla di sensato: così vale il default di `omoda_auth`."""
    cifre = "".join(ch for ch in str(area or "") if ch.isdigit()).lstrip("0")
    return {"dept_id": cifre} if cifre else {}


def build_params_mobile(phone, area, code, codefmt="plain"):
    """Parametri per il login MOBILE (SMS). L'identità è la stringa COMPOSITA
    `APP-LOGIN@<areaCode>_<numeroNazionale>` (prefisso PRIMA, numero DOPO) e il codice è SM4
    come l'email. NB: questi vanno inviati nel BODY, non in query (vedi `call`).

    ⚠️ ORDINE — verificato dal vivo (2026-08-24) confrontando due login sullo STESSO account
    Omoda (numero + e-mail): l'ordine `<numero>_<area>` fa risolvere il backend a un account
    FANTASMA vuoto (crea un utente con `areaCode`/`phone` invertiti, senza veicoli né utente TSP
    → `getTuserId` = "0", `login` = `app.service.failed`), mentre `<area>_<numero>` risolve
    all'account REALE con il veicolo (stesso tUserId del login e-mail). Era la causa del
    fallimento di OGNI login via SMS: si coniava un token per un account sbagliato. L'app
    ufficiale usa quest'ordine (prefisso_numero), coerente con come il profilo memorizza il dato
    (`areaCode`=prefisso, `phone`=numero).

    Confermato anche nel DECOMPILATO (non solo dal confronto live): `UserService::phoneVerifyLogin`
    costruisce `APP-LOGIN@{arg2}_{arg3}`, e `isValidPhoneNum2(receiver=arg3, argument=arg2)` chiama
    `AreaString.phoneMaxInputLength(arg2)` sul prefisso e `splitPhoneNumber(arg3)` (che ne stacca il
    prefisso davanti) sul numero → `arg2`=areaCode, `arg3`=number. Un `200 operation.successful` da
    solo NON conferma l'ordine: dice che la richiesta era ben formata, non a quale account è arrivata.
    Sull'account giusto la controprova è `GET /marketing/v1/app/user`, che rende `phone`/`areaCode`
    nei campi corretti, e — con un veicolo — il `queryList` non vuoto (NON `tUserId`: "0" vale anche
    «nessun utente TSP mappato»)."""
    phone = str(phone).lstrip("+").replace(" ", "")
    cv = code if codefmt == "raw" else A.sm4_code(code, codefmt)
    return {
        "mobile": f"APP-LOGIN@{area}_{phone}",
        "code": cv,
        "needDecode": "0",
        "grant_type": "mobile",
        "scope": "server",
        "loginType": "mobile",
        "loginAction": "1",
    }


def build_params_password(username, password, is_phone=False, area="39"):
    """ROPC (grant_type=password): login con USERNAME + PASSWORD, senza OTP né captcha.

    `username` è l'identificatore GREZZO (e-mail oppure numero), NON la forma composita
    `APP-LOGIN@…` che usa l'OTP; la password viaggia in chiaro dentro il TLS con `needDecode=1`.
    Verificato dal vivo (2026-08-24): risolve all'account REALE, stesso token del login e-mail.

    ⚠️ La password è una CREDENZIALE: non entra MAI in un log (solo la sua lunghezza) né in
    entry.data. Si conia il token UNA volta e da lì la sessione vive sul refresh_token, come per
    l'OTP — la password non viene conservata."""
    p = {"username": username, "password": password, "grant_type": "password",
         "scope": "server", "needDecode": "1"}
    if is_phone:
        p["loginType"] = "mobile"
        p["areaCode"] = area
    else:
        p["loginType"] = "email"
    return p


def call_password(username, password, is_phone=False, area="39", verbose=True):
    """Conia il token via ROPC (username+password). Ritorna (status, json, token)."""
    params = build_params_password(username, password, is_phone, area)
    H = A.headers_post(TOKEN_PATH, secret=A.SIGN_SECRET, **_dept(area))
    # come il login e-mail OTP: parametri in QUERY (verificato dal vivo per l'e-mail).
    r = requests.post(A.BFF + TOKEN_PATH, params=params, headers=H, timeout=20)
    try:
        j = r.json()
    except Exception:
        j = {"_raw": r.text[:300]}
    tok = j.get("access_token") or (j.get("data") or {}).get("access_token")
    if verbose:
        # ⚠️ La password NON si logga: solo la sua lunghezza. Identità mascherata con helper
        # ORDINE-INDIPENDENTI (non la composita), token redatti. Questo stdout finisce in HA.
        who = mask.numero_con_prefisso(username, area) if is_phone else mask.indirizzo_email(username)
        print(f"[login password user={who} pwd_len={len(password)}] HTTP {r.status_code}")
        print("  resp:", json.dumps(_redact(j), ensure_ascii=False)[:400])
    return r.status_code, j, tok


def call(email, code, secret="prod", emailfmt="module", codefmt="plain", verbose=True,
         phone="", area="39"):
    sec = {"prod": A.SIGN_SECRET, "test": A.SIGN_SECRET_TEST}.get(secret)
    is_mobile = bool(phone)
    if is_mobile:
        # login via SMS: identità composita + parametri nel BODY (query VUOTA)
        params = build_params_mobile(phone, area, code, codefmt)
    else:
        params = build_params(email, code, emailfmt, codefmt)
    if secret == "h5md5":
        # vecchio schema MD5/5c7af05e/marketing, niente brackets (POST)
        import hashlib, time
        ts = int(time.time()*1000)
        S, N = "5c7af05e6fbf562842ef483ee96e06a0", "chery_legend_marketing"
        sig = hashlib.md5(f"{S}{N}{TOKEN_PATH}{ts}".encode()).hexdigest()
        H = A.headers_post(TOKEN_PATH, **_dept(area))  # base
        H.update({"nonce": N, "timestamp": str(ts), "signature": sig})
    else:
        H = A.headers_post(TOKEN_PATH, secret=sec, **_dept(area))
    # ⚠️ mobile → BODY (data=), email → QUERY (params=). È la differenza che fa coniare il
    # token mobile (verificato dal vivo 2026-08-02: la forma in query dà "codice non valido").
    if is_mobile:
        r = requests.post(A.BFF + "/auth/oauth2/token", data=params, headers=H, timeout=20)
    else:
        r = requests.post(A.BFF + "/auth/oauth2/token", params=params, headers=H, timeout=20)
    try: j = r.json()
    except Exception: j = {"_raw": r.text[:300]}
    tok = j.get("access_token") or (j.get("data") or {}).get("access_token")
    if verbose:
        # LOG per il debug/supporto: la FORMA del tentativo + stato/chiave server. L'utente può
        # incollare questo blocco in una issue PUBBLICA → non deve contenere né credenziali né
        # dati personali: il codice OTP si registra solo per lunghezza e il numero mascherato
        # (le ultime 4 cifre bastano a riconoscere «è il mio numero», non a identificarlo).
        # I TOKEN sono redatti da _redact nella riga sotto.
        via = f"mobile mobile={_mask_identity(params.get('mobile'))}" if is_mobile else f"email={emailfmt}"
        print(f"[login {via} code_len={len(str(code))} code_fmt={codefmt} loc={'BODY' if is_mobile else 'QUERY'}] HTTP {r.status_code}")
        print("  resp:", json.dumps(_redact(j), ensure_ascii=False)[:400])
    return r.status_code, j, tok


def _mask_identity(mobile):
    """`APP-LOGIN@<prefisso>_<numero>` → `APP-LOGIN@<prefisso>_***<ultime 4>`: tiene la forma
    dell'identità (che è poi ciò che si sta verificando) e butta il numero. Lo stdout di questo
    script viene loggato da Home Assistant, e i log finiscono nelle issue pubbliche.

    ⚠️ Prima questa funzione, sotto le 4 cifre, restituiva la stringa **in chiaro**: una
    mascheratura che si arrende sui casi limite non è una mascheratura. La regola unica sta in
    `core/mask.py` e non ha rami che lascino passare l'originale.
    ⚠️ Nessun numero per esteso nei commenti: `check_secrets.sh` li segnala tutti."""
    return mask.identita_mobile(mobile)


def _redact(obj):
    """Copia con access_token/refresh_token oscurati (per le stampe che vanno in HA)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("access_token", "refresh_token") and v:
                out[k] = f"<{len(str(v))}ch redatto>"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    return obj

if __name__ == "__main__":
    # P1-4: email e codice OTP possono arrivare dall'ambiente (OMODA_EMAIL/OMODA_OTP) invece
    # che da argv → non compaiono in `ps`/`/proc/<pid>/cmdline`. argv resta per l'uso a mano.
    email = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("OMODA_EMAIL", "")
    code = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("OMODA_OTP", "")
    phone = os.environ.get("OMODA_PHONE", "")
    area = os.environ.get("OMODA_AREA", "39")
    # login con PASSWORD (ROPC): la password arriva SOLO dall'ambiente (mai in argv → mai in
    # `ps`/`/proc/<pid>/cmdline`), è usata una volta per coniare il token e non viene conservata.
    password = os.environ.get("OMODA_PASSWORD", "")
    if password:
        is_phone = bool(phone)
        username = phone if is_phone else email
        if not username:
            print("MOTIVO: manca l'identità (numero o e-mail) per il login con password")
            print("RESULT: FAIL")
            sys.exit(1)
        sc, j, tok = call_password(username, password, is_phone=is_phone, area=area)
    else:
        # login via SMS: serve (telefono + codice); via email: (email + codice)
        if not code or not (phone or email):
            # ⚠️ Sentinella e motivo anche qui. Prima questo ramo stampava il solo testo d'uso, e
            # `session._riga_utile` — che cerca l'ultima riga significativa — mostrava all'utente
            # una frase a caso di quel testo come «motivo del rifiuto del codice». È lo stesso
            # difetto già corretto nel gemello `login_omoda.py`, che qui era rimasto.
            print(__doc__)
            print("MOTIVO: manca il codice OTP oppure l'identità (numero o e-mail)")
            print("RESULT: FAIL")
            sys.exit(1)
        secret  = sys.argv[3] if len(sys.argv) > 3 else "prod"
        emailfmt= sys.argv[4] if len(sys.argv) > 4 else "module"
        codefmt = sys.argv[5] if len(sys.argv) > 5 else "plain"
        sc, j, tok = call(email, code, secret, emailfmt, codefmt, phone=phone, area=area)
    if tok:
        # scrittura atomica: tmp + rename (token.json mai troncato se il processo muore)
        tmp = _TOKEN_OUT + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(j, fh, indent=2, ensure_ascii=False)
        os.chmod(tmp, 0o600)   # il token è una credenziale: leggibile solo dal proprietario
        os.replace(tmp, _TOKEN_OUT)
        print(f"\n✅ LOGIN OK — token salvato in {_TOKEN_OUT}")
        print("RESULT: OK")          # H7: sentinella stabile per session.confirm_otp
        sys.exit(0)
    # H7: conio fallito → sentinella + exit code != 0 (session.py si basa su questi)
    print("RESULT: FAIL")
    sys.exit(1)
