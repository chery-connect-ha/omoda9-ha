# Moving to Chery Connect (2.0)

From 2.0 this integration installs under its final name, **Chery Connect**, with the Home
Assistant domain `chery_connect`. Every vehicle moves to it, whether it runs today on the
`omoda9` integration (this repository, up to 1.14) or on the older `omoda_jaecoo` line.

For Home Assistant a new domain is a new integration, and the Marketplace treats it that way:

- it **refuses to update** an installed integration to a version with another domain ("changed
  its domain ... uninstall it and install it again");
- it **refuses to remove** an integration while it is still configured, and offers to delete the
  configuration for you.

> [!WARNING]
> **Never let the Marketplace delete the configuration for you**, and never delete the old entry
> by hand before the move. Deleting the entry deletes its entities and the device, which is
> exactly what the move carries over. If the Marketplace shows that dialog, close it.

So the move goes in two halves: the old integration hands the vehicle over, then the Marketplace
swaps the code. It reuses your login, so no new code arrives by e-mail or text message, and it
carries your entities, their history and the device across.

## From `omoda9` (this repository)

Tried on a real installation on 21 November 2026 (Home Assistant 2026.11.2, Marketplace): every
entity moved with its entity id and history, the device kept its id, the session was reused.

### First half: hand the vehicle over

1. **Update Omoda 9 / Jaecoo** in the Marketplace to a version with the handover:
   `1.14.0-beta.16` or later. Restart Home Assistant.
2. **Open Settings, Repairs.** A notice says "*your car*: move this vehicle to Chery Connect".
   Open it, read the confirmation and press **Submit**. In that moment:
   - a Chery Connect entry is created with the same login, PIN and options;
   - the session token, the mutual-TLS certificates and the task id are **copied** next to the
     old ones;
   - the **entities** move to it, with their unique id, entity id and history, then the
     **device**, with its id, so automations that use the device keep working;
   - the old entry is removed: it is empty by then.
3. A second notice, "**Chery Connect: finish the move in the Marketplace**", says how many entities
   moved and lists the second half.

From here until the end of the second half **the car is not updated**: the Chery Connect entry
shows as not loaded, because its code is not installed yet. That is expected.

### Second half: swap the code in the Marketplace

4. **Marketplace, Omoda 9 / Jaecoo: Remove.** It is allowed now, without any dialog, because no
   `omoda9` entry is left.
5. **Same card: download Chery Connect 2.0.** While 2.0 is a beta, turn on *Show beta versions*
   first. If the card is gone, add `chery-connect-ha/omoda9-ha` again as a custom repository of
   type Integration.
6. **Restart Home Assistant straight away.** Right after the download Home Assistant may ask you to
   log in again: **do not**. After the restart Chery Connect starts with the login it already
   has, and the request goes away.

Chery Connect starts with your entities, history and device. The notice of step 3 goes away by
itself from `2.0.0-beta.2`; on `2.0.0-beta.1` you can dismiss it.

## From `omoda_jaecoo` (the older line)

Not yet tried on a real installation through the Marketplace: if you are on this line, wait for
the call on [#10](https://github.com/chery-connect-ha/omoda9-ha/issues/10).

Here the Marketplace does not get in the way: Chery Connect comes from another repository than
the one you have installed, so it installs next to it.

1. In the Marketplace, add `chery-connect-ha/omoda9-ha` as a custom repository of type
   Integration, download Chery Connect 2.0 (with *Show beta versions* while it is a beta) and
   restart Home Assistant.
2. **Settings, Devices and services.** With `omoda_jaecoo` 1.8.1 or later Chery Connect is listed
   as **Discovered**: press Add. Otherwise press **Add integration**, search for Chery Connect and
   pick **Move a vehicle from the old integration**.
3. **Read the confirmation and press Submit.** The old entry is disabled, so the two never talk to
   the car at the same time, and a Chery Connect entry is created with the same login and PIN. On
   its first start it copies the session files and moves the entities, then the device.
4. When everything works: delete the old, disabled entry in Devices and services (it owns nothing
   any more), then remove Omoda / Jaecoo in the Marketplace, and restart.

## What changes, by where you come from

**From `omoda9`:** entity ids do not change (they are already `sensor.chery_connect_...`), and
neither do unique ids. If you skipped 1.14 and still have Italian ids (`sensor.omoda9_batteria`),
update to 1.14 first: it renames them to English, with the history following them.

**From `omoda_jaecoo`:** 96 of the 101 entities move with their history, renamed to English
(`sensor.battery` becomes `sensor.chery_connect_battery`). Five cannot move, and the reason is
the same each time: on the old line they were a different kind of entity, and history does not
carry between kinds.

| Old entity | Why it does not move |
|---|---|
| windows (`select`) | here they are a `cover` |
| charging (`binary_sensor`) | here it is a `switch` |
| WLTP range, electric efficiency, charging power | only on the old line; Chery Connect has its own where the car sends them |

## What you fix by hand

- **Automations and scripts that call a service** of the old integration: `omoda9.xxx` becomes
  `chery_connect.xxx`.
- **The bundled blueprints**: re-import them from `blueprints/automation/chery_connect/`.
- **From `omoda_jaecoo` only**: automations, scripts and dashboard cards that name an entity in
  text, because those names changed.

Device automations and everything that refers to an entity through the user interface keep
working.

## If something goes wrong

Going back has not been tried on a real installation. If you need it, say so in an issue before
doing anything, so we can do it with you: in particular, do not delete the Chery Connect entry,
because that deletes the entities it now holds.

Either way, open an issue with the log lines that start with `omoda9: handed over` or
`chery_connect: moved from`: they list every entity that did not move and why.
