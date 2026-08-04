---
status: Proposed
date: 2026-07-31
version: 0.1.1
---

# ADR-032: The Shipped Defaults Floor Below the Operator Cascade

## Context

ADR-025's resolution order (section 7) walks five layers, deepest-stated-
value-wins: instance, collection, archive, content-organizing directory,
document. Every layer is operator data, living in a role-owned `dc.yml`,
written by an operator or by tooling acting on an operator's behalf. There
is no layer that is SAT's own opinion, shipped with the code, present
before any operator has stated anything.

In practice this means SAT's own baseline choices — that metadata is
Dublin Core, for instance — are not settings at all. They are assumptions
compiled into `cataloging.py` and reproduced as a normative table inside
ADR-023, changeable only by amending that ADR. As SAT grows — markdown
house rules (ADR-030), a `staging/` promotion policy (ADR-029), and
whatever comes after — each new feature has faced the same choice: bury
another assumption in code, or invent another one-off file location, as
was under active discussion for `default-markdown-spec.yml` before this
ADR. Neither scales. Bothered by this: bin/ directories were never meant
to be recreated per feature, and operators were never meant to have to
originate a value SAT could have shipped an opinion about.

A second problem sits alongside the first. `en/bin/sat/` is the one tier
never delegated (ADR-004's role table — Collection Admin receives
`bin/archive/` and `bin/content/`, never `bin/sat/`). If SAT's shipped
opinions live there, SAT Admin retains sole, structural control over them
regardless of what has been delegated elsewhere — visible, curatable, and
never reachable by a delegate who was never handed that tier.

Resolving where to put this surfaced a real ambiguity, worked through at
length before this ADR was drafted: does a shipped floor behave like the
existing five layers (read at read time, no caching, no exception), or
does it get copied into new scopes at creation the way ADR-026 explicitly
rejected for operator data ("duplicated defaults in lower tiers... two
copies of one fact is the definition of the drift problem")? The concern
was that a shipped floor changing silently on a SAT upgrade is a
different kind of surprise than an operator's own deliberate edit
cascading — even though the read mechanism is identical in both cases.

## Decision

### 1. Location: `en/bin/sat/defaults/<tier>/`, one directory per cascade tier

```
en/bin/sat/defaults/
  sat/
    metadata/
      dc.yml
  collection/
    metadata/
      dc.yml
  archive/
    metadata/
      dc.yml
  content/
    metadata/
      dc.yml
```

Four directories, matching the four operator-facing tiers ADR-025 already
resolves (sat, collection, archive, content). All four live under
`bin/sat/`, never delegated, so SAT Admin's shipped opinions cannot be
touched by any delegate at any tier, structurally, the same guarantee
ADR-025 decision 3 gives operator data ("defaults that cascade into
other collections are protected by construction").

`dc.yml` nests under a `metadata/` concern folder rather than sitting
flat, matching the reserved-concern-parent pattern ADR-025 already uses
for `resources/` (`resources/imgs/`, `resources/licences/`). This is not
preemptive: `content-egress.py`'s existing pipeline already produces
three metadata sidecar types from one cataloging pass, `dc.yml`,
`og.yml`, and `schema.yml`, so a shipped floor for Open Graph or
Schema.org defaults, should one ever be wanted, has a place to land
without restructuring. A single-file concern (see `markdown.yml` below)
does not need this treatment; `metadata/` earns it because a second file
is a real, already-precedented possibility, not a hypothetical one.

Four directories were chosen over one shared floor specifically for this
visibility property, not because resolution requires tier-specific
shipped values today. A single `en/bin/sat/defaults/dc.yml` would resolve
correctly for the MVP; the four-way split is what lets SAT Admin see, and
curate, exactly what is being shipped to each tier, independent of
whether any values actually differ between them yet.

### 2. Resolution order amendment (ADR-025 section 7)

Each tier's shipped-floor file is inserted immediately before that tier's
own operator layer, not appended once at the bottom. The five-layer walk
becomes nine:

```
0a. en/bin/sat/defaults/sat/metadata/dc.yml        SAT's shipped opinion
1.  .<instance>.assets/sat/dc.yml                   operator's instance override

0b. en/bin/sat/defaults/collection/metadata/dc.yml SAT's shipped opinion
2.  .assets/collection/dc.yml                       operator's override

0c. en/bin/sat/defaults/archive/metadata/dc.yml    SAT's shipped opinion
3.  .assets/archive/dc.yml                          operator's override

0d. en/bin/sat/defaults/content/metadata/dc.yml    SAT's shipped opinion
4.  .assets/content/dc.yml                          operator's override (per directory)

5.  document's own dc.yml, or transcribed frontmatter at ingress (ADR-023)
```

The operator-side paths (`.assets/<role>/dc.yml`) are unchanged by this
correction, they live in role directories per ADR-025, a separate
mechanism from the shipped floor's `metadata/` concern folder.

Precedence is unchanged: deepest-stated-value wins, absence inherits. A
shipped floor value is simply the new outermost candidate — the value an
operator inherits if nobody, at any tier, has ever stated an opinion of
their own.

### 3. Read-time resolution, no exception

The shipped floor resolves exactly like every other layer: read from disk
at the moment a command runs, discarded the instant that command finishes,
never cached, never watched. This is `resolve_entity()`'s existing,
uniform behaviour, applied without a special case. No daemon, no runtime
state, consistent with the standing principle ("filesystem-visible — no
database, no runtime state," `sat-mvp-roadmap.md`). ADR-014's filesystem-
event-driven model remains deferred and unaffected: if and when it lands,
it changes what *triggers* a read-time walk, not the walk itself.

### 4. Permission and the defaults floor are two different mechanisms

Stated explicitly, because the two were repeatedly conflated during this
ADR's own drafting discussion:

| | Permission (delegation) | Defaults floor |
| --- | --- | --- |
| Mechanism | Copy `bin/<tier>/`, or own the role directory (ADR-025 §3) | `en/bin/sat/defaults/<tier>/`, read at read time |
| Frequency | Once, at delegation | Every resolution, always |
| What changes it | A deliberate delegation or revocation act | SAT Admin editing the shipped file, or a version upgrade |
| Re-checked after the fact? | No — presence is the grant, permanently | Yes — that is the entire point |

Re-checking permission on every resolution would be pointless; it is a
grant, not a value. Not re-checking the defaults floor would silently
defeat the reason it exists: reaching scopes that never stated their own
opinion, without requiring every existing scope to be touched by hand.

### 5. Each shipped-floor location may hold more than `dc.yml`

The location is not `dc.yml`-specific. A shipped floor directory may hold
any named settings domain SAT ships an opinion about — `markdown.yml`
(ADR-030's house rules), a future `egress.yml`, and so on — following the
same file, or file-becomes-directory, pattern Ansible's `group_vars`
already proves (`all.yml`, or `all/` holding several files that merge
into the same namespace). This is the extensibility payoff motivating
the whole ADR: a new feature adds a new named file to an existing,
already-permission-scoped directory. No new `bin/` location is invented,
and no resolver change is required, per feature, ever again.

```
en/bin/sat/defaults/content/
  metadata/
    dc.yml
  markdown.yml       # ADR-030's rule toggles, single-file concern today
```

The same file-or-directory escape hatch applies to `markdown.yml` too,
not only to `metadata/`. If markdown rules ever need splitting by tool
rather than staying one flat file:

```
en/bin/sat/defaults/content/
  markdown/
    github.yml       # GFM-specific constraints (task lists, tables)
    goldmark.yml      # if the goldmark parser (radar, currently Hold)
                       # ever needs config distinct from mdformat's
```

Same merged namespace either way, `check_house_rules()` does not care
whether `markdown.yml` is one file or a directory of them, the same way
`resolve_entity()` does not care whether `dc.yml`'s values came from one
file or several.

This also makes SAT's own baseline choices — Dublin Core as the MVP
vocabulary, for instance — expressible as a value (`sat:metadata_schema:
dublin_core`, exact field left to implementation) rather than an
assumption compiled into `cataloging.py`. Actually performing that swap
in `cataloging.py` is follow-on work; this ADR only makes the value a
settable thing to swap.

### 6. `sat defaults --diff`: an on-demand, read-only report

A new CLI surface reporting what the shipped floor has changed since a
prior recorded state, and which currently-un-overridden scopes it would
newly affect. Read-only — it writes nothing, so it is not gated behind
`--apply` the way mutating tools are; it exists purely so an admin can
check before, or independent of, running anything that writes. **Flagged
for review**: the exact "changed since when" baseline is not designed
here — the most likely mechanism is a fixity digest of the shipped-floor
files (ADR-027's existing machinery, applied to a new location), recorded
at each release and compared on demand, but that is implementation work
for whoever builds this, not a decision this ADR makes.

Upgrade visibility during a write operation is already covered without
new work: every writing tool already narrates a PLAN before `--apply`
(`content ingress`'s own example: "6 fields resolved"), so a shipped-
floor change affecting an in-progress operation is already surfaced at
the moment it matters. `--diff` covers the separate case of checking
before anything is about to write at all.

## Alternatives Considered

**A single shared `en/bin/sat/defaults/dc.yml`, no per-tier split** —
considered sufficient for resolution alone; rejected in favour of four
directories specifically for the delegation-visibility property (decision
1), not because runtime resolution requires it. If that property turns
out not to matter in practice, collapsing to one file is a cheap future
revision — nothing else in this ADR depends on there being four.

**Copy the shipped floor into each new scope's `dc.yml` at creation** —
rejected. This is ADR-026's rejected "duplicated defaults in lower tiers"
pattern, relocated rather than avoided. "Change the default for everyone"
would require touching every already-created scope by hand, exactly the
outcome sparse inheritance and read-time resolution exist to prevent.

**A daemon or watcher keeping resolved values current** — rejected.
Contradicts the standing no-runtime-state principle and duplicates work
ADR-014 (deferred) already owns in a different, narrower form — a
filesystem-event trigger for an operator-invoked tool, not a persistent
cache.

**No shipped floor at all; keep baseline choices in code** — rejected as
the status quo this ADR exists to change. Confirmed not to scale as a
concrete instance: `default-markdown-spec.yml`'s location was under
active, inconclusive discussion, symptomatic of the general problem, not
a one-off.

**Making the defaults floor part of the operator cascade's own five
layers (a sixth `dc.yml` an operator could theoretically edit)** —
rejected. `en/bin/sat/` is versioned with the code and reset on upgrade;
treating it as operator-editable in place would make "upgrade SAT" and
"lose an operator's edit" the same event, an even worse drift trap than
the one being solved.

## Consequences

- ADR-025 section 7's resolution order is amended from five layers to
  nine: a shipped-floor layer inserted immediately before each of the
  four operator layers.
- `en/bin/sat/defaults/{sat,collection,archive,content}/metadata/` are
  new directories, each initially holding a `dc.yml`. None are
  delegated; all sit under `bin/sat/`, matching ADR-004's
  tier-permission table. `metadata/` nests as a concern folder, not a
  flat file, matching ADR-025's `resources/` pattern and leaving room
  for `og.yml`/`schema.yml` floors later without restructuring.
- satlib's cascade resolver (`resolve_entity()`) gains four additional
  read steps, read-time, no caching — a resolver change, not a new
  mechanism.
- Shipped-floor directories may grow additional named files
  (`markdown.yml`, future domains) without further resolver changes or
  new `bin/` locations — the extensibility property motivating this ADR.
- `cataloging.py`'s Dublin Core assumption becomes, in principle, a
  shipped-floor value rather than a hardcoded fact. Making that swap real
  is not designed here — flagged as follow-on work.
- New CLI surface: `sat defaults --diff` (name provisional), read-only,
  not gated by `--apply`. Its exact change-detection mechanism is flagged
  for review, likely fixity-based (ADR-027), not designed here.
- Documentation must keep "permission" (copy-once delegation) and
  "defaults floor" (read-time, SAT-owned) named as two distinct
  mechanisms — the two were repeatedly conflated while drafting this ADR,
  and nothing about the filenames involved (`dc.yml` appears in both)
  makes the distinction obvious to a future reader.

## References

- ADR-004: Self-replicating permission model
- ADR-014: Filesystem-event-driven tooling model (deferred, unaffected)
- ADR-023: Metadata cataloging at content ingress (the Dublin Core
  assumption this ADR makes swappable in principle)
- ADR-025: Role-named assets directories, sparse inheritance, and the
  resolution order (section 7 amended by this ADR)
- ADR-026: Full-chain creation, the instantiation preseed, and seeding
  (the duplicated-defaults rejection this ADR's read-time requirement
  preserves)
- ADR-027: Fixity (likely mechanism for `--diff`'s change detection)
- ADR-029: Staging — pre-ingress content placement and promotion
  (the same "specification needs a companion amendment" pattern)
- ADR-030: Markdown normalization at content ingress (the immediate
  motivating case — `default-markdown-spec.yml`'s undecided location)
- `sat-mvp-roadmap.md` — the no-runtime-state, filesystem-visible
  principles this ADR's read-time requirement is bound by
- `en/lib/satlib/satlib/roles.py` — the existing role-directory
  implementation this ADR's resolver change extends

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.1 | Proposed | `dc.yml` moved under a `metadata/` concern folder at each tier (`en/bin/sat/defaults/<tier>/metadata/dc.yml`), matching ADR-025's `resources/`-style nesting rather than sitting flat. Correction, not a new decision, `content-egress.py` already produces three metadata sidecar types (`dc.yml`, `og.yml`, `schema.yml`) from one cataloging pass, so a shipped floor needs room for more than `dc.yml` from the start. `markdown.yml` unaffected in its own path; the same file-or-directory escape hatch made explicit for it too (`markdown/github.yml`, `markdown/goldmark.yml`), not held out as metadata-specific. |
| 0.1.0 | Proposed | Initial draft, resolving a multi-turn discussion: four-tier shipped defaults floor under bin/sat/ (never delegated), inserted into ADR-025's resolution order as one layer per tier, read-time with no exception (rejecting both copy-at-creation and daemon/watcher alternatives), permission and defaults-floor explicitly named as two different mechanisms, shipped-floor locations generalized to hold more than dc.yml (the extensibility payoff), and an on-demand sat defaults --diff report flagged for review rather than fully designed. |
