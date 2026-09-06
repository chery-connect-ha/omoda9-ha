# enrollment probe

Four standalone probes that answer one question: **can each user of this
integration obtain their own MQTT credentials, instead of sharing the vendor
certificate bundled in `custom_components/omoda9/certs/store.json`?**

They exist to be re-run and disagreed with. Every claim in
[`docs/enrollment-findings.md`](../../docs/enrollment-findings.md) comes from one
of them.

They live outside `custom_components/` on purpose: the HACS payload is built from
that directory alone, so nothing here ships to users.

| script | question | network |
|---|---|---|
| `step1_cert_inspect.py` | Is the bundled certificate a per-device identity or a per-region constant? | none |
| `step2_tls_probe.py` | Does the broker actually demand a client certificate, and does it check who signed it? | TLS handshake only |
| `step3_response_scan.py` | Do the provisioning responses carry per-device credential material? | read-only BFF calls |
| `step4_keygen_scan.py` | Does anything, anywhere, generate a key pair or a CSR? | none |

## Safety rules these scripts obey

* **Nothing reaches the car.** No `setVecDefault`, no `checkPassword`, no PIN, no
  `taskId`, no `/asc/vehicleControl/*`. A wrong PIN increments a counter on Chery's
  side and can lock the account, so the PIN is never used at all.
* **No OTP.** `step3` reuses the stored session and, by default, does not even
  refresh it: it works on a copy of the token file so a running Home Assistant
  never has its refresh token rotated underneath it. An expired token stops the
  probe; it never asks for a new code.
* **No MQTT authentication.** `step2` stops at the end of the TLS handshake and
  then waits passively. It never sends a CONNECT.
* **No secrets in the output.** VIN, tokens, e-mail, phone number and coordinates
  are redacted. Values are reported by shape — type, length, an eight-character
  prefix — and even the prefix is suppressed for anything carrying an account
  identifier.
* **Nothing is written to the repository.** The certificate bundle is
  de-obfuscated in memory. When OpenSSL requires a key on disk, it goes to a
  private temporary directory, is overwritten with zeros and removed.

## Running them

```bash
python3 tools/enrollment_probe/step1_cert_inspect.py
python3 tools/enrollment_probe/step2_tls_probe.py --repeat 3
python3 tools/enrollment_probe/step4_keygen_scan.py --extra ../.coding_agent
```

`step3` needs a configured account. It reads the same environment variables
`core/provision.py` already uses:

```bash
export VIN=...                 # your vehicle
export OMODA_TOKEN_PATH=...    # <config>/omoda9_<VIN>_token.json
python3 tools/enrollment_probe/step3_response_scan.py
```

Every script takes `--json` for machine-readable output. The only dependency
beyond the standard library is `cryptography`, which the integration already
requires; `step3` also uses `requests`, for the same reason.
