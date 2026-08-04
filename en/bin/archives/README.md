# Archive Tools (MVP)

This directory contains the **archive management tools** for SAT.

These tools are responsible for **creating and initializing archives** based on explicit YAML definitions. They do not manage content, language, or publication.

---

## Purpose

The archive tools exist to:

- initialize a new archive from a definition file
- create directory structures only
- keep archive creation explicit and auditable

They are intentionally simple and deterministic.

---

## Key Files

### `archive`

Command-line dispatcher for archive-related subcommands.

Example:

```
archive init --archive-definition-path archive-definition.yml
```

---

### `archive-init.py`

Implements archive initialization.

Responsibilities:

- read an archive definition
- read an archives parent definition
- create directories only
- emit minimal user-facing output

---

### `config/archives-parent.yml`

Defines where archives are created relative to the project root.

Example:

```yaml
archives:
  root: "archives"
```

---

## Archive Definitions

Archive structure is defined in an **archive definition file**, typically named:

```
archive-definition.yml
```

This file defines:

- the archive name
- the directory tree to create under `en/docs/`

---

## Design Principles

- no implicit behavior
- no positional arguments
- no magic paths
- no SAT ownership of archives
- tools are language-specific, archives are not

---

## Status

This directory represents the **MVP archive initialization tooling**.

The interface and semantics are considered **locked**.

Further work should build on this foundation without changing its core behavior.
