---
Title: "SAT Bootstrap Process (MVP – Fast Manual Path)"
Description: "Defines the minimal, manual process for creating a working SAT installation by directly creating required system files and directories."
Author: "Christopher Steel"
Path: en/docs/projects/mvp/matryoshka/sat-bootstrap-process-mvp-fast-manual-path.md
License: "CC BY-SA 4.0"
---

# SAT Bootstrap Process (MVP – Fast Manual Path)

## Purpose

This document defines the **fastest authoritative path** to a working SAT installation by **manually creating** the SAT system directory structure and required files.

This approach intentionally avoids bootstrap scripts and automation in order to:

- Unblock progress immediately
- Preserve clear responsibility boundaries
- Keep the mental model simple and auditable

This is a **manual-first MVP** and is fully compatible with later automation.

---

## Scope

This document covers:

- Manual creation of the SAT container
- Creation of the `sat` entrypoint
- Creation of `sat-init`
- Creation of minimal required configuration files

This document does **not** cover:

- SAT-managed archive creation
- Content creation
- Publication workflows
- Tool discovery beyond SAT system tools
- Bootstrap scripts or installers

---

## Assumed SAT Installation Path

All examples in this document assume the permanent SAT container is created at:

```bash
mkdir -p ~/projects/sat/stage/sat
```

This path is chosen by the human operator.  
SAT never decides where it is installed.

---

## High-Level Overview

SAT is created by:

1. Manually creating the SAT directory structure
2. Manually creating SAT system tools
3. Treating the result as **immutable system infrastructure**

No bootstrap phase is required for this MVP path.

---

## Step 1: Create the SAT Directory Structure

Create the minimal SAT system layout:

```bash
mkdir -p ~/projects/sat/stage/sat/en/bin/sat/config
mkdir -p ~/projects/sat/stage/sat/en/docs
```

Resulting structure:

```text
~/projects/sat/stage/sat/
└── en/
    ├── bin/
    │   └── sat/
    │       └── config/
    └── docs/
```

At this point, SAT exists only as a directory skeleton.

---

## Step 2: Create the `sat` Entrypoint

Create the SAT command shim:

```bash
nano ~/projects/sat/stage/sat/en/bin/sat/sat
```

Contents:

```bash
#!/usr/bin/env bash
set -e

SAT_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$SAT_ROOT/en/bin/sat/sat-init.py" "$@"
```

Make it executable:

```bash
chmod +x ~/projects/sat/stage/sat/en/bin/sat/sat
```

---

## Step 3: Create `sat-init.py`

Create the initializer:

```bash
nano ~/projects/sat/stage/sat/en/bin/sat/sat-init.py
```

Contents (minimal, authoritative):

```python
#!/usr/bin/env python3

from pathlib import Path

def main():
    sat_root = Path(__file__).resolve().parents[3]
    docs_dir = sat_root / "en" / "docs"

    docs_dir.mkdir(parents=True, exist_ok=True)

    print(f"SAT initialized at: {sat_root}")

if __name__ == "__main__":
    main()
```

Make it executable:

```bash
chmod +x ~/projects/sat/stage/sat/en/bin/sat/sat-init.py
```

---

## Step 4: Create Required Configuration Files

### `sat.yml`

```bash
nano ~/projects/sat/stage/sat/en/bin/sat/config/sat.yml
```

Contents:

```yaml
sat:
  version: "mvp"
  language: "en"
```

---

### `discovery.yml`

```bash
nano ~/projects/sat/stage/sat/en/bin/sat/config/discovery.yml
```

Contents:

```yaml
discovery:
  sat_tools: true
  archive_tools: false
  content_tools: false
```

---

## Step 5: Add SAT to PATH (Optional)

For interactive use:

```bash
export PATH="$HOME/projects/sat/stage/sat/en/bin/sat:$PATH"
```

Test:

```bash
sat
```

Expected output:

```text
SAT initialized at: /home/<user>/projects/sat/stage/sat
```

---

## What You Have Now

You now have:

- A permanent SAT container
- A working `sat` command
- A defined, immutable system tool directory
- No automation
- No ambiguity

And explicitly **not**:

- No SAT-managed archives created
- No content created
- No self-installing behavior

---

## Invariants (MVP)

- SAT never installs itself
- Humans decide SAT placement
- `bin/sat/` is system-owned and immutable
- SAT self-documentation lives in `en/docs`
- SAT-managed archive creation is always explicit and separate
- This manual process may later be automated, but never obscured

---

## Summary

- SAT exists because you created it
- SAT system tools are simple, local, and auditable
- This fast path is intentional and foundational

---

## License

This document, *SAT Bootstrap Process (MVP – Fast Manual Path)*, by **Christopher Steel**, with AI assistance from **ChatGPT (OpenAI)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).

![CC License](https://mirrors.creativecommons.org/presskit/buttons/88x31/svg/by-sa.svg)
