# Field test — how we check that the car did it

Half of what this project ships is written for cars the author has never sat in.
That is not sloppiness, it is the shape of the problem: one person captured the
protocol on one model, and the fix for somebody else's model is, on the author's
own car, a literal no-op — it cannot be proved or disproved where it was written.
A field test is how that gap gets closed, and it is the one contribution that
cannot be delegated to whoever is most comfortable with code.

The method below is not new. It is what was already being done, written down so
that anyone with a car and half an hour can repeat it.

## The two layers

Almost every mistaken claim in this project comes from confusing them.

**Layer one — the backend accepted.** The request was well formed, signed, and
authorised. `operation.successful`. This says something about *us*.

**Layer two — the car acted.** A state field the vehicle reports changed, at a
time you can point to. This is the only layer that says anything about the car.

A command is verified at layer two or it is not verified. `HTTP 200` with
`code: 1` has been observed on a request the backend then refused at application
level, and a comfort macro has been seen to return success while the car cooled
down and switched itself off — the acceptance was real and the outcome was wrong.

## The procedure

**1. Write the prediction before you press anything.** One sentence: *"if I send
X, field Y should become Z within N seconds."* Written afterwards it is a story;
written beforehand it can be wrong, which is the entire value.

**2. Change one variable.** One field, one command, one setting. Two changes at
once produce a result nobody can attribute — and the refusals here are total: a
single denied field makes the backend reject the whole request, including the
parts the vehicle would have authorised. That is exactly the kind of finding a
single-variable test produces and a multi-variable one hides.

**3. Record the time.** Wall-clock, to the second, for the command and for the
observed change. Timing is not decoration: an ordering defect in the climate
macros was found only because "off" pressed first left the queue *after* "on"
pressed ten seconds later, and a warning meant for the user was found to have
lived for twelve milliseconds before the next message overwrote it. Neither is
visible without timestamps.

**4. Confirm on a state field, not on the button.** Name the field and its value.
A switch that stays on proves nothing about the car.

**5. Confirm the negative too.** Send the opposite command and watch it come back.
A test that only ever moves one way cannot distinguish "the car obeyed" from "the
field was already there".

**6. Say what you could not test.** The gap is part of the result. "The car does
not have that hardware" and "I did not try" are both useful, and they are
different.

## What a report is: one row

A report is not prose that somebody later turns into data. It **is** the row —
the same shape the model catalogue stores, so the sandbox can emit it for you.

```
verb:      windowControl
body:      {controlType: open, windowType: 2}    <- the one thing you varied
subject:   Omoda 9 - IT - fw <x> - declared: [...]
when:      2026-06-20 19:43:58
accepted:  A00079
acted:     fWinHeatingState 0 -> 1 at 19:44:12   <- empty if you did not watch
not tested: rear glass heating: different function, different state field
```

Four things, and the two people forget are the **body** and the **when**.

**The body, not just the verb.** The outcome is a function of what you sent, not
of the command's name. Changing only `cycleData` turned `[1,3,5]` into `A00084`
and `[1..7]` into `A00079`; changing only whether `backDefrosting` was present
flipped refusal into acceptance. One denied field makes the backend reject the
whole request, including the parts the car would have allowed.

**The when, because an outcome is an observation and not a property.** The same
car accepted a comfort macro four times in one day and refused it that evening.
A row may say "on this vehicle, with this body, at this time, the answer was
A00084". It may not say "this model cannot".

**The subject is the vehicle, not the model.** Two cars of the same model on the
same firmware do not necessarily accept the same commands, because what a car
can do is declared by the backend per vehicle. Model and region are the label we
group by, and the grouping is convenient rather than exact.

**Refusals are worth as much as successes.** `A00084` and `A00079` are the rows
that draw the boundary. A catalogue of successes alone teaches nobody anything.

**And the catalogue describes; it never decides.** It must not gate what the
integration sends: a stale row would take a working function away from someone,
which is precisely what failing open forbids. At runtime, capabilities
discovered from the car win. The rows are for people, for diagnosis, and for the
tested-models matrix.

Two examples of the method earning its keep. The defrost above was taken all the
way to the state field rather than stopping at "the backend accepted", which is
also what made it clear that it is a *different* function from the electric
heating of the rear glass: merging the two is the easy regression, and there is
now a test against it. And the discovery that one denied field poisons a whole
request came from two single-variable experiments with the prediction written
down first.

## Two instruments, and what each can prove

**The sandbox — no Home Assistant needed.** `sandbox/` runs the integration's real
authentication and signing code outside Home Assistant: a small GUI and a CLI over
the same core, with an isolated token, live status, point-and-click commands and
the raw JSON of every answer. It already carries single-variable experiments that
classify a response as accepted or refused by its code. You need the car, your
email and PIN, and Python — not an instance, and not a deploy.

This is the instrument for anything about the protocol: whether a command is
accepted, what a vehicle declares it can do, what a field is called. It reads
telemetry back, so it reaches layer two on its own for everything the car
reports.

*Not in this repository yet — it comes with the port of the fork line.*

**Your Home Assistant instance.** The sandbox cannot prove that an entity exists,
shows the right state, or that pressing the button in the UI reaches the car.
That path is only real in an instance, and pre-releases exist for it: turn on
*Show beta versions* for this repository in HACS.

If you have a spare machine or a container, keep a second instance for this. A
pre-release on the instance you rely on every day is a bet with your own car.

Rule of thumb, and it matches the table in `CONTRIBUTING.md`: changes to
`core/`, `platform/` or signing are proved in the sandbox; changes to entities,
state or the coordinator are proved in an instance.

## Redact before you post

No VIN, no token, no certificate, no account or user id — the last one turns up
in logs far more often than people expect. Replace with `<VIN>`, `<token>`. If in
doubt, post the shape and not the value: `"vin": "<redacted, 17 chars>"` tells us
everything we needed.

## What this produces

Not a patch. A **row of data**: this model, this region, this firmware, this
command, this outcome, this date. The integration then treats a car as data plus
capabilities discovered at runtime — so the next model is a row, not a new code
path, and the tested-models matrix is generated from the rows instead of being
kept by hand.

Which is the whole argument for writing reports rather than special cases: the
capture is specific to one car, but the *method* is universal, because the app is
universal. What generalises is not the finding. It is the procedure that produced
it.
