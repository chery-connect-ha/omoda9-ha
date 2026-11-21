# Moving to Chery Connect (2.0)

> [!WARNING]
> **On hold: do not follow this guide yet.** Step 1 does not work: HACS refuses to update an integration whose domain changes, and offers to delete the configured `omoda9` entry instead, which deletes its entities and device. The path is being reworked; see [#10](https://github.com/chery-connect-ha/omoda9-ha/issues/10).

From 2.0 this integration installs under its final name, **Chery Connect**, with the Home
Assistant domain `chery_connect`. Every vehicle moves to it, whether it runs today on the
`omoda9` integration (this repository, up to 1.14) or on the older `omoda_jaecoo` line.

For Home Assistant a new domain is a new integration. Updating in HACS installs it **next
to** the old one and leaves the old one running, so the move is a step you confirm once. It
reuses your login, so no new code arrives by e-mail or text message, and it carries your
entities, their history and the device across.

## Before you start

- **Be on a version that has the bridge**: `omoda9` 1.14.0-beta.15 or later, or
  `omoda_jaecoo` 1.8.1 or later. The bridge is what shows Chery Connect as discovered. Without
  it the move still works, from "Add integration" (step 3 below), you just will not be
  prompted.
- **A backup of Home Assistant** is good practice before any update that moves entities.

## The move

1. **Update in HACS** to 2.0, then **restart Home Assistant**. HACS writes the new folder
   `custom_components/chery_connect` and leaves the old one where it is.
2. **Open Settings, Devices and services.** Chery Connect is listed as **Discovered**, and
   Settings shows a notice about it. Press **Add**.
3. *(If nothing is discovered: press **Add integration**, search for Chery Connect, and pick
   **Move a vehicle from the old integration**. It is the same step.)*
4. **Read the confirmation and press Submit.** In that moment:
   - the old integration is **disabled** for that vehicle, so the two never talk to the car at
     the same time;
   - a Chery Connect entry is created with the same login, PIN and options.
5. **Chery Connect starts**, and on that first start it moves, in this order:
   - the session token, the mutual-TLS certificates and the task id, **copied** next to its own
     (the originals stay, so the old integration could still start if re-enabled);
   - the **entities**, with their unique id, entity id and history;
   - the **device**, with its id, so automations that use the device keep working.
6. **Settings shows a notice**: how many entities moved, how many could not (the log names each
   one and why), and the last step.

## The last step: remove the old integration

When you are satisfied that everything works:

1. Settings, Devices and services, the old integration (`omoda9` or `omoda_jaecoo`): **delete**
   its entry. It is disabled and owns nothing any more.
2. In HACS, remove the old repository if it is still listed, and delete the folder
   `custom_components/omoda9` (or `custom_components/omoda_jaecoo`) if it is still there.
   HACS does not remove a folder whose domain is no longer in the manifest.
3. Restart Home Assistant.

## What changes, by where you come from

**From `omoda9`:** entity ids do not change (they are already `sensor.chery_connect_...`), and
neither do unique ids, so history does not even move: it stays where it is. If you skipped
1.14 and still have Italian ids (`sensor.omoda9_batteria`), they are renamed to English on the
same first start, as in 1.14, with the history following them.

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

The old integration is only **disabled**, never deleted by the move, and its files are copied,
not moved, so it can be turned back on from its menu. Going back has not been tried yet on a
real installation: if you need it, say so in an issue before doing it, so we can do it with you.

Either way, open an issue with the log lines that start with `chery_connect: moved from`: they
list every entity that did not move and why.
