# What you have to do, depending on where you are coming from

Two different situations, and they are not the same amount of work. Find yours.

## You already have this integration (domain `omoda9`)

**Three steps, and the third one is optional.**

1. Update in HACS.
2. Restart Home Assistant.
3. Read the notice that appears in Settings and fix your own automations.

That is the whole procedure. **Do not uninstall anything**, do not remove the
integration, do not log in again. The folder, the config entry and the mutual-TLS
certificates all stay where they are.

**What happens on that restart.** Every entity is renamed from its Italian id to
an English one: `sensor.omoda9_batteria` becomes
`sensor.chery_connect_battery`. The integration does it itself, before anything
is loaded.

**Your history comes with it.** Home Assistant moves long-term statistics and
state history when an entity is renamed through the registry. Graphs, the energy
dashboard and the logbook follow. Nothing to export, nothing to rebuild.

**What does not come with it: anything you typed yourself.** An automation,
script, template sensor or dashboard card that names an entity in text still
points at a name that no longer exists. Home Assistant shows those as unknown
entities.

**How to find yours** - this is the part people get stuck on, so it is answered
rather than left as an exercise:

- a notice appears in **Settings -> Devices & services -> Repairs**, saying how
  many entities were renamed on your vehicle;
- **Settings -> Automations & scenes**: an automation referring to a missing
  entity is flagged there;
- **Settings -> Dashboards**: a card pointing at nothing renders as an error;
- the complete old-to-new list is in [`entity-id-rename.md`](entity-id-rename.md).
  If you keep your automations in YAML, one search and replace per line does it.

Dismiss the notice when you are through. It will not come back.

## You are coming from the `omoda_jaecoo` line (JackRonan's fork)

For Home Assistant that line is a **different integration**: different domain,
different folder, different entities. So this is a fresh setup, not an update.

**But your history can come across.** That was not true when this document was
first written and it is true now: two actions do it, and both were run on a real
pair of installations before this was written.

### The order that costs you the least

1. **Install this integration from HACS.** It lands beside your existing one, in
   its own folder. Nothing of yours is touched yet.
2. **Add it** in *Settings -> Devices & services -> Add integration*. You log in
   from scratch: this is a different integration and it has no session.
3. **When the form asks for `certs_src`, give it your old certificate folder** -
   `/config/omoda_jaecoo_<VIN>_certs`, the path as Home Assistant sees it, not
   as your file manager sees it. The integration copies the certificates itself.
   Do not move files by hand.
4. **Check the car appears** and the entities have values.
5. **Disable the old integration** (its menu, *Disable*). Do not delete it yet.
6. **Recover your history**, below.
7. **Rebuild what refers to entities by name**, below.
8. **Only then** delete the old integration.

### Recovering the history

Two actions in *Developer tools -> Actions*. Both default to a **dry run** that
changes nothing and reports what it would do. Run the dry run, read the result
in *Settings -> System -> Logs*, and only then run it for real.

**If the old integration is still installed** (step 5 above): disable it first,
then call **Adopt entities from the omoda_jaecoo installation**. It takes over
the old entities themselves, with everything attached to them.

**If you already deleted the old integration** - the common mistake, and there
is no need to reinstall it - call **Recover history from a removed omoda_jaecoo
installation**. Deleting an integration removes its entities from the registry;
it does not delete the data. Home Assistant still remembers every entity it
removed, and that is enough to put the statistics and the history back on the
new entities.

**What comes across, measured on a real migration:** 20 statistics series and 96
state histories, including both charging-energy counters, the odometer, the
battery, the ranges and the eight tyre series. Two months of continuous data in
that case.

**What cannot, and why:** five entities. Three exist only on the old line. Two
were built as different kinds of entity on the two lines - the windows are a
`cover` here and a `select` there, charging is a `switch` here and a
`binary_sensor` there - and history is not portable between entity types. The
report names them.

**There is a clock.** The recorder eventually purges orphaned data. Days, not
hours, but do not leave it for a month.

### Two things that will look broken, and are not the integration

**Custom cards stop working**, and it is worth knowing why before you conclude
something is wrong. A card that names entities in its configuration still points
at the old names. Worse, a card that relies on its own built-in defaults points
at them silently: it loads, and controls nothing. If you wrote or installed a
card for the old line, open its configuration and check every entity id in it,
and if it has defaults in its source, check those too.

**Dashboards and automations** that name an entity in text keep pointing at the
old name. The full old-to-new list is in
[`entity-id-rename.md`](entity-id-rename.md); one search and replace per line.

### One thing to plan around

Two installations can coexist, but **two logins cannot**: the manufacturer's
backend allows one session per account, so while the new integration holds it
the old one is logged out. Plan it as a switch, not as a side-by-side trial.
