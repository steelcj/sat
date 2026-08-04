---
status: Proposed
date: 2026-05-13
amended: 2026-07-12
version: 0.1.2
---

# ADR-009: Distribution by Installer and Instantiation

## Context

SAT tools self-discover their operational language context by walking upward from their position in the filesystem until they find a directory whose name is a valid BCP 47 language tag (ADR-005). This mechanism is load-bearing: it is what allows the tool's own structural position to declare its language rather than relying on a configuration value or a hardcoded default. It is also what allows new language editions of SAT to operate without code changes.

Conventional Python distribution via PyPI is incompatible with this model. A tool installed by `pip install sat` or `pipx install sat` lives in a virtual environment such as `~/.local/pipx/venvs/sat/bin/` or in `site-packages/`. None of the ancestor directories of that location is a BCP 47 tag. Every invocation of a directly installed tool therefore falls into the non-authority path defined in section 4 of the SAT Language Validation and Offline Registry Cache Specification — not because the operator intends to work outside the authority model, but because the installation method has erased the structural declaration.

A second consequence is the loss of the structural English default. ADR-005 makes the explicit point that SAT ships in `en/` "so English is the default not because it was assumed but because it was declared structurally." A direct pip install removes that declaration. The default returns to being an assumption — exactly the failure mode that ADR-001 was written to refuse in the document domain.

A third consequence is that the delegation model defined in ADR-004 has nothing to operate on. Delegation works by copying or symlinking `bin/` tiers from a SAT root into subordinate collection, archive, or content scopes. A venv install does not expose a `bin/` tier in the structural sense — only a Python entry point. There is no archive `bin/` tier to copy.

At the same time, operators familiar with Python tooling reasonably expect PyPI to be the acquisition channel. Requiring manual filesystem assembly to obtain a working SAT instance would create friction with no compensating benefit. The question is how a SAT instance comes into being on an operator's machine in a way that satisfies both the structural model and reasonable distribution expectations.

## Decision

PyPI distributes an installer, not the tool. The installer is a small, stable package whose single responsibility is to perform an instantiation that materialises a sovereign SAT instance at an operator-chosen path. The installer is not required to remain installed after instantiation.

Instantiation is invoked as:

```text
sat instantiate <path> --language <bcp47-tag>
```

Instantiation performs the following:

```text
1. Validates the --language argument against the IANA registry cache
   (seeding the cache from network if absent, per the validation spec)
2. Materialises the full structural payload at <path>:
     <path>/<language>/bin/sat/
     <path>/<language>/bin/archive/
     <path>/<language>/bin/content/
     <path>/<language>/docs/
3. Writes the new instance's immutable identity (ADR-021) and
   provenance (ADR-020 §4) records at the instance root
4. Verifies the materialised root satisfies ADR-005 self-discovery
5. Reports the instantiation and exits
```

The materialised instance contains its own canonical launcher at `<path>/<language>/bin/sat/sat.py`. All subsequent invocations of SAT go through that launcher, not through the installer. Self-discovery walks upward from the launcher's location and finds the language ancestor exactly as ADR-005 specifies. The structural model is preserved literally.

The instance provenance record carries the installer version, the IANA registry `File-Date` at the moment of instantiation, and the instantiation timestamp. This record is immutable for the same reason every provenance record is immutable (ADR-020 §4): it is the instance's own provenance, not a cached value to be re-derived. The `[birth]` cfg block collision with cfg conventions established in ADR-007 and ADR-008, once acknowledged and deferred here, is closed as moot per ADR-020: the block was never implemented and the term is retired. The instance provenance record is a `provenance.yml` asset (ADR-018), not a cfg block.

The instance also carries a stable identity minted at the same moment: an `identity.yml` at the instance root holding a UUID `dc:identifier`, written once and never modified (ADR-021). The identity record answers what the instance *is*, independent of the path it occupies; the provenance record answers how it *came to exist*. Both are written at instantiation under the same write-once, refuse-if-present contract — instantiation refuses a target that already carries either.

Instantiation is available from within any instantiated SAT instance, allowing one instance to instantiate another without re-acquiring the installer. The actor differs; the event is identical. This is consistent with the project's broader pattern of treating SAT instances as sovereign — once instantiated, an instance carries everything it needs, including the capacity to instantiate siblings.

The PyPI package name (`sat`, `sat-installer`, or whatever is ultimately registered) is an acquisition-channel name. It is not the project name. The project is what gets instantiated, not what gets installed.

## Alternatives Considered

**Direct PyPI install of the running tool** — rejected because the installed tool has no language ancestor in its filesystem path. Self-discovery per ADR-005 cannot succeed. Every invocation falls into the non-authority path by accident rather than by operator intent. This is the precise failure mode SAT was designed to refuse.

**Hardcoded English default in the installed tool** — rejected because it embeds an English assumption invisibly into the tool's behaviour. This is the failure mode ADR-001 exists to prevent in the document domain; adopting it in the tool domain would be self-contradictory.

**Edition wheels installed conventionally via pip** — rejected for the same reason as direct install. Wheel payloads unpacked into `site-packages/<language>/` would have a language ancestor in name only — the surrounding venv structure would still dominate the self-discovery walk, and operators would be unable to delegate `bin/` tiers per ADR-004 because the wheel's `bin/` tier is not at a path they own.

**Manual filesystem assembly with no PyPI presence** — rejected because it removes the acquisition path entirely. New operators would need to clone a repository, place its contents correctly, and configure their PATH before performing any SAT operation. This raises the barrier to entry without strengthening the structural model.

**A shell script fetched by curl** — rejected because it provides no version provenance, no integrity verification by default, and no clean upgrade path. PyPI provides these by convention and tooling; replicating them in a custom script is work that does not need to be redone.

## Consequences

- The PyPI dependency is bounded to a one-time acquisition event. The running SAT instance is sovereign by the style guide's definition once instantiation completes.
- The installer can be uninstalled after instantiation without affecting the instantiated instance. Operators who prize sovereignty can remove it; operators who prefer convenience can leave it installed.
- Instantiation and archive creation share the same provenance-record shape (ADR-020 §4) but are named distinctly per tier: instantiation at the instance level, creation at the archive level. Neither borrows the other's vocabulary.
- Instantiation writes the instance's identity record (ADR-021) at the instance root, under the same write-once, refuse-if-present contract as its provenance record; the two together answer what the instance is and how it came to exist.
- New language editions of SAT are acquired by passing a different `--language` argument to the same installer. There is no separate `sat-fr-ca` package to publish, no per-edition release cadence to coordinate. The installer is language-neutral; instantiation is what carries the language declaration.
- Non-Python tooling added in the future can be acquired by the same installer or by parallel installers without changing the structural model. The installer is an acquisition layer; the running instance is what carries the structural commitments.
- The `[birth]` cfg block collision with ADR-007 and ADR-008, once acknowledged and deferred here, is closed as moot per ADR-020: the block was never implemented and the term is retired.
- An instantiated SAT instance can instantiate another instance using the same verb. This gives operators a path to create sibling instances, language editions, or test environments without re-acquiring the installer — preserving sovereignty after the initial acquisition.
- The installer framing makes the role of PyPI explicit: it is where SAT instances are acquired, not where they live. The project's centre of gravity remains the filesystem instance, not the package index.

## Amendments

| Date | Change |
|------|--------|
| 2026-07-12 | Retitled and revised per ADR-020: midwife → installer, birth/born → instantiate/instantiated throughout; the `[birth]` cfg block collision with ADR-007/ADR-008, previously deferred, is closed as moot (the block was never implemented); the inverted framing borrowing legitimacy from the validation spec's archive-tier record is corrected — the instance provenance record stands on ADR-020 section 4. |
| 2026-07-12 | Cite ADR-021: instantiation writes the instance's stable identity record (`identity.yml`) at the instance root alongside its provenance record. Version 0.1.2. |

## References

- ADR-001: Language as Filesystem Structure
- ADR-004: Self-Replicating Permission Model
- ADR-005: Tool Self-Discovery from Filesystem Context
- ADR-006: Corpus as Level 1 Container Term (Rejected)
- ADR-018: Universal Assets Directory Convention
- ADR-020: Controlled Vocabulary and Creation-Event Terminology (amends this ADR; section 4 establishes the instance provenance record this ADR's instantiation writes)
- ADR-021: Stable Identity at Creation (the instance identity record this ADR's instantiation writes at the instance root)
- SAT Language Validation and Offline Registry Cache Specification v0.1.1
  — section 5: Archive Immutability
- SAT Filesystem and Configuration Cascade Specification v0.0.2
