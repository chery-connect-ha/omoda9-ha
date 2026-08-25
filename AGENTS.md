# AGENTS.md — read this before you touch anything

You are probably a coding agent, working for someone who owns one of these cars
and does not necessarily read code or use GitHub. That is normal here: everyone
who built this integration built it this way. Your job is to make your human's
contribution land correctly **without them having to learn git**, and to stop
them from making the one mistake that actually hurts other people — claiming that
something works when nobody watched it work.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) for the reasoning. This file is the
operational half: what must never break, and the exact commands.

*(Human reading this: you don't need to understand any of it. Point your agent
here and carry on.)*

## What this project is

A Home Assistant integration for cars on the **Chery telematics platform** —
OMODA, Jaecoo and their siblings. It is unofficial and reverse-engineered. The
badge on the car is presentation; what actually varies is the authentication and
signing front door, the hostname of the region, and the set of commands a given
vehicle turns out to accept.

Where the truth lives, in order of authority:

1. `docs/design/domain-model.md` — what the integration talks about. The code
   implements it; it is not a description of the code. *(Proposed in #6.)*
2. `docs/design/architecture.md` — where things live and which way dependencies
   point. *(Proposed in #6.)*
3. `tests/` — what is actually guaranteed. `tests/test_entity_count.py` already
   enforces that no refactor quietly costs a user an entity;
   `tests/test_architecture.py` enforces the layering *(proposed in #6)*.

If your change contradicts one of these, the document wins, or the document
changes in the same pull request. Never leave them disagreeing in silence.

## Invariants — do not break these, ever

**Fail open.** If something cannot be read, is unrecognised, or times out, send
exactly what we sent before: full request, historic endpoint. The worst an
untested path may do is *fail to help*. It must never take away a function from
someone for whom it worked.

**Never remove or narrow a working entity or command** as a side effect of a
refactor. If the entity count changes, that is a deliberate, announced change —
and the test will stop you first.

**Never leave a language behind.** Anything that adds or renames a user-visible label or
an error message touches **three** files: `strings.json`, `translations/en.json` and
`translations/it.json`. A key present in one and missing in another produces an entity
with **no name at all** — but only for the people using that language, so whoever wrote
the change never sees it. `tests/test_traduzioni_complete.py` compares the key sets and
fails if they diverge; it checks that you did not forget a file, not that you translated
anything, so a key is only really done when the text is in the right language.

**No Home Assistant imports in `core/`.** The protocol logic must be exercisable
without Home Assistant installed. This is what lets the sandbox test a change
without an instance, and it is the rule the whole suite rests on.

**Entity modules never open sockets.** They render state and forward intent.

**No secrets, ever, in this repository.** No VIN, token, certificate, user id,
account identifier, or raw traffic capture — not in code, not in tests, not in a
log paste inside an issue. They appear in captured material far more often than
people expect. Redact before you paste. Fixture data is synthetic.

**No model names as code paths.** A new car is data plus capabilities discovered
at runtime — not a new branch, class, or `if model == …`. If you find yourself
adding one, you have found an architecture problem: say so instead of encoding it.

**Write the code in English — identifiers, comments and docstrings.** The people
maintaining this live in Italy, the UK, Denmark, Austria and Poland, and the prose around
the project is already English: commit messages, pull requests, `CONTRIBUTING.md`, this
file. The reasoning *inside* the code is the one place that is not, and it is the place a
new maintainer has to understand before they can change anything safely.

**Going forward, not retroactively.** Roughly 1,400 comments and 290 docstrings here are in
Italian, and they are the best asset this codebase has — measured, dated, specific. Machine
translating them would destroy exactly what makes them worth reading. So:

- **new code is English**, including variable and function names;
- **a block you are already editing becomes English** as part of that change — if you touch
  the lines, translate the paragraph you touched, and do it yourself rather than with a
  tool that will smooth away the detail;
- **everything else stays as it is** until somebody has a reason to touch it. A rule that
  makes the whole repository non-compliant on the day it is written gets ignored by the
  end of the week.

**Two things this rule does not cover**, deliberately:

- **entity translation keys and `entity_id` slugs** (`autonomia_benzina`,
  `carburante_residuo`, …), of which **91 out of 107 are currently Italian**. Those are
  user-visible identifiers: renaming one changes an `entity_id` and breaks somebody's
  automations, dashboards and long-term statistics. Never as a side effect of tidying.

  **They are not excluded forever, though — they are booked for the one moment when they
  are free.** The HA domain rename (`omoda9` → `chery_connect`) changes every `entity_id`
  in the integration anyway, and costs every user one reconfiguration. Renaming the slug at
  the same time costs them nothing on top of a migration they are already doing; renaming it
  at any other time is a second break for no reason. So the whole set moves **in that
  release and in no other**, listed in its notes, with an old → new table so people can fix
  their automations in one pass. See step 3 of #10;
- **the user-facing Italian in `translations/it.json` and in command-result text**, which is
  a translation and is supposed to be in Italian.

**The same rule covers everything you write on GitHub**: issues and their titles,
comments, review comments — not only the commit messages and pull request text the hook
below already refuses. Not as a matter of taste, but of who can read the queue.
@GurliGebis is building the merged repository and offered to handle the HACS
default-store submission, and has no Italian; @JackRonan, @ThomasMeyer1970, @Sisku and
@kowi4 all write in English. An Italian title on a pull request asks them to review code
through a thread they cannot read, and today several of the open ones do exactly that.

The exception is the one directly above, and the test is **who the sentence is addressed
to**: a collaborator, or somebody driving the car. `translations/it.json`, the Italian
half of `CHANGELOG.md` and command-result text stay Italian — they are translations doing
their job, and they are not to be "fixed".

**What enforces it: a reader, not a test.** No check can tell whether a comment is English,
so this is one of the few rules here that depends on somebody noticing in review. That is
stated rather than hidden — see *Before you write a rule, ask what would enforce it* above.
The one automated piece is the hook that already refuses non-English commit messages and
pull request text.

**The suite stays green.** Not "green after a follow-up" — green in the pull
request that changes the behaviour.

## Before you write a rule, ask what would enforce it

You will be asked to write rules — into this file, into `CONTRIBUTING.md`, into a pull
request description. **A written rule is free and a tool is not**, so the gap between what
the documents claim and what the repository actually permits widens on its own, silently,
until somebody tries to follow the rule and hits a wall.

When that happens it does not look like a rule being broken. It looks like a person not
bothering.

This project collected five of these in a single day, 24 August 2026:

- `CONTRIBUTING.md` said the review that counts is somebody running the change on their own
  car — while a pull request produced **nothing anyone could install**;
- both documents told people to use the labels `beta`, `unverified-hardware` and
  `merged-unread`, and **none of the three existed**. Two maintainers had just agreed to use
  one: they would have got an error;
- a maintainer proposed GitHub Projects while **Projects were disabled** and he had
  read-only access;
- another had built the executable form of these rules on his own machine, so his pull
  requests were better documented than everyone else's — not through more care, but because
  he had a gate and nobody else did;
- and `AGENTS.md` forbids AI co-authorship trailers while one maintainer's tooling adds one
  to every commit by default.

So, when you write a rule:

- **name the thing that enforces it** — a test, a CI job, a label that exists, a template
  field. If the honest answer is "whoever reads this will remember", it is not a rule, it is
  a hope, and hopes should be written as advice rather than as requirements;
- **ship it in the same change.** `tests/test_traduzioni_complete.py` arrived in the same
  commit as the rule about the three language files, and it started green — a rule that is
  already true, pinned so it cannot quietly stop being true;
- **check the thing exists before telling somebody to use it.** Open the settings, list the
  labels, read the permissions. It takes a minute and it is the difference between an
  instruction and an error message.

## The discipline that matters most: don't overstate evidence

Half of this codebase is written for cars the author does not own. That is
unavoidable and it is fine — as long as it is labelled.

Before you write that something works, in a commit message, a pull request, a
changelog or a release note, ask your human **one question**:

> Did you watch the car do it, or did the backend answer OK?

They are different claims. The backend returning `operation.successful` means the
request was accepted; it does not mean the vehicle acted. A command has been
verified only when a state field on the car changed, at a time you can point to.

- If the human owns the car and watched it: say so, and say when.
- If the human owns the car and only saw the backend accept: say *that*, in those
  words.
- If the human does **not** own that model: write the code, open the pull request,
  and mark it `unverified-hardware`. Do not soften it into "should work".

An overstated claim is the only kind of damage in this project that reaches a
stranger. Wrong code gets found; a wrong claim gets believed.

### Say which part was yours and which was the agent's

Nobody here writes this code by hand; all of us drive a model. So "I read it" and
"the agent I drive read it" are different claims, and letting them blur is how a
statement ends up carrying weight it did not earn.

Wherever a claim rests on a **reading, a count or a check**, say who performed it.
A short line at the top or the bottom is enough:

> *The reading of `routing.py` behind this was done by the agent I drive. The
> conclusion, and what to do about it, are mine.*

Two rules under that, and the first is absolute:

- **Never write that your human read something they did not read.** Not in a
  review, not in a pull request, not in a comment. This is the same failure as
  claiming a car did something it did not do, pointed at ourselves — and it is
  the one that cannot be walked back, because it is the basis on which everything
  else here is believed.
- **State facts so they can be checked without you.** A file and a line beats a
  summary: `lock.py` line 44 rather than "the lock handling looks correct". Then
  it does not matter who read it.

This is not about crediting tools. It is that a project which gates on evidence
has to apply the same standard to how it describes its own work.

## How a change moves

Land it (small pull request, CI green), it ships to volunteers as a
**pre-release**, and it becomes **stable** only once someone who owns each
affected model has run it. Nothing waits on anybody's free time except the last
step. Full rules in [`CONTRIBUTING.md`](CONTRIBUTING.md).

A pull request can also be made installable **before** it lands — label it
`beta` and a pre-release is cut from it. Reach for that whenever the change is
written for a car you do not own: your instance cannot disprove it, and this is
what puts it in front of the person whose instance can, while there is still
time to change it.

## The commands

`master` is protected: no direct pushes. Everything below assumes the remote is
called `origin`. Replace `<name>` placeholders.

**Once, to get set up**

```bash
git clone https://github.com/chery-connect-ha/omoda9-ha.git
cd omoda9-ha
gh auth status || gh auth login     # the GitHub CLI, for pull requests
```

**Start a piece of work — always from an up-to-date `master`**

```bash
git fetch origin
git switch -c fix/<short-name> origin/master
```

Name it for the behaviour, not the file: `fix/charge-energy-undercount`, not
`fix/coordinator`.

**Keep it current while it is open — not only when it conflicts**

```bash
git fetch origin
git merge origin/master
git push
```

Do this whenever `master` has moved and your branch has been open more than a day
or two. Conflicts are the obvious reason and the least important one. The real
reason is that **a branch that sits behind loses access to whatever arrived after
it was cut, and finds out by nothing happening**:

- on 24 August the `beta` label was applied to two pull requests in the same
  minute. One published a pre-release; the other produced **no workflow run at
  all and no message**. The workflow had landed on `master` a minute after that
  branch's last commit;
- a stale branch also carries stale CI. A green tick from five days ago says
  nothing about today's `master`, and GitHub may not even have recomputed whether
  the branch still merges.

If you label a pull request and no run appears within a minute, the label did not
take: push the branch and try again, or use `workflow_dispatch`, which runs from
the default branch and does not depend on yours.

**Save the work**

```bash
git add -A
git commit -m "<what changed and why, in one line>"
```

Write the message for the person who will run `git blame` in a year. Reference
the issue (`#12`) when there is one. Never add AI co-authorship trailers — how
this project credits its tools is a decision for the group, not a default.

**Run the checks locally if you can**

```bash
pip install -r requirements_test.txt
pytest tests/ -q
```

Home Assistant needs Python 3.13+. If the local Python is older, skip it and let
CI be the gate — that is why CI exists — but say so in the pull request.

**Open the pull request**

```bash
git push -u origin HEAD
gh pr create --fill
```

**Put `Closes #12` in the body when the pull request finishes an issue.** GitHub then
closes it on merge, and links the two forever. Without it somebody has to remember, and
nobody does: on 24 August this repository had fifteen issues of which exactly one was
closed — by the single pull request that carried the line.

Use it only when the merge really finishes the issue. If it fixes part of one, write
`Relates to #12` and say in the body what is left, so the issue outlives the merge instead
of being closed on a half-answer.

Then fill in the field-test block in the template. If you did not test on
hardware, say it there rather than leaving it blank:

```bash
gh pr edit --add-label unverified-hardware
```

**Get it onto a real car, before it lands**

```bash
gh pr edit --add-label beta
```

This publishes a pre-release built from the pull request, installable from HACS
with *Show beta versions* on. Ask for it whenever the change touches a model
nobody testing it here owns — including your own author's case, where the change
is a no-op on your car and therefore unfalsifiable by you. Post the release link
in the pull request and name who you are asking. Only write access can label, so
a tester never has to run anything: they get a link.

A beta is never cut from a fork. If this pull request comes from one, a member
publishes it by hand after reading what is in it.

**When CI is red**

```bash
gh pr checks                    # what failed
gh run view --log-failed        # why
```

Fix, commit, `git push`. The pull request updates itself; do not open a new one.

**When `master` has moved on and the pull request shows a conflict**

```bash
git fetch origin
git merge origin/master         # resolve, then:
git commit
git push
```

Use `merge`, not `rebase`. Rebasing a branch that is already pushed requires a
force-push, and a force-push is how history gets lost by people who did not
intend to lose it.

**When review comes back**

Make the changes on the same branch, commit, push. Do not close and reopen. Reply
to the comment saying what you changed — a review is a conversation, and silence
reads as disagreement.

**Cutting a release** (maintainers)

A pre-release from a pull request is the `beta` label — do not do it by hand.

For a **stable**, the archive is not optional. `hacs.json` sets `zip_release`
with `omoda9.zip`, so HACS installs *only* from a release carrying that asset:
publish without it and HACS lists the version and then fails to install it,
which is worse than not publishing at all.

```bash
# from a clean checkout of the commit you are releasing
cd custom_components/omoda9
git ls-files -z | xargs -0 zip -q -X ../../omoda9.zip
cd -
gh release create v<X.Y.Z> omoda9.zip --latest --generate-notes
```

Only tracked files, and the contents of `custom_components/omoda9/` sit at the
root of the archive — that is where HACS expects them with
`content_in_root: false`. The version in `manifest.json` must already match the
tag. A stable also requires the field tests described in `CONTRIBUTING.md`.

## Getting out of trouble

**"I committed on `master` by mistake" (locally, not pushed)**

```bash
git branch fix/<short-name>          # keep the work on a branch
git reset --hard origin/master       # put master back
git switch fix/<short-name>
```

**"I have changes and I'm on the wrong branch"**

```bash
git stash
git switch -c fix/<short-name> origin/master
git stash pop
```

**"I committed something secret"**

Stop. Do not push. Do not open a pull request. Say so to the maintainers
immediately — a secret that reached the remote has to be treated as leaked and
rotated, and that is a different, much longer procedure than fixing it before it
leaves the machine.

**Never**: force-push a shared branch, rewrite published history, push straight
to `master`, or bundle unrelated changes to "save time". Each of those turns a
five-minute problem into somebody else's afternoon.

## When you are not sure

Open an issue and describe what you observed, rather than guessing in code. An
observation nobody can explain yet is more valuable to this project than a fix
nobody can verify — it is, quite literally, how every command we speak was found
in the first place.
