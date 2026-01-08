---
Title: "SAT Matryoshka Architecture (MVP)"
Description: "Defines the concrete, non-metaphorical Matryoshka architecture used by SAT, establishing strict containment, ownership, and independence rules between SAT, archives, and content."
Author: "Christopher Steel"
License: "CC BY-SA 4.0"
---

# SAT Matryoshka Architecture (MVP)

## Reality Check

These are the goals and reasons behind our semantically based archive layout. This does not mean that everything in this list is working and or completed. Most have been tested using beta like tools but a number of tools and configuration files need to be created in order to reach our goals. This gives us the architecture to do so in a way that places human languages at the forefront vs. a "translation" added later...

## Purpose

This document defines the **authoritative structural architecture** of SAT using a **Matryoshka (nested system) model**, applied *literally* rather than metaphorically.

The goal of this architecture is to ensure that:

- Each layer is **complete and functional on its own**
- Outer layers may create inner layers, but **never become dependencies**
- Inner layers can be **copied, moved, or published independently**
- Physical directory structure directly encodes system boundaries

This document establishes **non-negotiable invariants** for SAT development.

---

## Core Principle (Normative)

> **Each SAT layer is a complete system that may contain another system,  
> but never depends on any system outside itself.**

This is not conceptual guidance.  
It is a **structural contract** enforced by filesystem layout.

---

## Layer Overview

SAT consists of **three concrete layers**, each with a fixed responsibility boundary:

1. SAT Container (system controller)
2. Archive (meaning container)
3. Content (payload)

Each layer is represented by a **directory root**.

---

## Layer 1: SAT Container

### Definition

The **SAT container** is the outermost system.
It exists to **create, initialize, and validate archives**.

It is not required once an archive has been created.

### Canonical Layout

```text
sat/
└── en/
    ├── docs/
    └── bin/
        └── sat/
            ├── sat
            └── config/
                ├── sat.yml
                └── discovery.yml
```

### Properties

- Owns SAT system tools
- Owns SAT configuration
- Contains SAT self-documentation
- May be deleted without affecting any archive
- Never embeds itself inside an archive

### Authority Boundary

The SAT container **may act on archives**, but archives **must not depend on SAT**.

## Layer 2: Archive

### Definition

An **archive** is a complete, portable system whose purpose is to **hold meaning**.

Archives may be created by SAT, but are **not owned by SAT** once created.

### Canonical Layout

```text
my-archive/
└── en/
    ├── docs/
    └── bin/
        └── archive/
            ├── archive-validate
            ├── archive-build
            └── config/
                └── sat-archive.yml
```

### Properties

- Owns its own tools
- Owns its own configuration
- Contains all meaningful material under `docs/`
- Can exist, function, and be published without SAT
- Is portable by simple file copy

### Authority Boundary

An archive **must never call SAT tools**.  
Archive tools operate only on archive-local state.

## Layer 3: Content

### Definition

**Content** is the payload of an archive.

It is not executable and has no awareness of tooling.

### Canonical Location

```text
en/docs/
```

### Properties

- Contains all meaningful material
- May be published, rendered, or transformed
- Has no configuration of its own
- Must not depend on SAT or archive tools

Content is **pure data + meaning**.

---

## Configuration Placement Rule (Invariant)

> **Configuration always lives with the tools that execute it.**

Therefore:

| Configuration         | Location                         |
| --------------------- | -------------------------------- |
| SAT configuration     | `sat/en/bin/sat/config/`         |
| Archive configuration | `archive/en/bin/archive/config/` |
| Content configuration | None                             |

This rule is mandatory.

---

## Archive Independence Test (Normative)

An archive is considered **correctly implemented** if:

- The archive directory can be copied alone
- SAT is completely absent
- Archive tools still function
- Content remains intact and publishable

If removing SAT breaks an archive, the architecture is incorrect.

---

## Implications for Tooling

### SAT Tools

- Controllers only
- One-time or occasional use
- Never required at archive runtime

### Archive Tools

- Local to the archive
- Operate only within the archive boundary
- May be distributed with the archive

### Content

- Tool-agnostic
- Immutable by default
- Always safe to copy or publish

---

## Explicit Non-Goals (MVP)

This architecture explicitly excludes:

- Global archive registries
- SAT-managed runtime dependencies
- Filesystem scanning or discovery
- Implicit archive registration
- Hidden coupling between layers

All such behavior must be layered **above** this model, not within it.

---

## Summary

- SAT uses a **literal Matryoshka architecture**
- Each layer is a complete system
- Outer layers may create inner layers, but never persist within them
- Physical structure enforces conceptual boundaries
- Independence is provable by file copy

This architecture is foundational and must remain stable.

---

## License

This document, *SAT Matryoshka Architecture (MVP)*, by **Christopher Steel**, with AI assistance from **ChatGPT (OpenAI)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).

![CC License](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)