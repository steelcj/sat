# ADR-019: satlib as Single Source of Truth with Thin Tier CLIs
# Status: Proposed
# Date: 2026-07-09

## Context

The sat tier composes the collection and archive tiers: creating a SAT instance creates a collection containing language archives. The composition mechanism was an open decision — do tier executables invoke one another as subprocesses, or do all tiers call shared library functions directly?

The subprocess model would dogfood the delegated-tool model of ADR-004 literally: the sat tool shells out to the collection tool, which shells out to the archive tool. The cost is output parsing at every boundary, error propagation through exit codes and text, and the risk of the same logic drifting across tiers.

The question intersects the permission model: ADR-004 expresses permission through the filesystem — presence of a bin tier grants tier capability. Any shared-library answer must not turn the library into a second, contradictory permission surface.

## Decision

### 1. satlib is the single source of truth

Shared behaviour lives in one Python library, satlib. Tier CLIs are thin wrappers over its functions: argument parsing, operator interaction, and reporting belong to the CLI; validation, record writing, cascade resolution, and every other behaviour belongs to the library. The sat tier creates archives by calling the same `plan_archive` and `create_archive` the archive tier's own CLI calls. One implementation, every caller.

### 2. satlib is not a permission surface

ADR-004 is preserved unchanged: the thin CLIs remain the unit of delegation, and presence of `bin/collection/` is what grants collection-tier capability. satlib is shared plumbing, importable by every tier from the artifact's venv, and enforces nothing. Library sharing and filesystem-expressed permissions are orthogonal concerns; the gate is which executables exist at a given scope, exactly as before.

### 3. Placement and installation

satlib lives in the artifact at `en/lib/satlib/` — a self-contained Python project (its own `pyproject.toml`, package, and tests), parallel to `en/bin/`, never inside it. `lib/` is outside the permission surface by construction: bin tiers are delegated; libraries are not a unit of delegation. Future shared libraries arrive as sibling projects under `en/lib/`.

```text
sat/en/
├── bin/                    # permission surface (ADR-004), tiers only
│   ├── sat/
│   ├── collection/
│   ├── archive/
│   └── content/
├── lib/
│   └── satlib/             # project root: the pip install target
│       ├── pyproject.toml
│       ├── satlib/         # the importable package
│       └── tests/
└── docs/
```

The manager (`osat-fluent-sat-tool`) installs satlib into each version's venv as part of artifact installation (`pip install $SAT_TOOL_ROOT/en/lib/satlib/`). Tier executables simply `import satlib` — no path manipulation. Because delegated bin symlinks resolve into `$SAT_TOOL_ROOT`, executables always run beside the venv holding their satlib version; wrapper-driven version switching switches library and tools together, atomically.

### 4. Design disciplines the library carries

**Pure plan, executing create.** Resolution functions compute exactly what an operation will write without touching disk; separate functions execute plans. Dry-run and real runs share one resolution path, diverging only at the write — which is what makes the initialisation sequence's "nothing is approximated" contract literally true.

**Injected effects.** Network fetchers and clocks are parameters. The test suite runs against fixtures with no network and no wall time.

**Errors name the principle.** Refusal messages carry the architecture's own words (records are immutable; re-initialisation is an error, not a merge; a residual `<calculated>` is a tooling error, not a fallback), and verification reports every offending item together.

### 5. Deliberate absences

There is no `collection.py`: a collection has no creation event of its own — it is containment, cascade defaults, and (pending ADR-011 amendment) a relationship record, all compositions of existing primitives. Collection-tier orchestration (multi-archive atomicity, partial-failure policy) is deferred to the collection tooling decision. There is no `content.py`: ingress is outside the initialisation sequence. A planned `scan.py` dissolved during implementation — the pruned content walk belongs with the assets exclusion rule, the pattern test with validation; a module holding only relocated responsibilities is not a module.

## Alternatives Considered

**Subprocess composition** — rejected. Literal dogfooding of delegation is appealing, but every tier boundary becomes an output-parsing contract, errors flatten to exit codes and text, and dry-run purity cannot be guaranteed across process boundaries. The delegated-CLI model can still be layered on top of satlib later; the reverse migration — extracting a library from N subprocess protocols — is far costlier.

**Duplicated logic per tier executable** — rejected. The same validation and record-writing implemented four times is four opportunities to drift, and archive records written by different tiers must be byte-identical in convention.

**Shared code inside a bin tier** (`en/bin/sat/lib/`) — rejected. Every tier imports the library, so placing it inside one tier's delegated directory either breaks subordinate delegations (imports pointing into an undelegated tier) or leaks that tier's material through delegation. `lib/` beside `bin/` keeps the permission surface pure.

**A separate satlib repository and PyPI package** — rejected for now. The library and the tools it serves version together; the artifact is the unit of distribution, and a separately versioned library reintroduces the label/content divergence class the release workflow just eliminated. Revisit only if a second consumer outside the artifact appears.

## Consequences

- One implementation of every SAT behaviour; tier CLIs cannot drift from one another
- `--dry-run` is exact by construction: plan and create share resolution
- The test suite (109 tests at time of writing) ships in the artifact; operators can verify an installed version with pytest against `$SAT_TOOL_ROOT/en/lib/satlib/tests`
- Version switching is atomic across library and tools
- The fluent manager gains one install-time responsibility: the pip install into the version's venv
- Development requires a venv (PEP 668); the editable install mirrors the production per-version venv model
- Collection and content modules are deferred decisions, not omissions; their arrival will not restructure the library
- ADR-004 requires a small amendment (delegation source is the system artifact), recorded separately

## References

- ADR-004: Self-Replicating Permission Model
- ADR-016: Operator Wrapper Script Convention
- ADR-018: Universal Assets Directory Convention
- SAT Instance Initialisation Sequence v0.5.0
- satlib Design and Rationale v0.2.0
- SAT Language Validation and Offline Registry Cache Specification v0.1.0
