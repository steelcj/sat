# ADR-004: Self-Replicating Permission Model
```yaml
Status: Accepted
Date: 2026-04-14
Amended: 2026-07-09 (delegation source; see Amendments)
version: 0.1.1
```
## Context

SAT needs a permission model that works for a single author on one
machine in the MVP and scales to multi-user organisational deployments
without requiring a separate access control system. The model must be
self-documenting, portable, and congruent with Unix filesystem
conventions.

Since this record was accepted, tool distribution has moved to a
system-installed, wrapper-resolved model (ADR-016, ADR-019): versioned
artifacts live under `~/.local/share/sat-tool/<version>/` and instances
resolve tooling through operator wrappers rather than embedded copies.
The permission model is unchanged by this; the source of delegation is.

## Decision

Permissions are expressed through the filesystem. The act of copying
a bin directory tier to a subordinate location is the act of delegating
the permissions associated with those tools. No separate access control
configuration is required.

Four roles are defined:

```text
SAT Admin         ← sat/en/bin/ full access
Collection Admin  ← collection/bin/ archive/ and content/ tiers
Archive Admin     ← archive/bin/ archive/ and content/ tiers
Content Admin     ← content/bin/ content/ tier only
```

Delegation is performed by placing bin tiers at subordinate locations.
The delegation source is the installed artifact:

```text
$SAT_TOOL_ROOT/en/bin/archive/ → collection/bin/archive/   (Collection Admin)
$SAT_TOOL_ROOT/en/bin/archive/ → archive/bin/archive/      (Archive Admin)
$SAT_TOOL_ROOT/en/bin/content/ → content/bin/content/      (Content Admin)
```

The default delegation method is symlinks for single-machine
deployments: version switches performed by the manager propagate to
every delegated scope with no modification, because the links resolve
through `$SAT_TOOL_ROOT`. Copies are used for multi-user or distributed
deployments where independent versioning is required; copies pin the
scope to the copied version and require an explicit upgrade step.

Shared library code is not part of the permission surface. satlib
(ADR-019) is importable by every tier and enforces nothing; the gate
is which executables exist at a given scope.

## Alternatives Considered

**Separate RBAC configuration file** — rejected because it creates an
external dependency that must stay in sync with the filesystem and
requires tooling to enforce.

**OS-level file permissions** — rejected because they are not portable
across operating systems and do not survive git operations cleanly.

**Role registry in definitions/** — rejected because it separates the
permission declaration from the tools it governs.

## Consequences

- The filesystem layout is the permission documentation
- Adding a new user means placing a bin tier, not editing a config file
- Symlinks mean version switches by the manager propagate automatically
  to all delegated scopes; a delegated symlink breaks if the manager's
  artifacts are removed — an accepted trade of the system-installed
  model (ADR-019 supersedes the embedded-copy notion of sovereignty:
  instance data and provenance are sovereign; tooling is resolved)
- Copies require an explicit upgrade propagation step
- A collection can be promoted to a standalone SAT by adding bin/sat/
- The model is self-documenting — presence of a tool implies permission
- OPEN: how subordinate tier commands are placed when not already
  present — via `sat`, a `sat install` verb, or companion
  `osat-fluent-*` repositories — is an open decision awaiting its own
  record; nothing in this model constrains the answer

## Amendments

| Date | Change |
|------|--------|
| 2026-07-09 | Delegation source restated as the installed artifact (`$SAT_TOOL_ROOT/en/bin/`) rather than an in-instance `sat/en/bin/`; symlink default explained in terms of wrapper-resolved version switching; satlib explicitly excluded from the permission surface; `sat install` recorded as open. |

## References

- ADR-016: Operator Wrapper Script Convention
- ADR-019: satlib as Single Source of Truth with Thin Tier CLIs
- [SAT Filesystem and Configuration Cascade Specification v0.0.2](sat-filesystem-and-configuration-cascade-specification-v0.0.2.md)
