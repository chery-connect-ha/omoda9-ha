# Contributing

> **Status: proposed.** This document describes rules that have been agreed in
> outline but not yet ratified, and it arrives as a pull request rather than as a
> push to `master` — which is itself the first rule it asks for. Argue with the
> text, not with whoever opened it.

## In one page

**What this is.** A Home Assistant integration for cars on the Chery telematics
platform — OMODA, Jaecoo and their siblings. Unofficial, reverse-engineered,
built by four people who each own one of these cars.

**What is scarce here.** Not writing code: an agent writes faster than any of us
can read. What is scarce is **checking** — and a check is what makes a claim true
for somebody else's car. Everything below is bookkeeping for that.

**Four things, kept apart on purpose.**

| | what it is | who touches it |
|---|---|---|
| **The instrument** | `sandbox/` — log in, send a command, see the answer, with no Home Assistant involved | rarely anyone |
| **The protocol** | authentication, signing, transport. No Home Assistant imports, so the sandbox can drive it | whoever reads code |
| **The catalogue** | rows: *verb, body, subject, when, accepted, acted* — what a real car answered, on a date | **whoever owns a car** |
| **The integration** | entities, state, the buttons people press | whoever reads code |

Adding a car should mean adding rows, not adding code paths.

**How a change moves.** It **lands** — cheaply if it only touches your own car's
data, with one read by somebody else if it touches shared code, and labelled
`unverified-hardware` if it is written for a car none of us owns. It **ships as a
pre-release** — on merge, or from the pull request itself if you label it `beta`
— so you have your own work on your own car the same day. It becomes
**stable** only once someone who owns each affected model has run it. Merging is
never blocked. Only the last step is.

**Who does what.** If you own a car, you are the only proving ground for it — and
half of what we ship is written for models the author has never sat in. If you
read code, you carry the reads. Nobody approves because they own the org.

**The rest of this file** is the detail: the gates, the one-week rule, the
labels, and the things never to do. The method for checking is in
[`docs/field-test.md`](docs/field-test.md); the commands your coding agent needs
are in [`AGENTS.md`](AGENTS.md).

---

None of the people who built this integration wrote it by hand. Each of us drove
a model, on our own car, and the code arrived faster than any of us can read it:
the runtime is over eleven thousand lines in a couple of months, and a single
release once landed 4,500 lines in thirty-four hours. That is not a complaint —
it is the engine of the project, and slowing it down would cost more than it
saves.

But it changes what is scarce. Writing is cheap here; **checking is expensive**,
and checking is the only thing that makes a claim true for somebody else's car.
So the currency of this project is not lines of code. It is **claims that have
been checked**, and everything below is bookkeeping for that one idea.

## Roles — each defined by what only you can do

**Field authority.** If you own a car, you are the only proving ground for it.
Nobody can buy their way around this, and it cannot be delegated: half of what
we ship is written for models the author has never sat in, and on the author's
own car that code is often a literal no-op — it cannot be falsified where it was
written. Your car can falsify it. That is worth more than an approval on a diff.

**Protocol source.** If you captured a telematics stack, you own the *method*.
The method is universal, because the app is universal; the endpoints and commands
you verified are specific to the car you verified them on. Both matter, and they
are different artefacts: the method is written down once and published, the
captures stay private and per-model. See [`docs/field-test.md`](docs/field-test.md).

**Code reader.** If you read diffs, you carry the reads. There are fewer of you
than of us, which is why the gate below is proportional rather than uniform.

**Coordinator.** Keeps the plan current and the boundaries visible. No casting
vote: the plan is a document to be argued with, not an office.

**Nobody approves because they own the org.** An approval that isn't backed by
either a read or a car is a signature, and a signature is worth nothing here.

If you cannot read code, you are not a second-class maintainer in this project.
You hold the only instrument that can disprove half of what we ship.

| Who | Car | Region |
|---|---|---|
| @Caslinovich | Omoda 9 | IT |
| @drake69 | Omoda 5 BEV Premium | IT |
| @JackRonan | Omoda E5 | UK |
| @GurliGebis | Jaecoo J5 EV | DK |

If you own a Chery-platform car and are willing to run a check when asked, add
yourself to the tested-models issue. You do not need to write code to be
essential to this project.

## How a change moves

There are three moments, and only the third one is a gate on other people.

### 1. It lands

The cost of review is proportional to the blast radius, because a uniform tax
prices the harmless change the same as the dangerous one — and then everybody
routes around it.

| What the change touches | What it needs to merge |
|---|---|
| Data or capabilities for a car **you own** | CI green |
| **Shared code** — `core/`, `platform/`, `transport/`, `coordinator.py`, auth, signing, the entity model | CI green **+ one read by somebody other than the author** |
| Behaviour for a car **nobody here owns** | CI green, merged with the `unverified-hardware` label |

The third row is the important one. Code written for a model you cannot test is
**not blocked** — it merges, and it merges honestly labelled. What you may not do
is *claim* it works. Merging is a statement about the code; the label is a
statement about the evidence, and only the second one can be wrong in a way that
reaches a stranger's car.

### 2. It ships to the people who asked for it

Merges go out as **pre-releases**. Anyone who wants them turns on *Show beta
versions* for this repository in HACS and has them on their own car the same day.
This is deliberate: nobody in this project should ever be separated from work they
just did because they are waiting on somebody else's free time.

**And it can ship before it lands.** Put the label `beta` on a pull request and a
pre-release is built from it, installable the same way. That is what carries a
change to the one person who can disprove it *while there is still time to change
it* — which matters most exactly where the author is powerless: code written for a
car they do not own is, on their own car, a no-op. It is two taps in a phone
browser, and only write access can do it, so a tester never runs anything.

### 3. It becomes stable

**This is the only real gate.** A stable release is a statement to strangers, so
before one is cut:

- every model in the blast radius of the changes has had a field test — one
  report, from someone who owns that car, in the form described in
  [`docs/field-test.md`](docs/field-test.md);
- anything still carrying `unverified-hardware` is named as such in the release
  notes, rather than being quietly folded in;
- the suite is green and the entity count is unchanged (`tests/test_entity_count.py`),
  which is checked by CI and not by anybody's memory.

A stable release may therefore ship unverified code. It may not ship unverified
code *silently*.

## The one-week rule

A read is promised within **one week**. If nobody has read it by then, the author
merges it themselves and labels it `merged-unread`.

This is not a loophole, it is the point: the rule must fail loudly instead of
stopping everyone. If `merged-unread` starts appearing regularly, the rule has
failed and we drop it — better an honest record of what nobody read than a queue
of pull requests that quietly teaches everyone to stop opening them.

## Keep changes small

A large change is one nobody can review, and asking for review of an unreviewable
diff is theatre. One behaviour per pull request; a behaviour that needs sixteen
files is telling you something about the architecture, not about your discipline.

If you have been working offline for a while and have a pile of improvements,
open them one at a time rather than as one bundle. It is more work for you and
much less work for everyone else.

## Labels, and the matrix that comes out of them

- `verified:<model>` — somebody with that car ran it and reported.
- `unverified-hardware` — written for a model none of us could test.
- `needs-field-test:<model>` — a specific ask, waiting for a specific car.
- `merged-unread` — merged because the week elapsed.

The tested-models matrix is generated from these. It is not documentation to be
kept by hand: it is the register of **who can check what**, which is the same
question as who can review what.

## Never

- **Push to `master`.** Everything lands as a pull request, including from the
  people who wrote this file.
- **Commit a VIN, a token, a certificate, a user id, or a raw capture.** They
  turn up in logs far more often than you would expect. Redact first; captures
  belong in the private channel, never in this repository.
- **Claim hardware verification you do not have.** "The backend accepted it" is
  not "the car did it". If you did not watch the car, say so.
- **Say you read something when your agent read it.** All of us drive a model, so
  where a claim rests on a reading, a count or a check, say who performed it — one
  line is enough. This is the same rule as the one above, pointed at ourselves,
  and the reason for it is the same: everything here is believed on the strength
  of what we say we checked. Facts stated with a file and a line survive the
  question entirely.
- **Remove a function that worked for somebody.** When in doubt the code fails
  open: unknown, unreadable or timed-out means *send exactly as before*. The worst
  an untested path may do is fail to help.

## The mechanics

**If this is your first change here, start with the shape of the repository, because
getting it wrong costs you a rewrite rather than a correction.** There is one long-lived
branch, `master`, and no `develop`. It is protected: nobody pushes to it, maintainers
included, and everything arrives as a pull request. If you are contributing from outside,
you cannot push a branch here at all, so you fork first and open the pull request from
your fork.

The part people get wrong, and it has already happened here: **do not commit on the
`master` of your own fork.** Make a branch, even for a one-file change. A pull request
opened from `master` follows that branch, so anything else you commit afterwards lands
inside the open pull request, and you are limited to one at a time. `AGENTS.md` has the
exact commands for both cases, fork and clone.

If you are working with a coding agent — and most of us are — point it at
[`AGENTS.md`](AGENTS.md) before it touches anything. It carries the invariants
above plus the literal git and GitHub commands for branching, opening a pull
request, syncing and getting out of trouble. You are not expected to know
GitHub to contribute here.

Everything above is prose, and prose is a thing to remember rather than a thing that
stops you. [`tools/`](tools/) is the same rules written so a machine can check them:
numbered `R01`–`R26`, each one pointing back at the paragraph here or in `AGENTS.md`
that it comes from, and each one saying whether it blocks, warns, or merely asks.
`./tools/rules.sh list` prints the table. Where a rule has **no** paragraph behind it in this
repository, it is marked a house rule of whoever wrote the scripts, rather than
presented as something the group agreed.

Using it is optional and always will be: `git push` and `gh pr create` are in
`AGENTS.md` for a reason. The point of putting it here is that a rule only one machine
can enforce is a rule the rest of us are guessing at.
