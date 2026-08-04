# ADR-018: Universal Assets Directory Convention

```yaml
status: Accepted
date: 2026-07-09
amended: 2026-07-09 (collision edge and precedence; see Amendments)
version: 0.1.1
```

## Context

SAT has accumulated parallel conventions for files related to a content entity: `filename.meta/` for metadata, `filename.schema/` for schemas, and hidden sidecar files (`.dc.yml`, `.provenance.yml`, `.language.yml`) at archive roots. Each concern introduced its own placement rule. A single entity's related material could be spread across several locations, and each new concern (fixity records, slug schemes, document media, derived renditions) would have required another convention.

A unifying rule is needed: one place per entity for everything regarding that entity, with a naming transform that is mechanical, reversible, and collision-free, and a placement rule that preserves self-containment — an archive or collection copied, moved, or cloned must carry all of its own records with it.

## Decision

### 1. One assets directory per entity

Every file and directory `<name>` has exactly one hidden assets directory named `.<name>.assets`. Everything regarding the entity lives in its assets directory.

```text
sat/               → .sat.assets/
en/                → .en.assets/
docs/              → .docs.assets/
sat-guide.md       → .sat-guide.md.assets/
```

### 2. The transform is literal

The assets directory name is the literal on-disk entity name with `.` prepended and `.assets` appended. No slugging, casing, or character substitution occurs at mapping time. Slug conformance is a precondition, not a runtime operation: in a SAT-managed tree, entity names are already slugs, derived from the DC sidecar at ingress (ADR-015).

For files, the name includes the extension. The dots delimit slug, extension, and suffix; slugs themselves contain no dots.

```text
sat-guide.md       → .sat-guide.md.assets/     ← correct: extension preserved
sat-guide.pdf      → .sat-guide.pdf.assets/    ← distinct entity, distinct assets
sat-guide.md       → .sat-guide-md.assets/     ← WRONG: re-slugged, not literal
```

The literal transform is reversible: strip the leading `.` and the trailing `.assets` and the entity name is recovered exactly. A slugging step at mapping time would collide distinct entities whose names slug identically onto a single assets directory.

The transform is injective per placement rule, not across both rules. One collision edge exists between them: a file named identically to its parent directory (`some/b/b`) maps its assets beside itself to the same path as the directory's own assets (`some/b/.b.assets`). The inside-placement interpretation takes precedence everywhere: that path is the directory's assets, and validation reports the file's claim as a `collision` orphan rather than guessing. Slug-governed trees make the case unlikely; deterministic precedence makes it harmless.

### 3. Placement

A directory's assets directory lives inside the directory it describes. A file's assets directory lives beside the file, since a file can contain nothing.

```bash
~/projects/sat/                                     # a directory
├── .sat.assets/                                    # its assets: inside it
│   ├── dc.yml                                      # collection default metadata (cascade source)
│   └── slug-scheme.yml                             # directory-level slug pattern (ADR-015)
│
└── en/                                             # a directory
    ├── .en.assets/                                 # its assets: inside it
    │   ├── dc.yml                                  # archive metadata (inherits collection defaults)
    │   ├── language.yml                            # language record (ADR-001, ADR-003)
    │   └── provenance.yml                          # archive provenance record
    │
    └── docs/
        ├── .docs.assets/
        │   └── dc.yml
        │
        ├── sat-guide.md                            # a file
        └── .sat-guide.md.assets/                   # its assets: beside it
            ├── dc.yml                              # file-level metadata
            ├── fixity.yml                          # checksum record: sha256, size, verified date
            └── figure-1.svg                        # media belonging to this document
```

Inside placement for directories is what preserves self-containment. The alternative — a sibling assets directory — would place the instance root's own metadata outside the instance:

```text
~/projects/sat/            + sibling  ~/projects/.sat.assets/    ← metadata left behind
                                                                    by any copy, move,
                                                                    clone, or tar of sat/
~/projects/sat/            + inside   ~/projects/sat/.sat.assets/ ← travels with the entity
```

### 4. Contents

The assets directory is the single home for all material regarding its entity. Typical contents by entity kind:

```text
collection root    dc.yml, slug-scheme.yml
archive root       dc.yml, language.yml, provenance.yml, slug-scheme.yml
content directory  dc.yml, slug-scheme.yml where a pattern is declared
content file       dc.yml, fixity.yml, document media, derived renditions
```

Files appear only where they carry information. In particular, `slug-scheme.yml` exists only where a directory declares a pattern; the cascade covers absent entries, and tooling does not scaffold empty stubs.

### 5. Renames are tool-mediated

The convention's known cost is that renaming an entity touches two names. Renames are therefore performed by tooling (`slug_rename.py`), which renames the entity and its assets directory atomically:

```text
mv guides/ handbooks/                       ← manual rename: pairing broken
                                              handbooks/.guides.assets/ orphaned

slug_rename guides/ handbooks/              ← tool rename: pairing preserved
                                              handbooks/.handbooks.assets/
```

Validation gains a tripwire from the same property: any `.*.assets/` whose pairing with an entity is broken is an orphan, reported and never silently repaired. Three orphan classes are distinguished: `no-entity` (no file or directory with the embedded name exists in the expected location), `misplaced` (the embedded name matches a sibling directory; directory assets belong inside, not beside), and `collision` (the edge case of Decision 2).

```text
$ sat-validate ~/projects/sat
ORPHAN: ~/projects/sat/en/docs/.old-guide.md.assets/
        no entity old-guide.md at ~/projects/sat/en/docs/
        Reported only. No repair performed.
```

### 6. One exclusion rule

Anything matching `.*.assets/` is metadata space. It is excluded from content enumeration, from ingress, and from the BCP 47 directory walk (the leading dot already guarantees the last, since language archive roots are never hidden).

## Alternatives Considered

**Sibling placement for directory assets** (`sat/` beside `.sat.assets/`) — rejected because the topmost entity's metadata falls outside the entity itself. Copying, moving, or archiving the directory silently leaves its records behind, breaking the self-containment that archive provenance depends on.

**Fixed internal name for directory assets** (`sat/.assets/` — the container identifies itself) — rejected because it splits the convention into two naming rules, one for files and one for directories, and an `.assets/` listing no longer states what it describes. The uniform `.<name>.assets` rule costs a two-name rename, accepted and mitigated by tool-mediated renaming (Decision 5).

**Slugging the entity name at mapping time** — rejected because the mapping becomes non-injective: distinct entities whose names slug identically would collide on one assets directory, and the entity name could no longer be recovered from the assets name. The transform must be literal; slug conformance is enforced at ingress, once.

**Parallel per-concern directories** (`filename.meta/`, `filename.schema/`, and successors) — rejected because each new concern multiplies visible directories and placement rules. One assets directory per entity scales to new concerns by adding a file, not a convention.

**Metadata embedded in content frontmatter** — rejected because it is format-dependent, unavailable to binary content, and conflates the content record with the content itself.

## Consequences

- `filename.meta/` and `filename.schema/` are absorbed and replaced; existing documentation referencing them requires adjustment
- Archive root sidecars relocate: `.dc.yml`, `.provenance.yml`, `.language.yml` become `dc.yml`, `provenance.yml`, `language.yml` inside `.<archive>.assets/` — the assets directory is now the hidden thing, so its contents drop the leading dot
- Every entity's related material has exactly one location, discoverable by a mechanical transform of the entity's name, and reversible back to it
- Content enumeration, ingress, and validation share a single exclusion pattern: `.*.assets/`
- Renaming an entity is a two-name operation and belongs to tooling; manual renames become detectable as orphaned assets directories rather than silent divergence
- Self-containment holds at every tier: any directory copied or cloned carries its own assets, including the instance root
- Publishing vectors own all adaptation of assets content for their targets (transmog); nothing in this convention is shaped by any publishing target
- Implemented in `satlib/assets.py` with the orphan classes and exclusion walk as its reference implementation

## Amendments

| Date | Change |
|------|--------|
| 2026-07-09 | Collision edge documented (Decision 2): file named as its parent directory; inside-placement precedence; injectivity restated as per placement rule. Orphan classes enumerated (Decision 5). Implementation reference added. Status Proposed → Accepted. |
| 2026-07-12 | `born.yml` renamed to `provenance.yml` per ADR-020, including the `.born.yml` pre-relocation form. |

## References

- ADR-001: Language as Filesystem Structure
- ADR-003: IANA Language Subtag Registry as Authoritative Source
- ADR-015: Slug Pattern Language
- ADR-017: Hugo Publishing Vector
- SAT Instance Initialisation Sequence v0.5.0
- satlib Design and Rationale v0.2.0 (ratification row 6)
