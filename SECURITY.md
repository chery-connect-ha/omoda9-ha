# Security Policy

## Reporting a vulnerability

Report security issues **privately**. Please do not open a public issue, pull request or
discussion for anything security-sensitive.

- **GitHub → Security → "Report a vulnerability".** Private Vulnerability Reporting is
  enabled on this repository, so the report is visible only to the maintainers until we
  publish an advisory together.
- Include the affected version, what the problem is, how to reproduce it, and what an
  attacker gets out of it. A proposed fix is welcome and never required.
- **Redact your own data before sending.** No real tokens, VINs, GPS coordinates, account
  identifiers or phone numbers — the shape of a value tells us what we need
  (`"vin": "<redacted, 17 chars>"`).

You will get an acknowledgement as soon as one of us sees it. Coordinated disclosure is
welcome: we will agree a timeline for the fix and the public advisory, and credit you by
name unless you would rather stay anonymous.

## Which versions get fixes

This is a community project run by four people, none of whom does it for a living. Security
fixes target the **latest stable release**. Update through HACS before reporting.

Pre-releases exist here (HACS → *Show beta versions*) and are how a change gets tried on a
real car before it lands. They are for testing, not for running on an instance you depend
on — see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Sensitive data: what this integration actually touches

This integration signs in to the Chery-group cloud as you and can send commands to your car,
so it necessarily handles data that matters. What follows is what the code does, not what we
would like it to do.

**Credentials and tokens stay on your own instance.** Account e-mail or phone number, the
four-digit command PIN, access and refresh tokens and `tUserId` live in the Home Assistant
config entry and in files under your HA config directory. Nothing is sent anywhere except
the vehicle backend, and nothing is stored in this repository. Note that Home Assistant
keeps config entries **in plain text** in `.storage/` — that is standard Home Assistant
behaviour and applies to every integration, but it is the real place your credentials sit.

**Diagnostics are safe to attach to a bug report.** The diagnostics download redacts e-mail,
PIN, VIN, `tUserId`, phone number and GPS position, and reports tokens and certificates only
as present or absent, never their contents. The redaction works on values inside free text as
well as on dictionary keys, because some fields are exported verbatim. Skim yours anyway
before posting it in public.

**Logs: what we can and cannot promise.** In normal operation the PIN, OTP codes and tokens
are not written to the log; the most sensitive value that appears at debug level is the VIN.

We deliberately do not state that as an absolute. Sign-in runs in a subprocess whose output is
captured and logged, and an unhandled error there produces a traceback we did not compose — so
what a failure path can carry is a property of the error, not only of our logging. Where we
find such a path we treat it as a security issue in this project and handle it through the
channel above, on the same terms we ask of you.

**The bundled certificates and signing constants are not secrets of yours.** The mutual-TLS
certificates and the app's signing constants are extracted from the publicly distributed
vehicle app and are identical for every user. They are not per-account material, and finding
them in this repository is not a vulnerability.

## Out of scope

- Anything requiring access to your unlocked Home Assistant instance: if someone has that,
  they already have your car.
- The vehicle backend's own behaviour. We can report upstream and sometimes work around it,
  but we do not control it and cannot fix it.
- The plain-text storage of config entries in `.storage/`, which is Home Assistant's design
  and identical for every integration.
- Reports produced by a scanner with no demonstrated impact on a real installation.

## If you find something in the protocol research

Some of this project's reverse-engineering material lives in a private repository shared
between maintainers. If you have access to it and find something sensitive that should not be
there — a real identifier, a live token, a key that is not one of the app's universal
constants — say so through the private channel above rather than in a commit message, and it
will be removed and the history rewritten.
