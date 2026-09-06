# Domain model

This document defines **what** the integration talks about, before any decision
about how the code is arranged. It is the single source of truth for the domain:
the code implements it, it is not an alternative description of it. The layer
layout that implements this model lives in [`architecture.md`](architecture.md).

It is written for a codebase that already exists and already runs on other
people's cars. Where today's code contradicts the model, that is recorded
honestly in [Known gaps](#known-gaps) rather than quietly smoothed over — a
documented gap is a work item, an undocumented one is a bug waiting to be
rediscovered.

## Why this model looks the way it does

Three findings from the field shaped it, and they are worth stating up front
because they explain choices that would otherwise look arbitrary.

The first is that **the vehicle is not the unit of variation**. Two cars of the
same model, on the same firmware, do not necessarily accept the same commands,
and the same car does not necessarily accept the same command twice: a comfort
macro that succeeded four times in one day started being refused later the same
evening. Anything the model says about "what a car can do" is therefore a
statement about *what the backend declared, when we last asked* — never a
property baked into a type.

The second is that **the brand is not the unit of variation either**. Servers,
MQTT brokers and certificates all live on one platform; the pieces that actually
differ between deployments are the authentication front door and a handful of
host/tenant values. A car's badge is presentation.

The third is that **acceptance is not execution**. The backend answering "issued
successfully" and the car actually doing the thing are two different events,
arriving over two different channels, and a domain that collapses them lies to
the user.

## Glossary — ubiquitous language

These names are the same in this document, in the code, and in the user-facing
strings. No layer renames a concept on the way through.

| Term | Meaning | Not to be used as a synonym |
|---|---|---|
| **Vehicle** | One car bound to one account, the aggregate root of everything we know about it | "device" (that is a Home Assistant object), "car id" |
| **VIN** | The vehicle's identity, everywhere and always | "vehicle number", "chassis" |
| **Platform** | The auth + signing + transport front door of a telematics stack (e.g. the OMODA/Jaecoo *legend* gateway, the Chery-branded BFF/UAA stack, CarLinko). Determines *how* we authenticate and speak | "brand", "region" |
| **Region** | One deployment of a platform: BFF host, tenant, certificate bundle. Data, not behaviour | "country", "market" |
| **Brand** | Marketing identity: display name, logo, imagery. Presentation only, never behaviour | "platform", "model" |
| **Model** | What the car calls itself. Used for display and for the compatibility matrix — never as a branching condition in code | "variant", "trim" |
| **Capability** | Something a *specific* vehicle declared it can do or accept, as reported by the backend at a point in time | "feature", "option" |
| **Command** | An intent addressed to a vehicle (lock, climate on, seat heating…) | "action", "service call" |
| **Command catalog** | The single shared set of commands the platform exposes; vehicles differ by which ones they accept, not by which exist | — |
| **TaskId** | Short-lived control credential minted by `checkPassword`, scoped to a session and **not** to a command category | "token" (that is a login credential) |
| **Control PIN** | The 4-digit code that signs commands. It is **not** a login credential | "password", "PIN di accesso" |
| **Backend acceptance** | The synchronous answer to the HTTP call (`A00079` accepted, `A00084` denied…) | "result", "confirmation" |
| **Vehicle acknowledgement** | The asynchronous confirmation the car later publishes over MQTT, carrying `result` and an optional `reason` list | "response", "ack HTTP" |
| **Telemetry frame** | One coherent set of vehicle readings as published by the car | "update", "poll" |
| **Placeholder frame** | A frame whose fields are structurally impossible (high-voltage readings at `0`/`-1000`, an odometer that went backwards). Carries no information and must never be treated as a reading | "stale data", "glitch" |
| **Charge session** | One continuous period during which the vehicle reports charging | "charge", "cycle" |
| **Zone** | Whether the vehicle is at the user's home location or away. Decides how charged energy is attributed | "location" (that is a coordinate) |
| **Poll cycle** | Periodic sampling of the vehicle, gated by the user-facing *Auto Update* switch | "refresh" |
| **Settle** | The minimum quiet interval enforced after a command, before another may be sent | "delay", "timeout" |

## Entities and aggregates

### `Vehicle` — aggregate root

- **Identity:** the VIN. Everything else about a vehicle, including its name, is
  mutable decoration.
- **Attributes:** identity (name, model, brand), a `CapabilitySet`, the last known
  `TelemetrySnapshot`, the current `ChargeSession` if any, current `Zone`.
- **Aggregate boundary:** capabilities, telemetry and charge sessions have no
  meaning outside a vehicle and are only reachable through it. Commands are
  addressed *to* a vehicle but have their own lifecycle (see below).
- **Invariants:**
  - **The odometer never decreases.** A frame reporting a lower odometer than the
    last known value is a placeholder frame, not a reading.
  - **A placeholder frame never overwrites a good value.** The previous reading
    survives; the entity reports its last known state rather than a fiction.
  - **Identity is never silently overwritten.** A probe performed to learn
    capabilities must not rewrite a name the user chose, or one already cached.
  - **State of charge does not fall during a charge session.** A drop back to the
    session's starting value at charge completion is a placeholder frame.

### `CapabilitySet` — what this vehicle declared, and when

- **Identity:** none of its own; it belongs to its `Vehicle`.
- **Attributes:** the declared values (power type, climate temperature range, …),
  plus a marker recording that a probe has actually happened.
- **Invariants:**
  - **Absence is not negation.** A capability the backend did not declare is
    *unknown*, and unknown must fall back to the historical behaviour. Suppressing
    a feature requires a positive declaration: fuel sensors disappear only for a
    *confirmed* battery-electric vehicle, never for an undeclared one.
  - **Implausible declarations are discarded, not adopted.** A climate range
    outside human plausibility is bad data, not an exotic car; the defaults hold.
  - **"Never asked" is distinguishable from "asked, backend said nothing".**
    Without that distinction a silent backend causes an identical probe on every
    restart.
  - **Capabilities may change over time** and must be re-probeable. They are a
    cache with a reason to expire, not a constant.

### `Command` — an intent with two answers

- **Identity:** the request sequence (VIN + timestamp) together with the `TaskId`
  under which it was issued.
- **Attributes:** the catalog entry, its parameters, the backend acceptance, and
  — when it arrives — the vehicle acknowledgement.
- **Invariants:**
  - **At most one command is in flight per vehicle.** This is not an
    implementation detail of our client: the backend enforces it and rejects the
    second one. Serialisation plus a settle interval is therefore part of the
    domain, not an optimisation.
  - **Acceptance is not execution.** A command with backend acceptance and no
    vehicle acknowledgement has not been carried out, and must not be reported as
    success.
  - **A retryable rejection is retried before the user sees it.** "Another
    instruction is being issued" is a transient collision, not a failure; only a
    terminal outcome reaches the user.
  - **A refused control PIN is never reported as success.**
  - **A `TaskId` is per session, not per command category.** One valid `TaskId`
    drives every category; a category-specific denial is a permission decision by
    the backend, and no re-minting will change it.

### `Access` — the account and its credentials

- **Identity:** the account (login id).
- **Attributes:** login id (email or phone), the OTP channel that was used, the
  issued tokens, the control PIN and its lockout counter.
- **Invariants:**
  - **The OTP channel is stable for a given login.** A login that started as
    email stays email on re-authentication; a phone login carries its number.
  - **The control PIN is not a login credential.** Losing it must never invalidate
    a session; a wrong one must never look like an authentication problem.
  - **After repeated wrong PIN attempts the client refuses locally**, rather than
    letting the backend lock the account out.
  - **Secrets never travel through process arguments.**

### `ChargeSession` — energy, and what we can honestly claim about it

- **Identity:** the vehicle plus the session start.
- **Attributes:** start and end, the zone it took place in, accrued energy.
- **Invariants:**
  - **Energy accrues only while the vehicle reports charging.** Charging power
    read outside that state is noise, not a measurement.
  - **An unobserved interval is recorded as unobserved.** When consecutive samples
    are further apart than the trust threshold, that stretch of the session is
    unaccounted for — the session must carry that fact rather than silently
    reporting a smaller number as if it were complete.
  - **Accrued energy is battery-side, not meter-side.** It is what went into the
    battery, not what the wall socket delivered, and must never be presented as
    the quantity that was paid for.

## Value objects

| Value object | Composition | Constraints |
|---|---|---|
| `Vin` | the 17-character identifier | opaque, never parsed for meaning |
| `Region` | BFF host, tenant, certificate bundle | a region is fully described by data; adding one must never require code |
| `Brand` | display name, logo, imagery | presentation only; no behaviour may branch on it |
| `TemperatureRange` | minimum, maximum, step | minimum < maximum, both within human plausibility; step from the allowed set; an out-of-range declaration is discarded |
| `ResultCode` | the backend code plus its classification: accepted, transient, permission, parameter, session | the classification is the domain's, and every code maps to exactly one class |
| `LoginId` | the identifier plus its channel (email or phone) | the channel is derived from the identifier's form, once, and then carried |
| `Zone` | home or away | derived from position and the configured home location |

## Relations

- `Vehicle` **1 — 1** `CapabilitySet`, `Zone`, latest `TelemetrySnapshot`.
- `Vehicle` **1 — 0..\*** `ChargeSession`; at most one open at a time.
- `Vehicle` **1 — 0..\*** `Command`; at most one in flight at a time.
- `Access` **1 — 1..\*** `Vehicle`; a vehicle is reachable only through its account.
- `Region` **\* — 1** `Platform`; a platform has many regions, a region belongs to one.
- `Brand` is attached to a `Vehicle` for display and has no relation to `Platform`.

## Bounded contexts

Four contexts, each with its own model, meeting at explicit points:

- **Access** — captcha, one-time codes, tokens, control PIN, lockout. Knows
  nothing about vehicles beyond which ones an account may reach.
- **Control** — the command catalog, `TaskId` lifecycle, result classification.
  Owns the "at most one in flight" rule.
- **Telemetry** — frames, placeholder detection, the last-known-good state. Owns
  the odometer and placeholder invariants.
- **Energy** — charge sessions, zone attribution, observability of an interval.
  Consumes Telemetry, never reads the network itself.

**Control and Telemetry meet at the acknowledgement.** A command's outcome is
completed by a frame that arrives through the telemetry channel; that crossing is
the one place where the two models translate into each other, and it is where the
"acceptance is not execution" rule is enforced.

## Known gaps

Where the code does not yet uphold the model. Each is a work item, not a
tolerated exception.

| Invariant | Current behaviour | Consequence observed |
|---|---|---|
| The odometer never decreases | Frames are taken at face value | An odometer went backwards at charge completion; range and state of charge collapsed in the same frame |
| A retryable rejection is retried before the user sees it | Rejections are classified as retryable, but nothing consumes the classification | The transient "another instruction is being issued" reaches the user as a red error |
| An unobserved interval is recorded as unobserved | Intervals beyond the trust threshold are silently skipped | A slow charge was reported as a fraction of the energy actually stored, with nothing indicating the number was partial |
| Capabilities are re-probeable | Probed once, with no expiry path | A vehicle whose declarations change keeps the old ones until reconfigured |

---

*Maintenance: changing an entity or an invariant is a change **to this document**,
not only to the code. An undocumented invariant is a debt.*

## Note — what v1.10.0–v1.13.0 already confirmed

This model was drafted against v1.10.0 and is published against v1.13.0. The work that
landed in between is evidence for it rather than against it, and it is worth recording
which parts are no longer hypothetical:

- **Capabilities are discovered, not declared by model name.** `capabilities_from_item()`
  and `core/permessi.py` decide what a *specific* vehicle accepts from what the backend
  answers for that vehicle — which is the axis this model claims is the real one.
- **Absence is not negation.** `permessi.py` keeps an explicit sentinel for "I tried to
  read the permissions and failed", distinct from "I have not asked yet", and in both
  cases sends the command as before. That is exactly the invariant stated below, already
  implemented.
- **The unit of authorisation is the endpoint, not the feature name.** The tailgate appears
  both as `2032` (denied) and under category `205` (allowed); keying by feature name would
  have produced the wrong answer.

The seam this model asks for is therefore mostly *where these pieces live*, not what they do.
