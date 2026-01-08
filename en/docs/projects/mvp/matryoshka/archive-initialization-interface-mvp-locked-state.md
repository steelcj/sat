---
 Title: "Archive Initialization Interface (MVP – Locked State)"
Description: "Authoritative, frozen definition of the archive initialization interface, semantics, and responsibilities."
Author: "Christopher Steel"
License: "CC BY-SA 4.0"
---

# Archive Initialization Interface (MVP – Locked State)

This document records the **authoritative state** of the archive initialization design.  
This state is frozen to prevent further bikeshedding or silent semantic drift.

---

## Canonical Names (Final)

### Archive Definition (what to create)

```
archive-definition.yml
```

This file defines:
- the archive name
- the directory structure to be created

---

### Archives Parent Definition (where to create it)

```
archives-parent.yml
```

This file defines:
- the parent directory under which archives are created

---

## Canonical CLI (Final)

```
archive init \
  --archive-definition-path <archive-definition.yml> \
  [--archives-parent-definition-path <archives-parent.yml>]
```

- `--archive-definition-path` is required
- `--archives-parent-definition-path` is optional

Default for `--archives-parent-definition-path`:

```
bin/archives/config/archives-parent.yml
```

There are:
- no positional arguments
- no implicit guessing
- no ambiguity

---

## Canonical Directory Resolution (Final)

Given tool location:

```
<project-root>/bin/archives/
```

Resolution rules:

1. The tool determines the **project root**:

   ```
   bin/archives → bin → project-root
   ```

2. The tool reads the archives parent definition:

   ```yaml
   archives:
     root: "archives"
   ```

3. The archive is created at:

   ```
   <project-root>/<archives.root>/<archive-name>/en/docs/...
   ```

Archives are:
- never created in `bin/archives`
- never created relative to the current working directory
- never owned or embedded inside SAT itself

---

## Canonical Tool Responsibilities (Final)

### `archive-init.py`

Responsibilities:
- read the archive definition
- read the archives parent definition
- create directory structures only
- emit minimal, explicit user-facing messages

Non-responsibilities:
- language management
- tool installation
- content creation
- archive discovery

---

### `archive` (Dispatcher)

Responsibilities:
- parse CLI arguments
- route `archive init` to `archive-init.py`
- own command-line UX only

---

## Language Policy (Final)

- Language belongs to tools, not archives
- Manual translation is acceptable
- Future optional i18n may use simple YAML dictionaries
- No gettext or opaque frameworks

---

## Status

- Semantics corrected
- Path resolution fixed
- Naming clarified
- CLI stabilized
- Future-forward without overengineering

This interface is now stable.  
You may safely:

- commit
- tag the MVP
- continue development without reopening these decisions

---

## License

This document, *Archive Initialization Interface (MVP – Locked State)*, by **Christopher Steel**, with AI assistance from **ChatGPT (OpenAI)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).

![CC License](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)
