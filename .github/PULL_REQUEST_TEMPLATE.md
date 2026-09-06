## What changes, and why

<!-- One behaviour per pull request. If this touches many files to do one thing,
     say so — that is information about the architecture, not about you. -->

Closes #

## Evidence

Fill in the row that applies and delete the others. Being honest here costs
nothing; overstating it is the only mistake in this project that reaches a
stranger's car.

- [ ] **Verified on hardware** — I own this car and I watched it act.
      Car / region / version:
      Sent at:                          Observed at:
      State field that changed:
      <!-- The protocol, and why the backend answering OK is not enough:
           docs/field-test.md -->

- [ ] **Backend only** — the request was accepted, I did not confirm the car
      acted. Say what stopped you.

- [ ] **Not testable by me** — written for a model I do not own. This is fine;
      add the `unverified-hardware` label and, if you know who has that car,
      `needs-field-test:<model>`.

- [ ] **No runtime behaviour** — docs, tests, CI, refactor with no user-visible
      change.

## Checks

- [ ] Suite green (`pytest tests/ -q`, or CI if the local Python is older than 3.13)
- [ ] Entity count unchanged, or the change is deliberate and named above
- [ ] No VIN, token, certificate, account id or raw capture anywhere in the diff
- [ ] Fails open: nothing here can take away a function that worked for somebody
- [ ] Design docs updated if this contradicts them
