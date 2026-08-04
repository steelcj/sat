# ADR-016: Operator Wrapper Script Convention and sat-tools Directory Structure
# Status: Proposed
# Date: 2026-06-14

## Context

SAT tools live inside the `sat-tools` repository under a tiered directory structure that mirrors the four-tier permission model defined in ADR-004. Invoking them directly requires the operator to know the full path to the tool script and to manage the venv invocation explicitly. This creates fragile shell configuration and provides no clean separation between the tool source and the operator-facing command interface.

ADR-004 defines four roles — SAT Admin, Collection Admin, Archive Admin, and Content Admin — expressed through the filesystem by copying bin tiers downward. It does not address how the operator invokes tools from outside the archive structure. This leaves the operator-facing entry point undefined.

ADR-005 describes tool self-discovery from filesystem context: a tool determines its operational language by walking upward from its own location to find the nearest BCP 47 language archive root. This mechanism works correctly when the tool executes from its location inside the `sat-tools` repository. The wrapper convention must preserve this property.

SAT is under active development with tools added incrementally across multiple tiers. The wrapper convention must support modular tool development without requiring changes to the operator's shell configuration each time a new tool is added.

## Decision

### 1. sat-tools repository structure

The `sat-tools` repository is cloned to `~/bin/sat-tools/`. It is organised by tier, with each tier directory containing both the tool scripts and the wrapper scripts for that tier:

```text
~/bin/sat-tools/
  sat/
    sat-init.py
    scripts/
      nix/
        sat-init
  collection/
    collection-init.py
    scripts/
      nix/
        collection-init
  archive/
    archive-init.py
    scripts/
      nix/
        archive-init
  content/
    content-ingress.py
    slug-rename.py
    scripts/
      nix/
        content-ingress
        slug-rename
  .venvs/
    sat/
      1.0.0/
  requirements.txt
```

The four tiers — `sat/`, `collection/`, `archive/`, `content/` — correspond directly to the four roles defined in ADR-004. Each tier is self-contained: its tool scripts and its wrapper scripts travel together. This makes tier delegation consistent with the copy-downward model ADR-004 already defines.

### 2. Shared venv

All SAT tools share a single Python virtual environment versioned by SAT release. `requirements.txt` lives at the repository root and governs the shared venv. The venv is created once during installation and shared across all tool tiers:

```bash
python3 -m venv ~/bin/sat-tools/.venvs/sat/1.0.0
~/bin/sat-tools/.venvs/sat/1.0.0/bin/pip install -r ~/bin/sat-tools/requirements.txt
```

Upgrading SAT creates a new venv at the new version path. Wrappers are updated to point to it. The old venv is retained until the operator removes it explicitly.

Python 3.8 is the minimum supported version. This covers Ubuntu 20.04 LTS and later, macOS 12 and later, and Windows 10 and 11 via standard python.org installers.

### 3. Wrapper script convention

Each wrapper is a thin shell script that invokes the real tool at its repository location via the shared SAT venv. The wrapper does not contain logic. It resolves two paths — the venv and the tool script — and delegates entirely via `exec`:

```bash
#!/usr/bin/env bash
SCRIPT_DIR="$HOME/bin/sat-tools"
exec "$SCRIPT_DIR/.venvs/sat/1.0.0/bin/python" \
     "$SCRIPT_DIR/sat/sat-init.py" "$@"
```

`exec` replaces the shell process rather than spawning a child. `"$@"` passes all arguments through unmodified.

The wrapper executes the tool at its actual repository path, preserving the self-discovery sequence defined in ADR-005. The tool walks upward from its location inside `~/bin/sat-tools/`, finds the appropriate BCP 47 language directory, and declares its operational language context correctly regardless of how it was invoked.

### 4. Installation

Wrapper scripts are installed by copying from each tier's `scripts/nix/` directory to `~/bin/` in a single command:

```bash
cp ~/bin/sat-tools/*/scripts/nix/* ~/bin/.
chmod +x ~/bin/sat-tools/*/scripts/nix/*
```

The glob `*/scripts/nix/*` traverses every tier directory and copies all wrappers without naming them explicitly. Adding a new tool to any tier is picked up by the same install command with no further configuration required.

`~/bin/` is on the PATH by default in most Nix-like environments. No PATH configuration is needed beyond what the operating system already provides.

### 5. Platform support

Windows wrapper scripts live alongside their Nix equivalents in a platform-specific subdirectory:

```text
sat/
  scripts/
    nix/
      sat-init
    windows-11/
      sat-init.bat
```

Platform support is additive. Adding `windows-11/` wrappers requires no changes to the Nix convention. The installation command is platform-specific; the repository structure is not.

## Alternatives Considered

**One repository per tier** — rejected because it fragments the shared venv, complicates versioning SAT as a whole, and requires the operator to clone and maintain four separate repositories. The self-contained tier directories within a single repository provide the same modularity without the coordination overhead.

**Wrapper scripts at the repository root under `scripts/nix/`** — rejected because it separates wrappers from the tools they invoke. Keeping wrappers inside the tier directory means each tier is self-contained and delegation copies both tools and their wrappers together.

**Tiered subdirectories in `~/bin/`** — rejected because `~/bin/` is already on PATH in most Nix environments and no additional PATH configuration is needed. Flat wrappers in `~/bin/` follow the convention established by existing SAT-adjacent tooling such as `hugo-tool`.

**Adding the tool directories directly to PATH** — rejected because it encodes the repository structure into the operator's shell environment. Moving or restructuring the repository would require shell configuration changes.

**Single `sat` dispatcher with subcommands** — rejected because it couples all tool tiers into one entry point and conflicts with SAT's modular development model. Discrete wrappers require no coordination when new tools are added.

## Consequences

- Each tier is self-contained — tool scripts and wrapper scripts travel together
- Delegation follows the ADR-004 copy-downward model naturally
- Installation is a single glob command; adding new tools requires no installer changes
- The shared venv is versioned by SAT release and lives inside the repository directory, consistent with the pattern established by `hugo-tool` and `slugify-tool`
- `~/bin/` requires no PATH configuration beyond operating system defaults
- Platform support is additive via `scripts/<platform>/` subdirectories
- ADR-005 self-discovery is preserved — wrappers execute tools at their repository paths
- ADR-004 is unaffected in substance; this ADR addresses the operator-facing layer above the archive permission cascade

## References

- ADR-004: Self-Replicating Permission Model
- ADR-005: Tool Self-Discovery from Filesystem Context
- hugo-tool: https://github.com/steelcj/hugo-tool
