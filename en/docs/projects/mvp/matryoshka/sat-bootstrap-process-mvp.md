---
Title: "SAT Bootstrap Process (MVP)"
Description: "Defines the minimal, two-phase bootstrap and initialization process for installing and using SAT."
Author: "Christopher Steel"
Path: en/docs/projects/mvp/matryoshka/sat-bootstrap-process-mvp.md
License: "CC BY-SA 4.0"
---

# SAT Bootstrap Process (MVP)

## Purpose

This document defines the **minimal and authoritative process** for bringing SAT from **zero** to a **working, permanent installation**, without ambiguity between bootstrap, installation, and initialization responsibilities.

This process is intentionally simple and mirrors proven infrastructure patterns (e.g., ephemeral tooling used to create permanent systems).

---

## Scope

This document covers:

- How SAT is bootstrapped from nothing
- How the first permanent SAT installation is created
- What `sat init` does and does not do

This document does **not** cover:

- SAT-managed archive creation
- Content creation
- Publication workflows
- Tool discovery beyond SAT system tools

---

## High-Level Overview

SAT setup occurs in **two distinct phases**:

1. **Bootstrap (ephemeral)**
2. **Initialize (permanent)**

These phases must remain separate.

---

## Phase 0: SAT Bootstrap (Ephemeral)

### Goal

Provide a **temporary execution environment** capable of creating the first permanent SAT installation.

### Mechanism

- A script (e.g. `bootstrap-sat.sh`) is downloaded and executed
- The script creates a **Python virtual environment**
- SAT requirements are installed into that venv
- The venv exposes `sat-init`

### Resulting State (Example)

```text
~/.venvs/sat/
├── bin/
│   ├── python
│   └── sat-init
└── lib/
```

### Characteristics

- The venv is **not** a SAT container
- No SAT directories are created
- The environment is disposable
- The only responsibility is to provide `sat-init`

---

## Phase 1: SAT Initialization (Permanent)

### Goal

Create the **first permanent SAT container** on disk.

### Command

```bash
sat-init /path/to/sat
```

(Executed from the bootstrap venv)

---

## Files Created by `sat-init`

`sat-init` creates the **minimal SAT system layout**:

```text
/path/to/sat/
└── en/
    ├── bin/
    │   └── sat/
    │       ├── sat
    │       ├── sat-init.py
    │       └── config/
    │           ├── sat.yml
    │           └── discovery.yml
    └── docs/
```

### Notes

- `/path/to/sat` is the **SAT container**
- `en/docs/` is the **SAT self-documentation archive**
- `bin/sat/` is **system-owned and immutable**
- `sat-init` copies SAT system tools into the permanent location
- After this step, the bootstrap venv may be deleted

---

## What `sat init` Means After Installation

Once a permanent SAT container exists:

- `sat init` refers to **initializing a SAT workspace**
- It may:
  - Verify SAT container structure
  - Create missing workspace directories
- It does **not**:
  - Install SAT
  - Modify `bin/sat/`
  - Create SAT-managed archives

---

## Explicit Non-Responsibilities

`sat init` does **not**:

- Create SAT-managed archives
- Create content
- Name projects
- Install or upgrade SAT itself

SAT-managed archive creation is always handled by **archive-level tools**, explicitly and separately.

---

## Invariants (MVP)

- SAT bootstrap tooling is external to SAT
- `sat-init` is authoritative for creating a permanent SAT container
- SAT system tools never modify themselves
- SAT self-documentation is a special, system-owned archive
- SAT-managed archives are created explicitly and separately

---

## Summary

- **Bootstrap** provides tools
- **`sat-init`** creates the SAT container
- **SAT** creates SAT-managed archives later, explicitly

This separation is intentional and foundational.

---

## License

This document, *SAT Bootstrap Process (MVP)*, by **Christopher Steel**, with AI assistance from **ChatGPT (OpenAI)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).

![CC License](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)
