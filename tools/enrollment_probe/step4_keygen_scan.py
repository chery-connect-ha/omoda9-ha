#!/usr/bin/env python3
"""Step 4 — is there any client-side key or CSR generation, anywhere?

An enrollment based on a certificate signing request has a signature you cannot
hide: something, somewhere, has to generate a key pair and build a PKCS#10
request. This step looks for that signature across the codebase and across any
reverse-engineering notes handed to it with `--extra`.

A total absence is not a weak result. If nothing in the material generates a key
pair, then no CSR-based enrollment was ever observed in the app, and one cannot be
implemented by replaying what we know.

Read-only: it opens files and counts matches. Nothing is written and no network
is touched.

Usage:
    python3 tools/enrollment_probe/step4_keygen_scan.py [--extra DIR ...] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

PATTERNS = {
    "java_keypair": r"KeyPairGenerator|generateKeyPair|getInstance\(\s*[\"']RSA[\"']",
    "pkcs10_csr": r"PKCS\s*#?10|CertificationRequest|CertificateSigningRequest|"
                  r"createCertificateRequest|\bCSR\b|csr[_A-Z]",
    "bouncy_castle": r"bouncycastle|spongycastle|BouncyCastleProvider|\bBKS\b",
    "keystore_build": r"KeyStore\.getInstance|keytool|\.jks\b|\.p12\b|\.pfx\b|"
                      r"setKeyEntry|load_pkcs12",
    "python_keygen": r"generate_private_key|CertificateSigningRequestBuilder|"
                     r"CertificateBuilder|rsa\.generate|ec\.generate_private_key",
    "openssl_cli": r"openssl\s+(req|genrsa|genpkey|x509|pkcs12)",
    "enrollment_words": r"\benroll(ment)?\b|dynamic\s*regist|deviceSecret|productKey|"
                        r"\bdeviceName\b|iotId",
}

TEXT_SUFFIXES = (".py", ".md", ".js", ".ts", ".json", ".yaml", ".yml", ".txt",
                 ".java", ".kt", ".dart", ".smali", ".xml", ".sh", ".toml", ".cfg")
# `store.json` is the obfuscated certificate bundle: megabytes of base64 that match
# nothing meaningful and drown the output. The other two exclusions are this
# investigation's own output — `step2_tls_probe.py` genuinely generates a key pair,
# and `enrollment-findings.md` names every pattern below while reporting that none
# of them was found. Scanning either would manufacture the very evidence we are
# looking for: the first run of this script, before the report existed, found one
# match; with the report in the tree it found fourteen, all of them our own prose.
SKIP_PARTS = (os.sep + ".git" + os.sep, os.sep + "__pycache__" + os.sep,
              os.sep + "node_modules" + os.sep, os.sep + ".pytest_cache" + os.sep,
              os.sep + "certs" + os.sep + "store.json",
              os.sep + "tools" + os.sep + "enrollment_probe" + os.sep,
              os.sep + "docs" + os.sep + "enrollment-findings.md")
MAX_BYTES = 4_000_000


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "__pycache__", "node_modules", ".pytest_cache")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            if any(part in path for part in SKIP_PARTS):
                continue
            if not path.endswith(TEXT_SUFFIXES):
                continue
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield path


def scan_root(root: str, compiled: dict[str, re.Pattern]) -> tuple[dict, int]:
    hits: dict[str, list[str]] = {name: [] for name in compiled}
    files = 0
    for path in walk(root):
        files += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    for name, rx in compiled.items():
                        if rx.search(line):
                            rel = os.path.relpath(path, root)
                            hits[name].append(f"{rel}:{lineno}: {line.strip()[:120]}")
        except OSError:
            continue
    return hits, files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extra", action="append", default=[],
                    help="additional directory to scan (reverse-engineering notes)")
    ap.add_argument("--max-shown", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    compiled = {name: re.compile(rx, re.IGNORECASE) for name, rx in PATTERNS.items()}
    roots = [REPO] + [os.path.abspath(p) for p in args.extra]

    report = {"roots": [], "totals": {name: 0 for name in PATTERNS}}
    for root in roots:
        if not os.path.isdir(root):
            report["roots"].append({"root": root, "error": "not a directory"})
            continue
        hits, files = scan_root(root, compiled)
        for name, lines in hits.items():
            report["totals"][name] += len(lines)
        report["roots"].append({"root": root, "files_scanned": files,
                                "hits": {n: len(v) for n, v in hits.items()},
                                "samples": {n: v[:args.max_shown]
                                            for n, v in hits.items() if v}})

    generating = ("java_keypair", "pkcs10_csr", "bouncy_castle", "keystore_build",
                  "python_keygen", "openssl_cli")
    total_generating = sum(report["totals"][n] for n in generating)
    report["verdict"] = (
        "No key-pair or CSR generation anywhere in the scanned material: a CSR-based "
        "enrollment cannot exist here, and none was ever observed in the app."
        if total_generating == 0 else
        f"{total_generating} match(es) for key or CSR generation — inspect the samples "
        f"before concluding anything.")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    for entry in report["roots"]:
        if entry.get("error"):
            print(f"{entry['root']}: {entry['error']}")
            continue
        print(f"{entry['root']}  ({entry['files_scanned']} text files)")
        for name in PATTERNS:
            count = entry["hits"][name]
            print(f"  {name:<20} {count}")
            for sample in entry.get("samples", {}).get(name, []):
                print(f"      {sample}")
        print()
    print(report["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
