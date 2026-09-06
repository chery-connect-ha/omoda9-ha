# Contributors

Everyone who built a line of this. Two things worth stating before the list, because
they decide who is on it.

**Field testers count the same.** Someone who runs a build on their own car and reports
what the car actually did contributes something nobody else can produce — half of what
ships here is written for models the author has never sat in, and on the author's own car
it is a no-op that cannot be proved or disproved. There is one list, not a list of
developers and an appendix of testers.

**These are people's own words.** The entries below were written by the people they
describe, in response to [#8](https://github.com/chery-connect-ha/omoda9-ha/issues/8), and
are reproduced as written. If yours is missing, add it — nobody else should have to guess
what you did.

Listed alphabetically. The order means nothing.

---

**@Caslinovich** — reverse-engineered the Chery backend from my own car: endpoints, command
schema, SM2/SM4 signing, MQTT map. Author of the first version of the integration, written
with Claude Code. Field-tested on an Omoda 9 (BEV), Italy.

**@drake69** — CI hardening, clearer OTP-send errors and the repository's first automated
tests; home-versus-away charging energy with the "At Home" sensor and the energy card; the
climate setup-macro card. Reported the Lovelace card XSS privately. From August: the shared
organisation, the target architecture and the CI ratchet that holds it, the collaboration
model, and the beta build that makes a pull request installable on a real car. Driving
Claude Code throughout. Car: Omoda 5 Premium (BEV). Region: EU, Italy.

**@JackRonan** — Worked on extraction of the Omodao Jaecoo APK independently before finding
and forking @Caslinovich' work on the omoda9 repo. From there, driving Claude Code through
most of the coding, I worked on Omoda/Jaecoo generalisation, PHEV/BEV-agnostic sensors,
entity-naming overhaul, the custom Lovelace card, per-vehicle capability detection, charging
sensor and re-auth flow, phone/SMS login, and some security hardening. Credit where it's
due: Rino had already cracked the auth flow and captcha before I forked, and Luigi pitched in
directly too, with PRs for CI hardening, speaking OTP-send errors, and the home/away charging
energy feature. Fixes have gone both ways between the two repos after that: I ported several
parts of Rino's work into the fork, and some of mine went back upstream too. Car: Omoda E5,
Region: UK

**@Sisku** — reported the PIN login bug on issue #4 (phone login always failing with the
vehicle-control-PIN error even with the correct PIN; found that email login works around it).
Later found that "Refresh full status" succeeds without asking for the PIN when the car is
actively charging, but always fails with the PIN error when the car is idle — pointing to the
vehicle's deep-sleep state as the real cause, not the PIN itself. Car: Omoda 9. Region:
Catalonia, Spain.

**@ThomasMeyer1970** — field tester. Found that `queryVehicleAuthority` only returns data
when the body carries `tUserId` and `channelId` next to `vin`, and traced the A00084
failures to the per-vehicle permission list it returns. Measured that the backend validates
macro bodies field by field, not atomically — which is what made field pruning viable
instead of hiding buttons. Confirmed at the car that a composed `airControl` with
`mSeatAiry`/`pSeatAiry` really does ventilate the seats. Also reported two J7 unit bugs:
`oilSurplus` is percent, not litres, and `cruiseRange` is km, not miles. Car: Jaecoo J7 SHS
(PHEV). Region: EU, Austria.

---

## How this was written

**None of us wrote this code by hand.** All four maintainers drove a model — Claude Code, in
every case — and that is simply a fact rather than a disclaimer. It is stated here because
@Caslinovich asked for it on #8 and nobody argued: *"yes, put it in the file. None of us
wrote this code by hand."* @JackRonan had already said it in his own entry without being
asked.

It matters beyond bookkeeping. Generative code accretes faster than anyone reads it, which
is why this project gates the **stable release** rather than the merge, and why the review
that counts most here is somebody watching their own car do the thing. The rules are in
[`CONTRIBUTING.md`](CONTRIBUTING.md); the reasoning is in
[#2](https://github.com/chery-connect-ha/omoda9-ha/issues/2).

The same distinction applies to what we write about the work: where a claim rests on a
reading or a check performed by an agent rather than by the person signing it, that gets
said. "I read it" and "the agent I drive read it" are different claims, and letting them
blur is how a statement ends up carrying more weight than it earned.

## Still missing

These people have contributed and have not yet written their line — the invitation on #8 is
open, and an entry written by somebody else would be a worse version of the truth:

- **@GurliGebis** — built the merged repository that served as the completeness checklist for
  the consolidation, and offered the HACS default-store pull request.
- **@MassimoDe** — reported the SMS login failure on #5, the report that led to the identity
  fix in #14.
- **@kowi4** — asked for username-and-password sign-in on #13, which became #16.
- **@divisl** — brought the Chery Europe backend into view: a different gateway behind the
  same app family.
- **@YasM0** — invited on #8.

And anyone not on this page who should be. Open a pull request against this file, or say so
on #8 and it will be added.
