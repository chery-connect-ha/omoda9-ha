#!/usr/bin/env python3
"""Step 2 — does the broker actually require the client certificate?

The probe opens a TLS connection to the EMQX host and stops at the end of the
handshake: it never sends an MQTT CONNECT and never authenticates. Nothing is
written to the repository.

Three variants, and the comparison between them is the whole point:

  none        no client certificate at all;
  bundled     the certificate shipped in `certs/store.json` for this region;
  selfsigned  a throw-away RSA key and self-signed certificate generated here,
              which no Chery CA has ever seen. This is the variant that decides
              whether a user could bring their own locally generated material
              instead of the redistributed bundle.

**Why a completed handshake proves nothing on its own.** Under TLS 1.3 the client
finishes its side of the handshake before the server has had a chance to judge the
certificate it did or did not receive. A server configured with `verify_peer` and
`fail_if_no_peer_cert` therefore lets `wrap_socket()` return successfully and only
then drops the connection. The client sees "handshake_ok" followed by an immediate
EOF. So after every successful handshake this probe waits, passively, and records
what the server does: hold the connection open (accepted), close it (rejected), or
send a TLS alert such as 116 `certificate_required`. Waiting and reading is not
authenticating.

Each variant is repeated a few times, because "the connection dropped" is exactly
the kind of observation a single flaky run can fake.

Usage:
    python3 tools/enrollment_probe/step2_tls_probe.py [--host H] [--ports 8083,8883]
                                                      [--variants none,bundled,selfsigned]
                                                      [--repeat 3] [--json]
"""
from __future__ import annotations

import argparse
import datetime
import importlib.util
import json
import os
import socket
import ssl
import sys
import tempfile
import time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKAGE = os.path.join(REPO, "custom_components", "omoda9")

DEFAULT_HOST = "tspemqx-app-eu.cheryinternational.com"
# 8083 is what the integration actually dials (const.py DEFAULTS); the others are
# the conventional EMQX listeners — MQTT/TLS, alternative MQTT/TLS, WSS, plain MQTT.
DEFAULT_PORTS = "8083,8883,8884,443,1883"
VARIANTS = ("none", "bundled", "selfsigned")
TIMEOUT = 10.0
# How long to wait for the server to reveal its judgement after the handshake.
# EMQX drops a rejected peer within milliseconds; a healthy MQTT listener waits
# for the client to speak for far longer than this.
LINGER = 4.0


def load_cert_bundle():
    spec = importlib.util.spec_from_file_location(
        "_cert_bundle", os.path.join(PACKAGE, "cert_bundle.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_selfsigned() -> dict[str, bytes]:
    """A throw-away identity, generated here and trusted by nobody."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "enrollment-probe")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(minutes=5))
            .not_valid_after(now + datetime.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    return {
        "client.pem": cert.public_bytes(serialization.Encoding.PEM),
        "client.key": key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()),
    }


def describe_peer_cert(sock: ssl.SSLSocket) -> dict:
    """Server-side identity, used to tell the stack apart.

    A self-hosted EMQX presents a leaf issued by the region's own CA; Aliyun IoT
    Platform would present a `*.iot-as-mqtt.<region>.aliyuncs.com` certificate.
    That difference decides whether a dynamic-registration path can exist at all.
    """
    der = sock.getpeercert(binary_form=True)
    if not der:
        return {}
    try:
        from cryptography import x509
        cert = x509.load_der_x509_certificate(der)
        try:
            san = [f"{type(n).__name__}:{getattr(n, 'value', n)}" for n in
                   cert.extensions.get_extension_for_class(
                       x509.SubjectAlternativeName).value]
        except x509.ExtensionNotFound:
            san = []
        return {"subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "san": san,
                "not_after": cert.not_valid_after_utc.isoformat()}
    except Exception as err:  # noqa: BLE001
        return {"parse_error": f"{type(err).__name__}: {err}"}


def linger(sock: ssl.SSLSocket) -> dict:
    """Wait passively and record the server's verdict on our handshake."""
    started = time.monotonic()
    sock.settimeout(LINGER)
    try:
        data = sock.recv(16)
        elapsed = round(time.monotonic() - started, 3)
        if data:
            return {"outcome": "server_sent_bytes", "bytes": len(data), "after_s": elapsed}
        return {"outcome": "server_closed", "after_s": elapsed,
                "note": "clean EOF right after the handshake: the peer was rejected"}
    except socket.timeout:
        return {"outcome": "held_open", "after_s": round(time.monotonic() - started, 3),
                "note": "the listener is waiting for us to speak: the peer was accepted"}
    except ssl.SSLError as err:
        return {"outcome": "tls_alert", "reason": getattr(err, "reason", None),
                "after_s": round(time.monotonic() - started, 3), "detail": str(err)}
    except OSError as err:
        return {"outcome": "transport_error", "detail": f"{type(err).__name__}: {err}",
                "after_s": round(time.monotonic() - started, 3)}


def probe_once(host: str, port: int, material: dict[str, bytes] | None) -> dict:
    result: dict = {}
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # Server verification is deliberately off: the question is what the SERVER demands
    # of US, and the integration already runs with tls_insecure_set(True).
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    tmpdir = None
    if material:
        # OpenSSL can only load the key from the filesystem. It goes to a private
        # temporary directory outside the repo and is overwritten and removed below.
        tmpdir = tempfile.mkdtemp(prefix="enrollment_probe_")
        os.chmod(tmpdir, 0o700)
        paths = {}
        for name in ("client.pem", "client.key"):
            paths[name] = os.path.join(tmpdir, name)
            with open(os.open(paths[name], os.O_CREAT | os.O_WRONLY, 0o600), "wb") as f:
                f.write(material[name])
        ctx.load_cert_chain(paths["client.pem"], paths["client.key"])

    try:
        raw = socket.create_connection((host, port), timeout=TIMEOUT)
    except OSError as err:
        _wipe(tmpdir)
        return {"outcome": "tcp_failed", "error": f"{type(err).__name__}: {err}"}

    try:
        with ctx.wrap_socket(raw, server_hostname=host) as tls:
            result.update(outcome="handshake_ok",
                          tls_version=tls.version(),
                          cipher=tls.cipher()[0] if tls.cipher() else None,
                          alpn=tls.selected_alpn_protocol(),
                          server_cert=describe_peer_cert(tls))
            result["after_handshake"] = linger(tls)
    except ssl.SSLError as err:
        result.update(outcome="handshake_failed", error_class=type(err).__name__,
                      reason=getattr(err, "reason", None),
                      library=getattr(err, "library", None), detail=str(err))
    except OSError as err:
        result.update(outcome="transport_failed", error=f"{type(err).__name__}: {err}")
    finally:
        try:
            raw.close()
        except OSError:
            pass
        _wipe(tmpdir)
    return result


def _wipe(tmpdir: str | None) -> None:
    if not tmpdir:
        return
    for name in os.listdir(tmpdir):
        path = os.path.join(tmpdir, name)
        try:
            size = os.path.getsize(path)
            with open(path, "r+b") as f:
                f.write(b"\x00" * size)
            os.remove(path)
        except OSError:
            pass
    try:
        os.rmdir(tmpdir)
    except OSError:
        pass


def collapse(attempts: list[dict]) -> str:
    """One label for a set of repeats — `mixed:` when they disagree."""
    labels = []
    for a in attempts:
        if a["outcome"] != "handshake_ok":
            labels.append(a["outcome"])
        else:
            labels.append(f"handshake_ok/{a['after_handshake']['outcome']}")
    unique = sorted(set(labels))
    return unique[0] if len(unique) == 1 else "mixed:" + "|".join(unique)


ACCEPTED = "handshake_ok/held_open"
REJECTED_AFTER_HANDSHAKE = "handshake_ok/server_closed"


def serves_this_host(run: dict, host: str) -> bool | None:
    """Is the certificate on this port actually the broker's, or another service?

    Several ports on the same address answer TLS with a completely different
    service. A port that presents a certificate for another hostname says nothing
    about the broker's client-certificate policy, and reporting it as if it did
    would be the easiest way to reach a wrong conclusion.
    """
    cert = (run.get("attempts") or [{}])[0].get("server_cert") or {}
    names = [n.split(":", 1)[-1] for n in cert.get("san", [])]
    if not names and not cert.get("subject"):
        return None
    return host in names


def verdict(matrix: dict[int, dict[str, str]], foreign: dict[int, str]) -> list[str]:
    """Read the variant × port matrix into plain statements."""
    lines = []
    for port, by_variant in sorted(matrix.items()):
        if port in foreign:
            lines.append(f"port {port}: a different service answers here "
                         f"({foreign[port]}), not the broker — no conclusion about the "
                         f"broker's certificate policy.")
            continue
        none = by_variant.get("none")
        bundled = by_variant.get("bundled")
        selfsigned = by_variant.get("selfsigned")
        if none is None:
            continue
        if none.startswith("tcp_failed") or none.startswith("transport"):
            lines.append(f"port {port}: not reachable ({none}) — no conclusion.")
            continue
        if none == ACCEPTED:
            lines.append(f"port {port}: DECISIVE — the listener accepts a connection "
                         f"with NO client certificate. The certificate is irrelevant "
                         f"to the transport.")
        elif none == REJECTED_AFTER_HANDSHAKE and bundled == ACCEPTED:
            lines.append(f"port {port}: the broker REQUIRES a client certificate. The "
                         f"TLS 1.3 handshake completes either way, but without one the "
                         f"server drops the connection immediately, and with the "
                         f"bundled certificate it holds it open.")
        elif "CERTIFICATE_REQUIRED" in str(none).upper():
            lines.append(f"port {port}: the broker requires a client certificate "
                         f"(alert 116 certificate_required).")
        else:
            lines.append(f"port {port}: no certificate -> {none}"
                         f"{f'; bundled -> {bundled}' if bundled else ''}.")
        if selfsigned is not None and none == REJECTED_AFTER_HANDSHAKE:
            if selfsigned == ACCEPTED:
                lines.append(f"port {port}: and a SELF-SIGNED certificate generated "
                             f"locally is accepted too — the broker demands a "
                             f"certificate but does not check who signed it. Users "
                             f"could generate their own; the bundle is not needed.")
            else:
                lines.append(f"port {port}: a self-signed certificate is rejected "
                             f"({selfsigned}) — the material must chain to the region "
                             f"CA, so it cannot simply be generated locally.")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--ports", default=DEFAULT_PORTS)
    ap.add_argument("--variants", default=",".join(VARIANTS))
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ports = [int(p) for p in args.ports.split(",") if p.strip()]
    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    for v in variants:
        if v not in VARIANTS:
            print(f"FAILED: unknown variant {v!r}.", file=sys.stderr)
            return 2

    try:
        addresses = sorted({ai[4][0] for ai in socket.getaddrinfo(args.host, None)})
    except socket.gaierror as err:
        print(f"FAILED: {args.host} does not resolve ({err}).", file=sys.stderr)
        return 2

    materials: dict[str, dict[str, bytes] | None] = {"none": None}
    if "bundled" in variants:
        materials["bundled"] = load_cert_bundle().decrypt_region(args.host)
        if materials["bundled"] is None:
            print(f"NOTE: no bundled certificate for {args.host}; skipping that variant.",
                  file=sys.stderr)
            variants = [v for v in variants if v != "bundled"]
    if "selfsigned" in variants:
        materials["selfsigned"] = make_selfsigned()

    runs, matrix = [], {}
    for port in ports:
        matrix[port] = {}
        for variant in variants:
            attempts = [probe_once(args.host, port, materials[variant])
                        for _ in range(args.repeat)]
            label = collapse(attempts)
            matrix[port][variant] = label
            runs.append({"port": port, "variant": variant, "label": label,
                         "attempts": attempts})
            # A port that will not even accept TCP will not accept it for the other
            # variants either: skip them instead of burning three timeouts each.
            if variant == "none" and label == "tcp_failed":
                break

    foreign = {}
    for run in runs:
        if run["variant"] != "none":
            continue
        if serves_this_host(run, args.host) is False:
            cert = run["attempts"][0].get("server_cert") or {}
            foreign[run["port"]] = cert.get("san") or cert.get("subject")

    result = {"host": args.host, "resolves_to": len(addresses),
              "repeat": args.repeat, "matrix": matrix, "foreign_services": foreign,
              "verdict": verdict(matrix, foreign), "runs": runs}

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    print(f"Host: {args.host}  ({len(addresses)} address(es), {args.repeat} attempts each)")
    print()
    print(f"{'port':<6} {'variant':<12} {'outcome':<34} {'TLS':<9} cipher")
    print("-" * 92)
    for run in runs:
        first = run["attempts"][0]
        print(f"{run['port']:<6} {run['variant']:<12} {run['label']:<34} "
              f"{first.get('tls_version') or '-':<9} {first.get('cipher') or '-'}")
    print()
    seen = set()
    for run in runs:
        sc = (run["attempts"][0].get("server_cert") or {})
        if not sc.get("subject") or run["port"] in seen:
            continue
        seen.add(run["port"])
        print(f"Server certificate on port {run['port']}:")
        print(f"  subject {sc['subject']}")
        print(f"  issuer  {sc['issuer']}")
        print(f"  SAN     {sc.get('san') or 'absent'}")
        print()
    for line in result["verdict"]:
        print(f"* {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
