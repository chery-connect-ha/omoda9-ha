#!/usr/bin/env python3
"""Step 3 — is there per-device credential material in the provisioning responses?

Runs the read-only half of the provisioning chain implemented in
`custom_components/omoda9/core/provision.py` and scans the full JSON responses for
anything that could be a per-device enrollment: a certificate, a CSR, a keystore,
or the product/device/secret triple that Aliyun IoT Platform hands out through its
dynamic registration.

**What it does NOT do.** No `setVecDefault`, no `checkPassword`, no PIN, no
`taskId`, no `/asc/vehicleControl/*`. Nothing reaches the car. By default it does
not refresh the session either: it copies the token file to a temporary location
and uses the existing access token as-is, so the live Home Assistant session is
never rotated underneath a running instance. If that token is expired the probe
stops and says so — it never asks for an OTP.

**What it prints.** Dotted paths and the *shape* of values: type, length, an
eight-character prefix. Never a whole value, and never a prefix of anything that
carries an account identifier.

Environment (same names `provision.py` already uses):
    VIN, OMODA_TOKEN_PATH   required
    OMODA_BFF, TSP_HOST, CHANNEL_ID, OMODA_COUNTRY_ID, OMODA_TENANT_CODE  optional

Usage:
    python3 tools/enrollment_probe/step3_response_scan.py [--allow-refresh] [--json]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
import types

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
COMPONENTS = os.path.join(REPO, "custom_components")

# Long base64 that starts a DER structure, or the base64 of "-----BEGIN".
BLOB_PATTERNS = {
    "der_base64": re.compile(r"MII[A-Za-z0-9+/]{40,}"),
    "pem_base64": re.compile(r"LS0tLS1CRUdJTi"),
    "pem_literal": re.compile(r"-----BEGIN [A-Z ]+-----"),
}
LONG_STRING = 200

# Key names that would betray an enrollment. `productKey`/`deviceName`/`deviceSecret`
# together are the Aliyun IoT dynamic-registration triple.
KEY_MARKERS = (
    "cert", "pem", "csr", "p12", "keystore", "productkey", "devicename",
    "devicesecret", "iotid", "clientid", "mqttusername", "mqttpassword",
)
# Keys whose values are account data: their shape may be reported, never a prefix.
SENSITIVE_KEYS = (
    "vin", "token", "phone", "mobile", "mail", "password", "secret", "pin",
    "lat", "lon", "lng", "address", "idcard", "username", "nickname", "realname",
)


def load_core():
    """Import `omoda9.core.*` without executing the integration's `__init__.py`.

    `custom_components/omoda9/__init__.py` imports Home Assistant, which is not
    installed here. Registering a bare package object under the right name lets the
    submodules import each other with their normal relative imports.
    """
    if COMPONENTS not in sys.path:
        sys.path.insert(0, COMPONENTS)
    pkg = types.ModuleType("omoda9")
    pkg.__path__ = [os.path.join(COMPONENTS, "omoda9")]
    sys.modules.setdefault("omoda9", pkg)
    core = importlib.import_module("omoda9.core")
    return (core,
            importlib.import_module("omoda9.core.wake"),
            importlib.import_module("omoda9.core.provision"),
            importlib.import_module("omoda9.core.omoda_auth"),
            importlib.import_module("omoda9.core.context"))


def collect_secrets(ctx, access_token: str | None) -> set[str]:
    """Values that must never appear, not even as a prefix, in this output."""
    out = {ctx.vin, ctx.tuserid, ctx.email, ctx.phone, ctx.pin, access_token}
    return {s for s in out if s and isinstance(s, str) and len(s) >= 4}


def shape(key: str, value, secrets: set[str]) -> dict:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    info = {"type": type(value).__name__, "length": len(text)}
    sensitive = (any(m in key.lower() for m in SENSITIVE_KEYS)
                 or any(s in text for s in secrets))
    info["prefix8"] = "<redacted>" if sensitive else text[:8]
    return info


def scan(node, secrets: set[str], path: str = "$") -> list[dict]:
    """Walk the structure and report every path that looks like key material."""
    found: list[dict] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}"
            reasons = [f"key-name:{m}" for m in KEY_MARKERS if m in key.lower()]
            if reasons and not isinstance(value, (dict, list)):
                found.append({"path": child, "reasons": reasons,
                              **shape(key, value, secrets)})
            found += scan(value, secrets, child)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found += scan(value, secrets, f"{path}[{i}]")
    elif isinstance(node, str):
        reasons = [name for name, rx in BLOB_PATTERNS.items() if rx.search(node)]
        if len(node) > LONG_STRING:
            reasons.append(f"long-string:>{LONG_STRING}")
        if reasons:
            key = path.rsplit(".", 1)[-1]
            found.append({"path": path, "reasons": reasons, **shape(key, node, secrets)})
    return found


def key_census(node, path: str = "$", acc: dict | None = None) -> dict:
    """Every key name in the payload, with its path. Cheap, and it makes an absence
    verifiable: `productKey` missing is only a finding if you can show the full list."""
    acc = {} if acc is None else acc
    if isinstance(node, dict):
        for key, value in node.items():
            acc.setdefault(key, []).append(f"{path}.{key}")
            key_census(value, f"{path}.{key}", acc)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            key_census(value, f"{path}[{i}]", acc)
    return acc


def build_ctx(context_mod, token_path: str):
    ctx = context_mod.ctx_da_environ()
    ctx.token_path = token_path
    return ctx


def capture_login(wake, auth, ctx) -> tuple[int, dict]:
    """The BFF login call, keeping the body that `_bff_login` throws away.

    This is the same request the integration already makes every session check —
    read-only, and the most plausible place for a broker credential to ride along.
    """
    import requests
    path = "/tsp/v1/app/auth/login"
    token = wake._access_token(ctx)
    headers = auth.headers_post(path, ctx=ctx, extra={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json, text/plain, */*"})
    r = requests.post(ctx.bff + path, data=json.dumps({"channelId": ctx.channel_id}),
                      headers=headers, timeout=20)
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"_raw_len": len(r.text)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--allow-refresh", action="store_true",
                    help="permit a refresh_token rotation on the REAL token file "
                         "(off by default: rotation invalidates a running instance)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    real_token = os.environ.get("OMODA_TOKEN_PATH", "")
    if not real_token or not os.path.isfile(real_token):
        print("FAILED: OMODA_TOKEN_PATH is not set or does not point at a file.",
              file=sys.stderr)
        return 2
    if not os.environ.get("VIN"):
        print("FAILED: VIN is not set.", file=sys.stderr)
        return 2

    core, wake, provision, auth, context_mod = load_core()

    tmpdir = None
    if args.allow_refresh:
        token_path = real_token
        print("NOTE: refresh enabled — the server will rotate the refresh token.",
              file=sys.stderr)
    else:
        tmpdir = tempfile.mkdtemp(prefix="enrollment_probe_")
        token_path = os.path.join(tmpdir, "token.json")
        # copyfile + utime, not copy2: the token lives on a network share whose
        # flags cannot be copied, and the only attribute that matters here is the
        # mtime — `wake._eta_token` reads the token's age from it.
        shutil.copyfile(real_token, token_path)
        stat = os.stat(real_token)
        os.utime(token_path, (stat.st_atime, stat.st_mtime))

    try:
        ctx = build_ctx(context_mod, token_path)
        secrets = collect_secrets(ctx, wake._access_token(ctx))

        age, lifetime = wake._eta_token(ctx)
        session = {"token_present": bool(wake._access_token(ctx)),
                   "token_age_s": round(age), "token_lifetime_s": lifetime,
                   "expired_by_age": bool(lifetime and age >= lifetime)}

        user_token, tuser_id = wake._bff_login(ctx, _allow_refresh=args.allow_refresh)
        if not user_token:
            result = {"status": "STOPPED", "session": session,
                      "reason": "the BFF refused the stored session; a new OTP would be "
                                "needed and this probe must not ask for one"}
            print(json.dumps(result, indent=2) if args.json
                  else f"STOPPED: {result['reason']}\nsession: {session}")
            return 1
        session["login"] = "ok"
        session["tuser_id_present"] = bool(tuser_id)

        captures = {}
        status, body = capture_login(wake, auth, ctx)
        captures["auth/login"] = {"http": status, "body": body}
        status, body = provision.get_tuser_id()
        captures["auth/getTuserId"] = {"http": status, "body": body}
        status, body = provision.query_list()
        captures["vmc/queryList"] = {"http": status, "body": body}

        report = {"status": "OK", "session": session, "endpoints": {}}
        for name, cap in captures.items():
            census = key_census(cap["body"])
            hits = scan(cap["body"], secrets)
            report["endpoints"][name] = {
                "http": cap["http"],
                "code": cap["body"].get("code") if isinstance(cap["body"], dict) else None,
                "key_count": len(census),
                "keys": sorted(census),
                "hits": hits,
                "markers_present": {m: any(m in k.lower() for k in census)
                                    for m in KEY_MARKERS},
            }

        report["not_implemented"] = {
            "loginTSP": "no HTTP implementation exists in core/provision.py. The module "
                        "docstring records that the app's getTspToken()/loginTSP is a "
                        "native call, a no-op in the DEX, so there is nothing in this "
                        "codebase to replay and no observed request to imitate.",
        }
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"Session: token present: {'yes' if session['token_present'] else 'no'}, "
          f"age {session['token_age_s']}s of {session['token_lifetime_s']}s, "
          f"login: {session.get('login')}")
    print()
    for name, ep in report["endpoints"].items():
        print(f"--- {name}   http={ep['http']} code={ep['code']} "
              f"({ep['key_count']} distinct keys)")
        if ep["hits"]:
            for hit in ep["hits"]:
                print(f"    HIT {hit['path']}  {hit['reasons']}  "
                      f"type={hit['type']} len={hit['length']} prefix={hit['prefix8']!r}")
        else:
            print("    no blob and no marker key")
        absent = [m for m, present in ep["markers_present"].items() if not present]
        present = [m for m, ok in ep["markers_present"].items() if ok]
        print(f"    marker keys present: {present or 'none'}")
        print(f"    marker keys absent:  {', '.join(absent)}")
        print()
    print("loginTSP: " + report["not_implemented"]["loginTSP"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
