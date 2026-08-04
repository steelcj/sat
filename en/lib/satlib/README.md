# satlib

Shared Python library for Source Archive Tools (SAT). satlib is the single source of truth for behaviour shared across the sat, collection, archive, and content tier executables. Tier CLIs are thin wrappers over these functions. Permission delegation remains a filesystem concern (ADR-004) and is not enforced here — satlib is shared plumbing, not a permission surface.

Design rationale, module responsibilities, and the table of implementation interpretations pending ratification live in [satlib Design and Rationale](../../docs/architecture/satlib-design-and-rationale-v0-3-1.md).

## Layout

```text
sat/en/lib/
└── satlib/                     # project root: the pip install target
    ├── pyproject.toml
    ├── README.md
    ├── satlib/                 # the importable package
    │   ├── __init__.py
    │   ├── registry.py         # cached external authority sources (spec §2)
    │   ├── language.py         # BCP 47 validation, derivation, sat:authority (spec §1, §3, §4)
    │   ├── iso639.py           # embedded ISO 639-1 → 639-2/T derivation table
    │   ├── assets.py           # universal assets directory convention (ADR-018)
    │   ├── cascade.py          # metadata cascade, <calculated> tripwire
    │   ├── discovery.py        # tool self-discovery walk (ADR-005)
    │   └── archive.py          # archive creation: plan/create, immutability
    └── tests/
        ├── test_registry.py
        ├── test_language.py
        ├── test_assets.py
        ├── test_cascade.py
        ├── test_discovery.py
        └── test_archive.py
```

## Installation

satlib is installed into the per-version venv managed by `osat-fluent-sat-tool` as part of artifact installation:

```bash
pip install "$SAT_TOOL_ROOT/en/lib/satlib/"
```

For development, create a virtual environment first. Modern Debian-family systems mark the system Python as externally managed (PEP 668) and refuse bare `pip install`; the venv is required, not optional, and mirrors how satlib runs in production — one venv per installed version.

```bash
cd sat/en/lib/satlib
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[test]"
```

`.venv/` is development state: never commit it and never ship it in the artifact.

Requires Python 3.10 or later. The only runtime dependency is PyYAML.

## Running the test suite

From `sat/en/lib/satlib`, with the development venv active:

```bash
python -m pytest
```

Example output — illustrative only; test counts and files grow with the library:

```text
====================== test session starts ======================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0
rootdir: /home/initial/2-areas/development/sat/en/lib/satlib
configfile: pyproject.toml
testpaths: tests
collected 109 items

tests/test_archive.py ..............                        [ 12%]
tests/test_assets.py ................................       [ 42%]
tests/test_cascade.py ..................                    [ 58%]
tests/test_discovery.py ...........                         [ 68%]
tests/test_language.py .......................              [ 89%]
tests/test_registry.py ...........                          [100%]
====================== 109 passed in 0.35s ======================
```

`pyproject.toml` sets `testpaths = ["tests"]`, so no arguments are needed. To run against an installed artifact rather than a checkout:

```bash
"$SAT_TOOL_ROOT/venv/bin/python" -m pytest "$SAT_TOOL_ROOT/en/lib/satlib/tests"
```

The suite is self-contained: it uses a fixture registry and an injected fetcher, so no network access and no real IANA registry file are required.

## Governing documents

- ADR-001: Language as Filesystem Structure
- ADR-002: Mixed Language Archive Naming Convention
- ADR-003: IANA Language Subtag Registry as Authoritative Source
- ADR-004: Self-Replicating Permission Model
- ADR-005: Tool Self-Discovery from Filesystem Context
- ADR-018: Universal Assets Directory Convention
- SAT Language Validation and Offline Registry Cache Specification v0.1.0
- satlib Design and Rationale v0.1.0
