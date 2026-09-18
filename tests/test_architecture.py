"""Architectural gate — a ratchet, not a checklist.

Every rule in this file was true when it was added, and must stay true forever.
The contract is deliberately one-way:

  * a rule enters this file in the *same commit* that makes it true;
  * a rule is never weakened or removed to make a change pass.

That is what lets an existing codebase converge on the target architecture
described in ``docs/design/architecture.md`` without a big-bang rewrite: each
extraction slice lands with one new assertion, and CI stops the code from
drifting back.

Rules that are NOT here yet, and the slice that will add them (see
``docs/design/architecture.md`` for the full plan):

  slice 1  ``paho`` may only be imported from ``transport/``
           (today: __init__.py, coordinator.py, diag.py)
  slice 2  ``requests``/``ssl``/``socket`` may only be imported from
           ``platform/`` and ``transport/``
           (today: coordinator.py, config_flow.py and six ``core/`` modules)
  slice 3  ``domain/`` may not import Home Assistant nor the network
  slice 4  entity platforms may only import ``features/`` and ``domain/``
           (today: button.py reaches into ``core.commands``)

The checks are static: the file is parsed, never imported, so this suite runs
without Home Assistant installed — the same constraint the rest of the suite
already lives under.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _component_dir() -> Path:
    """The integration package, found by shape rather than by name.

    The domain is going to be renamed; hard-coding it here would turn a rename
    into a red build for the wrong reason.
    """
    candidates = [
        p
        for p in (REPO_ROOT / "custom_components").iterdir()
        if p.is_dir() and (p / "manifest.json").exists()
    ]
    assert len(candidates) == 1, f"expected exactly one integration, found {candidates}"
    return candidates[0]


COMPONENT = _component_dir()
CORE = COMPONENT / "core"

# The Home Assistant-facing modules: one per platform HA knows about. These are
# the only files allowed to speak HA's entity language, and the last place that
# should ever open a socket.
ENTITY_PLATFORMS = (
    "binary_sensor.py",
    "button.py",
    "climate.py",
    "cover.py",
    "device_tracker.py",
    "lock.py",
    "number.py",
    "select.py",
    "sensor.py",
    "switch.py",
    "text.py",
    "time.py",
)

NETWORK_ROOTS = {"paho", "requests", "ssl", "socket", "urllib", "http"}


def _imported_roots(path: Path) -> set[str]:
    """Top-level module names imported by ``path``, function-local ones included.

    Deferred imports inside a function are still imports: they are exactly how
    layering violations hide from a grep, so the AST walk covers the whole tree.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import — recorded separately below
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _relative_targets(path: Path) -> set[str]:
    """First component of every relative import in ``path`` (``from .x import y``)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            targets.add(node.module.split(".")[0])
    return targets


def _core_modules() -> list[Path]:
    return sorted(CORE.rglob("*.py"))


# ─────────────────────────────────────────────────────────────────────────────
# Rule 1 — core/ is Home Assistant-free.
#
# This is the rule the whole test suite rests on: `core/` can be exercised
# without Home Assistant installed. It is also what makes the protocol logic
# reusable across platforms (see docs/design/architecture.md).
# ─────────────────────────────────────────────────────────────────────────────
def test_core_does_not_import_home_assistant() -> None:
    offenders = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in _core_modules()
        if "homeassistant" in _imported_roots(p)
    ]
    assert not offenders, (
        "core/ must stay free of Home Assistant imports so it can be tested and "
        f"reused outside HA; offending files: {offenders}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 2 — entity platforms never talk to the network directly.
#
# An entity module renders state and forwards intent. The moment one of them
# opens its own connection, the transport stops being swappable and the vehicle
# state has two sources of truth.
# ─────────────────────────────────────────────────────────────────────────────
def test_entity_platforms_do_not_touch_the_network() -> None:
    offenders: dict[str, set[str]] = {}
    for name in ENTITY_PLATFORMS:
        path = COMPONENT / name
        if not path.exists():
            continue  # platforms differ per line; absence is not a violation
        leaked = _imported_roots(path) & NETWORK_ROOTS
        if leaked:
            offenders[name] = leaked
    assert not offenders, (
        "entity platforms must go through the coordinator, never the network: "
        f"{offenders}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rule 3 — core/ does not import the entity platforms.
#
# Dependencies point one way: HA-facing code may lean on the protocol code, and
# never the reverse. Without this, `core/` silently becomes un-testable again.
# ─────────────────────────────────────────────────────────────────────────────
def test_core_does_not_import_entity_platforms() -> None:
    platform_names = {name[: -len(".py")] for name in ENTITY_PLATFORMS}
    offenders: dict[str, set[str]] = {}
    for path in _core_modules():
        leaked = _relative_targets(path) & platform_names
        if leaked:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = leaked
    assert not offenders, f"core/ must not depend on HA entity modules: {offenders}"


# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — const.py stays a leaf.
#
# Constants and the small pure helpers beside them are imported by everything;
# the moment const.py imports back into the component, every import becomes a
# potential cycle.
# ─────────────────────────────────────────────────────────────────────────────
def test_const_is_a_leaf_module() -> None:
    const = COMPONENT / "const.py"
    assert const.exists(), "const.py is expected at the component root"
    assert not _relative_targets(const), (
        "const.py must not import other modules of the component — it is a leaf "
        f"imported by all of them; found: {_relative_targets(const)}"
    )
