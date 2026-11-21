# Naming, and why the HA domain is not changing

Measured on 27 September 2026, against the Home Assistant source in the test
environment and against the real entity registry. It exists because the plan it
replaces had been on #10 for three weeks and was wrong, and the reasoning is
cheap to lose and expensive to redo.

## Four names that look like one

An entity in this integration carries four different names. They were discussed
as if they were one thing, and that is where the plan went wrong.

| # | name | example | who sees it | what breaks if it changes |
|---|---|---|---|---|
| 1 | `unique_id` | `<vin>_cmd_raffredda` | nobody, internal | HA loses the entity and creates a new, empty one |
| 2 | `entity_id` | `button.omoda9_clima_raffredda_on` | anyone writing automations or dashboards | automations, dashboards, history references |
| 3 | `translation_key` | `clima_raffredda_on` | nobody, it is a lookup | only the displayed label, and only if wrong |
| 4 | displayed name | "Cool everything" | the user | nothing, it is text |

Two things that are easy to get wrong and cost days:

- **In `button.omoda9_clima_raffredda_on`, `button` is not this integration's
  domain.** It is the entity *type*, from a fixed Home Assistant list. The
  `omoda9_` that follows is an ordinary string, written by hand in
  `button.py` (`object_id=f"omoda9_{key}"`). Home Assistant does not require it
  and does not derive it from the domain.
- **`unique_id` is `f"{vin}_{suffix}"`.** It contains neither the domain nor the
  translation key. That is what makes the renames independent of each other.

## The line that made this look impossible

`entity.py` derived the translation key from `object_id`, which defaults to
`slugify(name)` - the same Italian string the entity id is built from. Key and
entity id were one string written once.

So moving the keys to English appeared to require moving every entity id, and
moving entity ids is only free in a release that regenerates them anyway. Which
is how "the keys can only move in the domain-rename release" became the plan.

It was never a Home Assistant constraint. The key is now a declared parameter
with the derivation kept as a fallback.

## What Home Assistant actually supports, measured

Adoption across the 1,401 integrations shipped with Home Assistant:

| operation | API | integrations using it |
|---|---|---|
| rename `unique_id` **within** an integration | `async_migrate_entries` | 40 |
| rename an `entity_id` | `async_update_entity(new_entity_id=...)` | 11 |
| move entities **between** integrations | `async_update_entity_platform` | **0** |

Changing an integration's domain is the third row. The API exists and its own
docstring says it is for migrating entities between integrations. In 1,401
integrations, nobody uses it. It also refuses to run on a loaded entity
(`"Only entities that haven't been loaded can be migrated"`), which means the
migration has to happen before the old integration mounts anything - and on a
domain change HACS leaves the old folder on disk, so both versions load
together.

That is not a path to put ~30 installations with mutual-TLS certificates on.

## History follows a rename. Verified

`recorder/entity_registry.py` listens for `EVENT_ENTITY_REGISTRY_UPDATED` and,
when `old_entity_id` is present, calls:

- `async_update_statistics_metadata(hass, old, new_statistic_id=new)` - long
  term statistics;
- `async_update_states_metadata(old, new_entity_id=new)` - state history.

So graphs, history and the energy dashboard survive an `entity_id` rename.

**One way it fails, and it is silent:**

```
Cannot migrate history for entity_id `X` to `Y`
because the new entity_id is already in use
```

If the target id already exists, history is left behind and only a warning is
logged. A collision check is therefore not tidiness, it is the difference
between keeping and losing somebody's year of data. Measured on the proposed
mapping: 110 entities, **0 collisions**.

## The decision

- **The HA domain stays `omoda9`.** With it the folder
  `custom_components/omoda9/` and the certificate directory
  `f"{DOMAIN}_{vin}_certs"`, which therefore does not move and does not need
  re-provisioning.
- **The repository is renamed** to `chery-connect`. GitHub redirects, HACS
  follows the redirect, nobody does anything.
- **`entity_id` and `unique_id` move to English**, in a release that carries
  nothing else, with the registry rewritten automatically at first start.
- **The manifest `name` becomes the brand.** That is the string the user
  actually reads; the domain appears only in a folder path and a settings URL.

If Home Assistant one day offers a real path for changing an integration's
domain, we take it. Until then the folder name is the price, and it is the
cheapest thing on this page.

## The English names were not invented

All 110 entities already had an English name in `translations/en.json`, written
and reviewed when somebody translated them. Slugifying those names produces the
new ids: 110 out of 110 available, 0 collisions. The expensive part of this
migration - choosing 110 names - had already been paid.

## Migrating from the other line

Users coming from the `omoda_jaecoo` line are a different case, because that is
a domain change for them whatever we do.

Comparing `unique_id` suffixes with the VIN stripped:

| | |
|---|---|
| suffixes **identical** on both lines | 83 |
| canonical only | 27 |
| `omoda_jaecoo` only | 18 |

The 83 match because the suffix is usually the Chery API field name
(`chargeGunState`, `engineState`, `airPurification`) - language-neutral by
accident, and the reason most of this is cheap.

The divergence is roughly 15 pairs where the suffix was written in the
developer's language on each side: `rt_alta_tensione` against
`rt_high_voltage_active`, `cmd_localizza` against `cmd_locate_car`,
`clima_durata` against `climate_duration`. Those need an explicit map. The
contamination runs both ways: the `omoda_jaecoo` line carries three Italian
suffixes of its own.

**One entity cannot be migrated at all:** `cover.finestrini` here against
`select.windows_select` there. Different entity types for the same function, and
history is not portable between types. It is one out of 110, and it is declared
rather than discovered.

Certificates for people arriving from that line: fill in `certs_src` at setup
with the old directory and `_provision_certs` copies them across. There is no
manual file move.
