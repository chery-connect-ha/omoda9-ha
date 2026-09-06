# `tools/` — the rules, in a form that can be run

`CONTRIBUTING.md` and `AGENTS.md` say what this project expects. This directory is the
same thing written so a machine can check it before something irreversible happens.

It arrives here because @drake69 asked for it on
[#25](https://github.com/chery-connect-ha/omoda9-ha/pull/25#issuecomment-5395878567): a
rule only one machine can enforce is a rule the other three of us are guessing at. He also
said the interesting half is the checklist rather than the shell, and he is right — the
table below is the part that ports without change.

**Nothing here is required.** `git push` and `gh pr create`, as written in `AGENTS.md`, work
fine and always will. These scripts just refuse to let you forget something.

## What each one does

| | |
|---|---|
| `rules.sh` | the rulebook itself: `list`, `check` (read-only preflight), `log`. Also the library the other two load |
| `pr.sh` | land a change: branch, gates in order, push, pull request filled from the repository's template |
| `release.sh` | `status` · `prepare` (version bump + pull request) · `publish` (archive, tag, release, zip — only on green CI) · `abort` |
| `check-secrets.sh` | every confidential pattern, across the **whole history** and the working tree, including files git has never seen |

A pre-release from a pull request is the `beta` label, never a script.

## Quick start

```bash
gh auth login                       # or: export GH_TOKEN=...
./tools/rules.sh list               # the 26 rules, with sources
./tools/rules.sh check              # read-only: what would stop you right now
./tools/pr.sh "fix: what changed and why"
```

`check-secrets.sh` also wants a file that is **not** in this repository and never can be:

```bash
cp tools/private-patterns.example.txt tools/private-patterns.txt   # gitignored
```

Put your own name, your own paths and your own machine names in there. They are exactly
the strings the checker exists to catch, so writing them into a tracked file publishes
them — and the checker would not even notice, because a regex written with backslashes
does not match itself. That is not a hypothetical: the author's e-mail address sat inside
this tool for months, in the line meant to protect it.

## The gate, and what it honestly is

A failing gate stops the script. Past it there are two doors:

- **a person at a terminal** — the dialogue runs on `/dev/tty`, you type a phrase
  containing a one-time code printed at that moment, and you write a reason of at least
  20 characters. It goes into `DEROGATIONS.log`, and if that file cannot be written the
  derogation is not granted;
- **`--authorized "<what you were told>"`, for agents** — most of us drive a coding agent,
  and an agent has no terminal. Without this, every failing gate is a wall with no
  recourse, and a tool that only works when everything is already green is a tool nobody
  uses. It opens **only for NORMAL-severity rules**, and the sentence is recorded word for
  word.

There is a third flag in the same spirit. `pr.sh --evidence backend|not-mine|none` lets a
script state what the evidence is, instead of falling back to `unverified-hardware` because
nobody was at a terminal — which would put a false line in the next release notes for a
change that touches no runtime behaviour at all. It deliberately **cannot** say *verified
on hardware*: that answer means somebody watched a car, and nothing running without a
person present is in a position to say so. The three it does accept can only ever weaken a
claim.

**What this is not.** No local mechanism can tell a person apart from a program that sees
the same terminal — `script -qec`, `expect` and `tmux send-keys` can all read the one-time
code and type it back. What is actually guaranteed is that a derogation cannot happen *by
accident*, and that every one leaves a written line or does not happen. That is a high
kerb and an honest register, not a wall. Anyone who calls it unbypassable is doing the
thing this project forbids in writing: claiming a check they do not have.

`--authorized` is weaker still, and says so: the script cannot verify that anybody
authorised anything. What it does is make the claim explicit and permanent.

## The 26 rules

**HIGH** = the damage leaves this room and reaches somebody who is not in it.
**NORMAL** = the damage stays at home.

A source marked **house rule** has no prose behind it in this repository. It is the
practice of the maintainer who wrote these scripts, kept because the gate is useful — not
something the group has agreed. They are marked rather than smuggled in, and they are open
to argument like everything else.

| | | Rule | Source | Gate |
|---|---|---|---|---|
| **R01** | HIGH | Never push to `master` — everything lands as a pull request | `CONTRIBUTING.md` *Never*; `AGENTS.md` *The commands*; branch protection | blocks |
| **R02** | HIGH | Never a secret: VIN, token, certificate, `tUserId`, account id, e-mail, phone, raw capture | `CONTRIBUTING.md` *Never*; `AGENTS.md` *Invariants*; `SECURITY.md` | blocks (`check-secrets.sh`, after the commit, before the push) |
| **R03** | HIGH | CI green on the **exact** commit being published | `CONTRIBUTING.md` *It lands*; branch protection | blocks |
| **R04** | HIGH | Changelog written for non-programmers, in both languages, never `--generate-notes` | **house rule** — and `AGENTS.md` *Cutting a release* currently suggests the opposite | blocks |
| **R05** | HIGH | At most one stable release every two weeks | **house rule**, from measured history (45 releases in 30 days) | blocks |
| **R06** | NORMAL | Shared code asks for a read by somebody who is not the author | `CONTRIBUTING.md` *It lands* | **warns** — the source says merging is never blocked |
| **R07** | HIGH | Never claim a hardware check you do not have; the unverified gets **named** | `CONTRIBUTING.md`; `AGENTS.md`; `docs/field-test.md` | asks, and labels `unverified-hardware` |
| **R08** | HIGH | No stable release without the `omoda9.zip` asset | `AGENTS.md` *Cutting a release*; `hacs.json` | blocks — archive built and validated **before** the tag |
| **R09** | HIGH | No force-push, no rewriting published history | `AGENTS.md` *Never*; branch protection | blocks |
| **R10** | NORMAL | No AI co-authorship trailers in commits | `AGENTS.md` *Save the work* | blocks |
| **R11** | NORMAL | No Home Assistant imports inside `core/` | `AGENTS.md` *Invariants* | blocks |
| **R12** | HIGH | Fail open; never take away an entity or a command that worked | `AGENTS.md` *Invariants*; `tests/test_entity_count.py` | blocks on a red suite; **warns** when there is no local interpreter, as `AGENTS.md` allows |
| **R13** | NORMAL | One behaviour per pull request | `CONTRIBUTING.md` *Keep changes small* | warns |
| **R14** | NORMAL | Private material stays out of the repository | `CONTRIBUTING.md` *Never*; `SECURITY.md` | blocks; again before every `git add`; and it checks git is not silently *ignoring* `tools/` |
| **R15** | HIGH | Never send a command to a car without the owner's explicit go-ahead | **house rule** for agent-driven work | none — it is for the person, not the script |
| **R16** | NORMAL | Never cut a release in order to test: that is what `beta` is for | `AGENTS.md`; `CONTRIBUTING.md`; `.github/workflows/beta.yml` | none |
| **R17** | NORMAL | The repository is the source of truth, never the installed copy | **house rule** (generalises to any HA integration) | none |
| **R18** | NORMAL | After publishing, tell the car owner the next step is theirs | **house rule** | none |
| **R19** | HIGH | Before a **stable**, a field test for every model in the blast radius | `CONTRIBUTING.md` *It becomes stable* — *"the only real gate"* | blocks |
| **R20** | NORMAL | A read is promised within a week, then `merged-unread` | `CONTRIBUTING.md` *The one-week rule* | none |
| **R21** | HIGH | No model names as code paths | `AGENTS.md` *Invariants* | blocks |
| **R22** | HIGH | The token is never committed nor left in `.git/config` | derived from `AGENTS.md` *Invariants*; `SECURITY.md` | blocks |
| **R23** | HIGH | `manifest.json` already matches the tag | `AGENTS.md` *Cutting a release* | blocks |
| **R24** | NORMAL | After an update: HA `RUNNING`, the entity count the test asserts, none unavailable | `tests/test_entity_count.py`; the inspection itself is a **house rule** | none |
| **R25** | HIGH | Say **who** did the work a claim rests on: a person, or an agent they drive | `CONTRIBUTING.md` *Never*, merged in [#28](https://github.com/chery-connect-ha/omoda9-ha/pull/28); @drake69's convention in [#7](https://github.com/chery-connect-ha/omoda9-ha/issues/7) | asks and records — it cannot verify |
| **R26** | HIGH | Re-read the thread before publishing a reply: somebody may have written since you drafted | a real mistake on 2026-08-24 | **not here** — it lives in the maintainer's local drafting tool |

Two of those deserve a footnote.

**R04 and R05 are house rules with blocking gates.** That combination is deliberate but it
is the most arguable thing in this directory: a bilingual changelog and a two-week cadence
are this maintainer's practice, and if you are cutting a release they will stop you. If the
group wants them, they belong in `CONTRIBUTING.md` as prose, and that is a separate pull
request. If the group does not want them, delete the gates.

**R25 asks, it does not verify.** No program knows who really read a file. The gate
recognises explicit first person ("I checked", "ho verificato") and, when the text does not
say whose work it is, makes you answer and writes the answer at the bottom. It deliberately
ignores impersonal forms ("Verified: 107 entities"), which are ambiguous by construction
and would produce enough false positives to teach everyone to ignore the warning. Measured
on the real material before adopting it: three lines in a 97 KB `CHANGELOG.md`, one in two
hundred commit messages.

### What `check-secrets.sh` will not catch

Measured, not assumed. The allowance that stops fixtures failing the gate is shared by
every pattern and filters by **line**, so any line containing the word `example` is exempt
from all of them: a real address pasted as `someone@example.com` goes through. The phone
shapes lean Italian, so a UK or Danish number is only caught by the international form.
And the whole thing is regex over text — it recognises the shapes it was told about, and
nothing else.

It is written down because a checker people trust more than it deserves is worse than no
checker at all.

## What is deliberately not here

- **A comment tool.** The maintainer has one, and it stays local: its distinguishing
  feature is a mandatory summary in Italian for a car owner who does not read code and
  should not approve English text blind. That is one person's problem, not the project's.
  R26 is its rule, which is why R26 is listed above with no gate rather than quietly
  dropped — a hole in the numbering would be more confusing than an honest line.
- **A deploy script.** It copies the component into one particular Home Assistant VM. The
  channel is HACS (R16); a fallback shaped around one person's virtualisation setup is not
  worth publishing.

## Portability, stated rather than discovered

- **Fork or upstream.** `pr.sh` pushes to `origin` and opens the pull request against the
  upstream repository, using `owner:branch` as the head when they differ. Set
  `OMODA9_REPO` if you work against a different upstream. A beta build is never cut from a
  fork.
- **Python.** Home Assistant needs 3.13+. The suite gate looks at `$VIRTUAL_ENV`, then
  `.venv/`, `.venv-test/`, `venv/`, `env/` inside the checkout, then
  `python3.14`/`python3.13`/`python3`. If none of them has pytest, it says so
  and lets CI be the gate — and the pull request body says the suite did not run locally.
  The interpreter is deliberately **not** settable from the environment: that variable was
  once the shortcut that made the suite gate pass without running a test.
- **macOS/BSD.** `grep -oP`, `sed -i` without a suffix, `base64 -w0` and `date -Is` are all
  GNU-only and none of them is used any more. If you find another, it is a bug.
- **`zip(1)` is not assumed.** The release archive is built by python, and validated before
  anything is tagged. It used to be built after the release was created, on a host with no
  `zip` — which produced a published release with no asset, exactly what R08 calls worse
  than no release at all.
