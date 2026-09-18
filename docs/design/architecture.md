# Architecture — target and route

Where the code is going, why, and how it gets there without a rewrite.
The *what* — the concepts this architecture arranges — is in
[`domain-model.md`](domain-model.md); this document only decides where things
live and which direction dependencies point.

## The decision that shapes everything: the axis of variation

The obvious way to organise a project that wants to support several car brands is
an abstract class per brand and a subclass per model. That would be the wrong
axis here, and the evidence is specific.

**Brands share the machinery.** The servers, the MQTT brokers and the
certificates all live on one platform's infrastructure. Two of the encryption
keys are byte-for-byte identical between the OMODA/Jaecoo app and the
Chery-branded one. A car's badge changes the logo and the marketing name, and
nothing else.

**What genuinely differs is the front door.** There are (at least) three
telematics stacks in this family: the OMODA/Jaecoo *legend* gateway that this
integration speaks, a Chery-branded stack with a different BFF, a separate user
service and a different request-signing scheme, and CarLinko, which is a
different protocol altogether — flat REST and WebSockets instead of MQTT. Within
one stack, moving between deployments has been shown to need nothing but a
different hostname: the same signing secret, the same client identity and the same
tenant were accepted unchanged by a second regional gateway. So the abstraction
that pays for itself sits at **authentication, signing and transport** — not at
the badge.

**And what a car can do is discovered, not declared by its type.** The backend is
asked what the vehicle is and adapts; two cars of the same model can be refused
different commands, and the same car can accept a command in the morning and
refuse it at night. A `class Omoda9` cannot represent a capability that changed at
23:18.

Hence: **platform is the abstraction, region and brand are data, model is a set of
capabilities discovered at runtime.**

## Target layout

```
custom_components/<domain>/
├── platform/          # the abstract seam: how we authenticate, sign, and reach a stack
│   ├── base.py            protocol: log in, refresh, sign, send, subscribe
│   ├── legend.py          OMODA/Jaecoo gateway — the implemented one
│   └── regions.py         host, tenant, certificate bundle: pure data
├── transport/         # the pipes, and nothing else
│   ├── mqtt.py            the broker client, mTLS, subscriptions
│   └── http.py            signed request/response
├── domain/            # the model in domain-model.md, in code. No HA, no network.
│   ├── vehicle.py         identity, telemetry state, invariants
│   ├── capabilities.py    discovery, validation, "unknown is not false"
│   ├── commands.py        catalog, TaskId lifecycle, result classification, retry policy
│   └── access.py          login id, OTP channel, PIN lockout
├── features/          # the services built on the domain
│   ├── energy.py          charge sessions, home/away attribution
│   └── comfort.py         the climate/seats macro
├── brands/            # display name, logo, imagery: data
├── coordinator.py     # orchestration only: schedule, fan out, hold state
└── <platform>.py      # the Home Assistant entity modules
```

Dependencies point one way, and each arrow is enforced by a test (see
[The ratchet](#the-ratchet)):

```
entity modules  →  features/  →  domain/  →  platform/  →  transport/
                        └──────────────────────→ domain/
```

`domain/` imports neither Home Assistant nor the network — that is what makes it
testable in isolation, and it is already true of today's `core/`.

## Where things live today, and where they go

Most of this is **re-seating, not rewriting**. A large part of the target already
exists as well-written modules sitting in the wrong place.

| Today | Goes to | Note |
|---|---|---|
| `coordinator.py` (~1850 lines) | split across `transport/mqtt.py`, `features/`, `domain/`, and a much smaller `coordinator.py` | the only genuinely new seam |
| `core/session.py`, `login_omoda.py`, `omoda_auth.py`, `prova_token.py`, `provision.py`, `captcha_solver.py`, `tsp_sign.py` | `platform/legend.py` | the front door, already isolated from HA |
| `core/tls_client.py` | `transport/http.py` | the client whose TLS fingerprint clears the SMS route |
| `cert_bundle.py`, `certs/store.json` | `platform/regions.py` | already data; make it only data |
| `core/commands.py`, `core/codes.py`, `core/routing.py` | `domain/commands.py` | the catalog and the result classification |
| `capabilities_from_item()` in `const.py` | `domain/capabilities.py` | the seed of the capability model |
| `core/permessi.py` (v1.11.0–v1.13.0) | `domain/capabilities.py` | per-vehicle authorisation: already HA-free, already keyed by endpoint rather than by feature name |
| `core/pin_lockout.py` | `domain/access.py` | already an encapsulated invariant |
| `core/mask.py`, `core/context.py`, `timers.py`, `diag.py` | cross-cutting, stay | infrastructure, not domain |
| the charged-energy integrators inside `coordinator.py` | `features/energy.py` | |
| `brand/` | `brands/` | presentation data |
| `sensor.py`, `switch.py`, `climate.py`, … | unchanged in place | they only lose their one shortcut into `core/` |

## A deliberate deviation, and why

The engineering standard this project follows requires the domain model to be
written **before** the layer code. That rule is written for a project that is
starting; this one is not. It already runs on other people's cars, and a
"model first, then rewrite" reading would mean a big-bang migration with a live
install base as the test group.

The brownfield reading of the same rule, and the one adopted here: **the domain
model is still written first, and it binds all future code**. Existing code
converges on it slice by slice, each slice releasable on its own. What makes this
honest rather than an excuse is that convergence is mechanically enforced —
see below. The gap between model and code is not left to memory: it is listed in
[`domain-model.md`](domain-model.md#known-gaps) and in the slice table.

## The ratchet

`tests/test_architecture.py` runs in CI alongside the test suite. Its contract is
one-way:

1. it starts with only the rules the code **already satisfies**, so the baseline
   is green and costs nothing;
2. each slice adds **one** assertion, in the same commit that makes it true;
3. no rule is ever weakened or removed to make a change pass.

Architecture is not maintained by remembering it in review. It is maintained by a
test that blocks the merge.

Rules live today (all passing): `core/` is free of Home Assistant imports; entity
modules never import the network; `core/` never imports entity modules; `const.py`
is a leaf.

## The route

Each slice is independently releasable, and lands one new rule.

| # | Slice | New rule it locks | Why here |
|---|---|---|---|
| 0 | This document, the domain model, the baseline test | the four rules above | costs nothing, sets the target |
| 1 | `transport/mqtt.py` — lift the broker client out of the coordinator | `paho` may only be imported from `transport/` | the sharpest cut, and the existing fake-cloud fixture makes it genuinely testable |
| 2 | `platform/legend.py` + `platform/regions.py` | `requests`/`ssl`/`socket` only in `platform/` and `transport/` | creates the seam a second stack would plug into |
| 3 | `domain/` — capabilities, commands, access | `domain/` imports neither HA nor the network | the invariants in the domain model get a home, and the retry policy lands where it belongs |
| 4 | `features/energy.py`, `features/comfort.py` | entity modules import only `features/` and `domain/` | the cards stop asking "which car is this" and start asking "what can it do" |
| 5 | the coordinator becomes orchestration | a size ceiling on `coordinator.py` | the result, not the goal |

Two consequences worth stating, because they change the order of unrelated work:

- The **retry policy for transient command rejections** belongs to
  `domain/commands.py`, i.e. slice 3. It is also a bug that bites today, so it
  ships tactically in the consolidation and is re-homed in slice 3 rather than
  waiting for it.
- The **capability model is what makes the dashboard cards portable**. Once a card
  can ask what a vehicle supports instead of which model it is, the same card
  works on every car in the family — and the compatibility matrix everyone has
  asked for becomes a report over the same data, not a separate hand-kept table.

## Out of scope

- Rewriting behaviour. Slices move code and lock rules; they do not change what
  the integration does. A slice that also changes behaviour is two commits.
- Implementing the other platforms. `platform/base.py` exists so that a second
  stack *can* be added by whoever reverses it; adding it is not part of this route.
- The Home Assistant domain rename. It is a user-visible migration with its own
  release and its own communication, and it is deliberately not bundled with any
  slice here.
