# Does the MQTT stack support a per-device enrollment?

**Measured on 2026-08-25**, against the EU region
(`tspemqx-app-eu.cheryinternational.com`), with the probes in
[`tools/enrollment_probe/`](../tools/enrollment_probe/). Every number below can be
re-produced by re-running them; where a step could not be run, it says so instead
of guessing.

## Why this was asked

`custom_components/omoda9/certs/store.json` carries mutual-TLS material — `ca.pem`,
`client.pem`, `client.key` — for 40 regional brokers. It comes from the public
assets of the official APK, and it is the same for every user of a region. That
means this repository redistributes a **vendor private key**. The goal is to stop
doing that.

The hypothesis worth falsifying was that this material is only *bootstrap*: that
somewhere in the `getTuserId → loginTSP` chain the app trades it for a per-device
identity — a locally generated key plus a CSR, or a dynamic registration. If such
an enrollment exists, every user can obtain their own material and the bundle can
go without losing anything.

## Verdict

**The enrollment does not exist, and the certificate cannot simply be dropped
either.** Both halves matter, and the second one contradicts the outcome the
investigation was hoping for:

* the bundled certificate is a per-region constant, not a per-device identity
  (step 1);
* the broker **does** require a client certificate, and it checks who signed it: a
  self-signed certificate generated locally is refused (step 2);
* nothing in the provisioning responses looks like credential material — no
  certificate, no CSR, no `productKey`/`deviceName`/`deviceSecret` (step 3);
* nothing anywhere generates a key pair or a CSR (step 4).

So the bundle cannot be removed without a replacement, and there is no
replacement to be had from the vendor. What remains is a distribution question,
not a protocol one — see [What is actually left](#what-is-actually-left).

## Step 1 — what the certificate actually is

`python3 tools/enrollment_probe/step1_cert_inspect.py`

40 regions, all 40 parsed, all 40 with a private key that matches its certificate.

| property | value |
|---|---|
| subject | `CN=client, O=EMQX, L=ShangHai, ST=SH, C=CN` — **identical in all 40 regions** |
| SAN | absent in all 40 |
| key usage / extended key usage | absent in all 40 |
| non-standard extensions | none in all 40 |
| public key | RSA-2048, `sha256WithRSAEncryption` |
| validity | 3650 days (10 years) in all 40, issued between 2023 and 2026 |
| distinct serials | 40 |
| distinct public keys | 40 |
| distinct issuing CAs | 40 |
| per-device markers in CN/SAN | none |

The EU certificate this integration uses:

```
subject     CN=client,O=EMQX,L=ShangHai,ST=SH,C=CN
issuer      CN=tspemqx-app-eu.cheryinternational.com,OU=EMQX,O=EMQX,L=ShangHai,ST=SH,C=CN
            (emailAddress=…@mychery.com)
serial      1c7a383f7ac05df7278cd5d16d504bfa88ab7f8b
validity    2023-10-26 .. 2033-10-23   (3650 days)
```

Read against the criteria set for this step: the CN is the generic literal
`client`, there is no SAN at all, and the validity is a decade. Different serials
and different keys across regions, with an identical subject structure and an
issuer that is the region's own self-signed CA, means **one identity per region**
— not one per device, and not one per account. Nothing in the certificate carries
a device id, a VIN or a `tUserId`.

This confirms what `cert_bundle.py` already documents. It does not by itself say
whether the certificate is *needed*.

## Step 2 — does the broker require it?

`python3 tools/enrollment_probe/step2_tls_probe.py --repeat 3`

Three variants per port — no client certificate, the bundled one, and a
throw-away self-signed one generated on the spot — three attempts each,
consistent across all three.

| port | no certificate | bundled certificate | self-signed certificate |
|---|---|---|---|
| 8083 (the port the integration dials) | handshake OK, **server closes immediately** | handshake OK, **connection held open** | handshake OK, **server closes immediately** |
| 8883 | TCP timeout | — | — |
| 8884 | TCP timeout | — | — |
| 1883 | TCP timeout | — | — |
| 443 | a different service answers (see below) | — | — |

**The trap this step was designed to avoid.** Under TLS 1.3 the handshake
completes on the client side before the server has judged the certificate it did
or did not receive. Reading only "handshake_ok" on port 8083 would have produced
exactly the conclusion the decision table's first row describes — *remove the
bundle, no replacement needed* — and it would have been wrong. What separates
acceptance from rejection is what happens next, and the probe waits for it: with
the bundled certificate the listener holds the connection open waiting for an MQTT
CONNECT; without one, and with a self-signed one, it sends a clean EOF within
milliseconds. That is EMQX with `verify_peer` and `fail_if_no_peer_cert`. The
alert 116 `certificate_required` this step went looking for never appears — the
server does not bother to send it — so its absence is not evidence of anything.

**The self-signed variant is the important one.** The broker does not merely want
*a* certificate; it wants one that chains to the region CA. A user cannot generate
accepted material locally.

**Which stack this is.** The certificate served on 8083 is
`CN=CA, O=EMQX, …`, issued by the region's own CA, with the broker hostname in its
SAN. It is a self-hosted EMQX. It is **not** Aliyun IoT Platform — nothing
resembling `*.iot-as-mqtt.<region>.aliyuncs.com` appears. This falsifies the
priority hypothesis of this investigation: there is no Aliyun dynamic
registration here, because there is no Aliyun.

Port 443 on the same address answers with a certificate for
`tspterminal-eu.cheryinternational.com`, issued by `Chery CA` — a different
service sharing the address. It accepts connections without a client certificate,
which says nothing whatsoever about the broker's policy. The probe labels it as
such rather than counting it as a result.

## Step 3 — is credential material in the provisioning responses?

`python3 tools/enrollment_probe/step3_response_scan.py`

The session was reused as required: existing token, no refresh, no OTP. The stored
access token was 23 648 s into its 43 200 s lifetime and the BFF login succeeded,
so this step ran in full.

Three read-only responses were captured and scanned recursively for base64 DER
(`MII…`), base64 PEM (`LS0tLS1CRUdJTi`), literal PEM headers, strings longer than
200 characters, and the marker key names.

| endpoint | HTTP | code | distinct keys | hits |
|---|---|---|---|---|
| `auth/login` | 200 | 0 | 9 | 1 — `$.data.userToken`, a 217-character opaque string |
| `auth/getTuserId` | 200 | 0 | 8 | none |
| `vmc/queryList` | 200 | 0 | 39 | none |

The single hit is the session token the integration already uses; it is long, not
cryptographic material, and its value is redacted in the probe's output.

Because an absence is only a finding if you can show what was there instead, the
probe enumerates every key name it saw. `queryList` — by far the richest response
— returns:

```
airConditionerType, authorizeEndTime, authorizeStartTime, authorizeTime,
authorizeType, carNumber, carPicture, code, colorCode, colorName, colorNameEn,
data, defCar, engineNumber, fullName, hiValue, iccid, isHaveLoAndHi, key,
loValue, maxAirDuration, maxEngineDuration, maxTemperature, minTemperature, msg,
nickname, ok, passwordType, powerType, promotionalCardUrl, remarks,
skylightType, steeringWheelPosition, tboxSn, temperatureStepLength, txId,
typeCode, vehicleType, vin
```

None of `cert`, `pem`, `csr`, `p12`, `keystore`, `productKey`, `deviceName`,
`deviceSecret`, `iotId`, `clientId`, `mqttUsername`, `mqttPassword` appears in any
of the three responses. `iccid` and `tboxSn` are device *identifiers*, not
credentials, and are returned alongside the paint colour and the sunroof type.

**`loginTSP` could not be executed, and this is a result, not a gap.** The brief
assumed the `getTuserId → loginTSP` chain was implemented in `core/provision.py`.
It is not: the module implements `getTuserId → queryList`, and its own docstring
records that the app's `getTspToken()`/`loginTSP` is a **native** call, a no-op in
the DEX. There is no request to replay and no observed traffic to imitate, so
there was nothing to run. Guessing endpoint names was ruled out: an invented
result would be worse than a missing one. `README.md` already states the same
thing — the car_token chain exists only in the experimental module and is unused
at runtime.

## Step 4 — does anything generate a key pair?

`python3 tools/enrollment_probe/step4_keygen_scan.py --extra ../.coding_agent --extra ../security-disclosure`

166 text files across the repository, the agent's working notes and the security
disclosure material.

| pattern | hits |
|---|---|
| `KeyPairGenerator` / `generateKeyPair` | 0 |
| PKCS#10 / `CertificateSigningRequest` / CSR | 0 |
| Bouncy Castle / Spongy Castle / BKS | 0 |
| keystore construction / keytool / `.jks` / `.p12` | 1 — false positive |
| `generate_private_key` / `CertificateBuilder` | 0 |
| `openssl req` / `genrsa` / `genpkey` | 0 |
| enrollment / dynamic registration vocabulary | 0 |

The single match is `tests/test_repo_hygiene.py:47`, the list of file extensions
the repository refuses to track — `".key", ".pem", ".cer", ".p12", ".pfx"`. It is
a guard against committing key material, not code that produces any.

The probe skips its own directory and this report. `step2_tls_probe.py` genuinely
does generate a key pair for its self-signed variant, and this file names every
pattern in the table while reporting that none was found: counting either would be
manufacturing the evidence. The effect is not hypothetical — run against a tree
containing this report, the scan returns fourteen matches, all of them these
paragraphs.

**Nothing generates a key pair.** A CSR-based enrollment therefore cannot exist in
this codebase, and none was ever observed in the app.

## Conclusion against the decision table

| criterion | result |
|---|---|
| Handshake without a certificate succeeds (step 2) → *remove the bundle, no replacement* | **No.** The handshake completes but the broker drops the connection. The certificate is required. |
| `productKey`/`deviceSecret`/CSR in the responses (step 3) → *implement enrollment* | **No.** Nothing of the kind in any of the three responses. |
| No client-side key pair and no endpoint (steps 3–4) → *enrollment does not exist: BYO or drop the MQTT path* | **Yes.** This is the row that applies. |

With one correction to what that third row implies. "BYO" cannot mean *the user
generates their own key*: step 2 shows the broker rejects material it did not
sign. It can only mean *the user supplies the same vendor material themselves*,
extracting it from the APK asset on a device they own.

## What is actually left

Three options, and none of them is free:

1. **Keep the bundle.** Function is preserved; the vendor private key stays
   redistributed in a public repository. This is the status quo.
2. **Ship the code, not the material.** Keep the de-obfuscation in
   `cert_bundle.py`, drop `store.json`, and have the user point the integration at
   the asset from their own copy of the APK. Nothing is lost functionally; the
   setup gains a manual step, and the repository stops carrying the key.
3. **Drop the MQTT path.** Push telemetry goes away and everything falls back to
   REST polling. This is a real loss of function, for a real simplification.

Option 2 is the only one that resolves the original problem without giving
anything up, and it is a change to the config flow and the packaging — not to the
protocol. Choosing between them is out of scope here.

## What this does and does not change about safety

The certificate admits a client to the transport and nothing more. Account
isolation is elsewhere and was already documented: the MQTT username is the
`tUserId`, the password is `md5(tUserId + seed)`, and the topic ACL is
`app/<channel>/<tUserId>/…` (`coordinator.py:721-731`). Holding the shared
certificate does not let anyone read another account's messages.

So removing the bundle is about **not redistributing someone else's private key**
— a licensing and key-hygiene problem, and the vendor's exposure — not about
protecting users of this integration from each other. Worth being precise about,
because the two arguments justify different levels of urgency.

## An observation outside this scope

`coordinator.py:735` calls `tls_insecure_set(True)`, with the comment that the
broker presents a non-matching CN. Measured today, that is no longer true: a
handshake with full verification — the bundled `ca.pem` as trust anchor,
`check_hostname` on, `CERT_REQUIRED` — succeeds against port 8083 and the
connection is held open. The server certificate's CN is indeed `CA`, but its SAN
carries the broker hostname, which is what a modern TLS stack checks.

Recorded here because it was measured here. It is a separate change, with its own
field test, and it is not part of this work.

## Limits of this report

* One region was probed on the network: the EU broker this account uses. Step 1
  covers all 40; steps 2 and 3 speak for the EU region only.
* Ports 8883, 8884 and 1883 timed out at TCP level. Timeout is not a closed port:
  a firewall on the path would look the same. No conclusion is drawn from them.
* Step 3 saw the responses this account receives. A different `authorizeType`, a
  different region or a vehicle with different options could return more fields.
* No command, no `taskId`, no PIN and no OTP were used at any point, by design.
  Anything only observable while sending a command was therefore not observed.
