#!/usr/bin/env python3
"""Step 1 — offline X.509 inspection of the bundled mutual-TLS material.

The question this step answers: is the client certificate shipped in
`custom_components/omoda9/certs/store.json` a *per-device* identity, or a
constant shared by every user of a region?

Reading key (from the investigation brief):

  * generic CN/SAN (app name, region, `client`)  -> not a per-device identity;
  * CN/SAN carrying a device id, VIN or tUserId  -> an enrollment exists;
  * multi-year validity                          -> static material;
  * different serials but identical CN structure -> one identity per region.

Nothing is written to disk: the bundle is de-obfuscated in memory and only
metadata is printed. Private key bytes never leave this process.

Usage:
    python3 tools/enrollment_probe/step1_cert_inspect.py [--json] [--store PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKAGE = os.path.join(REPO, "custom_components", "omoda9")

# Extensions we consider "standard furniture" for a TLS client certificate.
# Anything outside this set is reported verbatim: a vendor-specific OID carrying
# a device identifier is exactly the kind of thing that would prove enrollment.
WELL_KNOWN_OIDS = {
    "2.5.29.14",  # subjectKeyIdentifier
    "2.5.29.15",  # keyUsage
    "2.5.29.17",  # subjectAltName
    "2.5.29.19",  # basicConstraints
    "2.5.29.31",  # cRLDistributionPoints
    "2.5.29.32",  # certificatePolicies
    "2.5.29.35",  # authorityKeyIdentifier
    "2.5.29.37",  # extendedKeyUsage
    "1.3.6.1.5.5.7.1.1",  # authorityInfoAccess
}


def load_cert_bundle():
    """Import `cert_bundle.py` by path, without importing the HA package."""
    path = os.path.join(PACKAGE, "cert_bundle.py")
    spec = importlib.util.spec_from_file_location("_cert_bundle", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def key_usage(cert: x509.Certificate) -> list[str]:
    try:
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
    except x509.ExtensionNotFound:
        return []
    names = [
        "digital_signature", "content_commitment", "key_encipherment",
        "data_encipherment", "key_agreement", "key_cert_sign", "crl_sign",
    ]
    out = [n for n in names if getattr(ku, n, False)]
    if ku.key_agreement:  # encipher/decipher_only only defined when key_agreement is set
        for n in ("encipher_only", "decipher_only"):
            if getattr(ku, n, False):
                out.append(n)
    return out


def extended_key_usage(cert: x509.Certificate) -> list[str]:
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    except x509.ExtensionNotFound:
        return []
    return [getattr(oid, "_name", None) or oid.dotted_string for oid in eku]


def subject_alt_names(cert: x509.Certificate) -> list[str]:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return []
    out = []
    for name in san:
        out.append(f"{type(name).__name__}:{getattr(name, 'value', name)}")
    return out


def unusual_extensions(cert: x509.Certificate) -> list[str]:
    out = []
    for ext in cert.extensions:
        dotted = ext.oid.dotted_string
        if dotted in WELL_KNOWN_OIDS:
            continue
        label = getattr(ext.oid, "_name", None) or "unknown"
        out.append(f"{dotted} ({label})")
    return out


def public_key_info(cert: x509.Certificate) -> tuple[str, str]:
    """(description, SHA-256 fingerprint of the SubjectPublicKeyInfo).

    The SPKI digest is a hash of *public* material and is the cheapest way to say
    whether two regions ship the same identity or two different ones.
    """
    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        desc = f"RSA-{pub.key_size}"
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        desc = f"EC-{pub.curve.name}"
    else:
        desc = type(pub).__name__
    spki = pub.public_bytes(serialization.Encoding.DER,
                            serialization.PublicFormat.SubjectPublicKeyInfo)
    return desc, hashlib.sha256(spki).hexdigest()


def key_matches_cert(key_pem: bytes, cert: x509.Certificate) -> bool | None:
    """True if `client.key` is the private half of `client.pem`'s public key."""
    try:
        key = serialization.load_pem_private_key(key_pem, password=None)
    except Exception:
        return None
    a = key.public_key().public_bytes(serialization.Encoding.DER,
                                      serialization.PublicFormat.SubjectPublicKeyInfo)
    b = cert.public_key().public_bytes(serialization.Encoding.DER,
                                       serialization.PublicFormat.SubjectPublicKeyInfo)
    return a == b


def looks_per_device(cert: x509.Certificate) -> list[str]:
    """Heuristic flags for identifiers that would only exist per device."""
    haystack = [cert.subject.rfc4514_string(), *subject_alt_names(cert)]
    flags = []
    for text in haystack:
        for token in text.replace("=", " ").replace(",", " ").replace(":", " ").split():
            if len(token) == 17 and token.isalnum() and any(c.isdigit() for c in token):
                flags.append(f"VIN-shaped token ({len(token)} chars)")
            elif len(token) >= 24 and token.isalnum():
                flags.append(f"opaque id-shaped token ({len(token)} chars)")
    return sorted(set(flags))


def inspect_region(host: str, blobs: dict[str, bytes]) -> dict:
    cert = x509.load_pem_x509_certificate(blobs["client.pem"])
    ca = x509.load_pem_x509_certificate(blobs["ca.pem"])
    not_before = cert.not_valid_before_utc.replace(tzinfo=timezone.utc)
    not_after = cert.not_valid_after_utc.replace(tzinfo=timezone.utc)
    key_desc, spki = public_key_info(cert)
    return {
        "host": host,
        "subject": cert.subject.rfc4514_string(),
        "subject_cn": next((a.value for a in cert.subject
                            if a.oid == x509.NameOID.COMMON_NAME), None),
        "san": subject_alt_names(cert),
        "issuer": cert.issuer.rfc4514_string(),
        "issuer_cn": next((a.value for a in cert.issuer
                           if a.oid == x509.NameOID.COMMON_NAME), None),
        "serial_hex": format(cert.serial_number, "x"),
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "validity_days": (not_after - not_before).days,
        "signature_algorithm": cert.signature_algorithm_oid._name,
        "public_key": key_desc,
        "spki_sha256": spki,
        "key_usage": key_usage(cert),
        "extended_key_usage": extended_key_usage(cert),
        "unusual_extensions": unusual_extensions(cert),
        "per_device_markers": looks_per_device(cert),
        "key_matches_cert": key_matches_cert(blobs["client.key"], cert),
        "ca_subject": ca.subject.rfc4514_string(),
        "ca_fingerprint_sha256": ca.fingerprint(hashes.SHA256()).hex(),
        "cert_fingerprint_sha256": cert.fingerprint(hashes.SHA256()).hex(),
    }


def summarise(rows: list[dict]) -> dict:
    def distinct(field):
        return sorted({json.dumps(r[field], sort_keys=True) for r in rows})

    return {
        "regions": len(rows),
        "distinct_subjects": len(distinct("subject")),
        "distinct_serials": len(distinct("serial_hex")),
        "distinct_spki": len(distinct("spki_sha256")),
        "distinct_issuers": len(distinct("issuer")),
        "distinct_ca_fingerprints": len(distinct("ca_fingerprint_sha256")),
        "subjects": [json.loads(s) for s in distinct("subject")],
        "issuers": [json.loads(s) for s in distinct("issuer")],
        "validity_days_min": min(r["validity_days"] for r in rows),
        "validity_days_max": max(r["validity_days"] for r in rows),
        "regions_with_per_device_markers": [r["host"] for r in rows
                                            if r["per_device_markers"]],
        "regions_with_san": [r["host"] for r in rows if r["san"]],
        "regions_where_key_matches": sum(1 for r in rows if r["key_matches_cert"] is True),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    bundle = load_cert_bundle()
    hosts = bundle.available_regions()
    if not hosts:
        print("FAILED: no regions in the bundle store.", file=sys.stderr)
        return 2

    rows, failed = [], []
    for host in hosts:
        blobs = bundle.decrypt_region(host)
        if not blobs:
            failed.append(host)
            continue
        try:
            rows.append(inspect_region(host, blobs))
        except Exception as err:  # noqa: BLE001 — a broken region is a result, not a crash
            failed.append(f"{host}: {type(err).__name__}: {err}")

    if not rows:
        print("FAILED: no region could be parsed.", file=sys.stderr)
        return 2

    result = {"summary": summarise(rows), "failed": failed, "regions": rows}
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    s = result["summary"]
    print(f"Regions in bundle: {s['regions']}   (unparseable: {len(failed)})")
    print()
    print(f"{'host':<52} {'CN':<10} {'serial':<20} {'days':>5} {'SPKI sha256':<16} key?")
    print("-" * 118)
    for r in sorted(rows, key=lambda r: r["host"]):
        print(f"{r['host']:<52} {str(r['subject_cn']):<10} {r['serial_hex']:<20} "
              f"{r['validity_days']:>5} {r['spki_sha256'][:16]:<16} "
              f"{'yes' if r['key_matches_cert'] else 'NO'}")
    print()
    print("Cross-region comparison")
    print(f"  distinct subjects .......... {s['distinct_subjects']}   {s['subjects']}")
    print(f"  distinct issuers ........... {s['distinct_issuers']}   {s['issuers']}")
    print(f"  distinct serials ........... {s['distinct_serials']}")
    print(f"  distinct public keys (SPKI)  {s['distinct_spki']}")
    print(f"  distinct CA certificates ... {s['distinct_ca_fingerprints']}")
    print(f"  validity span (days) ....... {s['validity_days_min']} .. {s['validity_days_max']}")
    print(f"  regions with a SAN ......... {len(s['regions_with_san'])}")
    print(f"  private key matches cert ... {s['regions_where_key_matches']}/{s['regions']}")
    print(f"  per-device markers in CN/SAN {s['regions_with_per_device_markers'] or 'none'}")
    print()
    sample = rows[0]
    print(f"Sample region: {sample['host']}")
    print(f"  subject ................ {sample['subject']}")
    print(f"  issuer ................. {sample['issuer']}")
    print(f"  SAN .................... {sample['san'] or 'absent'}")
    print(f"  validity ............... {sample['not_before']} .. {sample['not_after']}")
    print(f"  signature algorithm .... {sample['signature_algorithm']}")
    print(f"  public key ............. {sample['public_key']}")
    print(f"  key usage .............. {sample['key_usage'] or 'absent'}")
    print(f"  extended key usage ..... {sample['extended_key_usage'] or 'absent'}")
    print(f"  non-standard extensions  {sample['unusual_extensions'] or 'none'}")
    print(f"  CA subject ............. {sample['ca_subject']}")
    if failed:
        print()
        print("Unparseable regions:")
        for f in failed:
            print(f"  {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
