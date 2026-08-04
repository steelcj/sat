# ADR-010: Document Identity and Cross-Language Linking

```yaml
status: Proposed
date: 2026-05-20
amended: 2026-07-10 (two-field identity model; assets-canonical storage; see Amendments)
version: 0.1.3
```

## Context

ADR-001 establishes that language is expressed by filesystem structure. Each language archive is an independent, self-contained archive. An English product document at `en/produits/henson-aircraft-aluminum.md` and its French translation at `fr/produits/henson-aluminium-aeronautique.md` share no structural relationship — they are in separate language archives with independent paths, filenames, and slugs. This is correct and intentional.

However, a publishing vector consuming the archive needs to know that these two documents are translations of the same work. Without a declared relationship, the vector must infer it from naming conventions or directory mirroring — both of which are fragile and incompatible with the independently-pathed archives that ADR-001 and ADR-008 describe. Search indexing, hreflang link generation, language switching, and cross-language navigation all depend on this relationship being explicitly declared in the archive, not reconstructed by the vector.

ADR-007 establishes path-as-identity for entities within a language archive. That model is correct for intra-archive references. It does not extend to cross-language linking, where the same conceptual document has different paths in different archives by design.

A secondary concern is the stability of citations and external references. A document's path may change — a section may be restructured, a slug corrected, a language archive renamed. An identifier that is independent of the path survives these changes. A path-derived identifier does not.

Since this record was first drafted, ADR-018 established the universal assets directory convention as the single home for entity metadata, and the FRBR work/expression distinction was adopted to separate two questions this record originally answered with one field: *which document is this?* and *which documents say the same thing in other languages?* One identifier cannot answer both without ceasing to identify.

## Decision

### 1. Two identifiers: expression identity and work correspondence

Every SAT entity carries `dc:identifier` — a universally unique identifier that is the entity's own identity. It is unique to that entity: no two entities ever share a `dc:identifier`. It is assigned at creation or ingress and is immutable thereafter.

Documents that are translations of the same work additionally carry `sat:work` — a shared work identifier in the same format. All expressions of one work carry the same `sat:work` value. Two documents with the same `sat:work` and different languages are the translation pair; correspondence is derived from identity, never from paths or names.

```yaml
# en/produits/.henson-aircraft-aluminum.md.assets/content/identity.yml
dc:identifier: "urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e"   # this expression
sat:work: "urn:uuid:018f2a91-6c3d-4e7a-8b2f-1a9c0d4e5f6a"        # the shared work

# fr/produits/.henson-aluminium-aeronautique.md.assets/content/identity.yml
dc:identifier: "urn:uuid:9a1b3c5d-2e4f-4a6b-8c0d-2b3c4d5e6f7a"   # a different expression
sat:work: "urn:uuid:018f2a91-6c3d-4e7a-8b2f-1a9c0d4e5f6a"        # the same work
```

`dc:identifier` uses the Dublin Core element in its standard sense: an unambiguous reference to the resource. `sat:work` is a SAT-minted term under the `sat:` namespace; `dcterms:relation` and `dcterms:isVersionOf` were considered and rejected because they express pairwise pointers requiring N-way maintenance, where `sat:work` is a group key each expression states once.

### 2. Canonical home is the assets record; frontmatter carries a derived copy

The canonical home of both identifiers is the entity's identity record: `identity.yml` in the entity's role directory — `.<file_name>.assets/content/identity.yml` for documents (ADR-025). Identity never lives in `dc.yml`: the identifier is tool-minted and immutable, and `dc.yml` is the operator's editable file (ADR-021).

This covers every content type, including binaries that have no frontmatter.

For formats that carry frontmatter, tooling writes a derived copy of both fields into the frontmatter for human visibility and vector convenience. The assets record is authoritative; the frontmatter copy is regenerable. Divergence between the two is a validation error to surface, in the same class as orphaned assets directories — never silently repaired.

```yaml
# henson-aircraft-aluminum.md frontmatter (derived, regenerable)
dc:identifier: "urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e"
sat:work: "urn:uuid:018f2a91-6c3d-4e7a-8b2f-1a9c0d4e5f6a"
```

### 3. Format

Identifiers use UUID version 4 (random), expressed as a URN in lowercase:

```text
urn:uuid:7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e
```

UUID v4 is retained over UUID v7 on re-examination (2026-07). SAT is a filesystem archive with no database index to optimise, so v7's locality benefit does not apply; and for ingested historical content a v7 timestamp records tool-run time, not content time — an actively misleading value frozen into an identifier. Creation time already lives, honestly labelled, in the provenance record.

A conformant value matches, after the `urn:uuid:` prefix:

```text
^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$
```

The version nibble (4) and variant bits are validated. Uppercase hex digits are not accepted — the canonical form is lowercase.

### 4. Immutability, splits, and merges

`dc:identifier` is written once and never changed: not on copy, move, rename, or re-slug. If a document is split, the original retains its `dc:identifier` and the new document receives a new one; both may carry the same `sat:work` if they remain expressions of one work, or the new document starts a new work. If two documents are merged, the surviving document retains its identifiers and the retired expression's `dc:identifier` may be recorded in a `sat:identifier_retired` array for provenance. `sat:work` values are never retired by merges of expressions; a work outlives any one expression.

### 5. Cascade exceptions

`dc:identifier` and `sat:work` never inherit down the metadata cascade. An identifier identifies one entity; an inherited identifier is a correctness bug, not a convenience. Both join `dc:description` as canonical never-inherits exceptions.

### 6. Scope

Every entity — archive roots, collections, content directories, content files — receives `dc:identifier` at creation or ingress. `sat:work` appears only where cross-language correspondence is declared, which in practice means documents participating in a `mirrored` or equivalent relationship (ADR-011).

### 7. Relationship to Hugo translationKey

Hugo's `translationKey` field relates translations across independently-pathed content directories. The Hugo publishing vector emits `translationKey` set to the `sat:work` value at transmogrification time. The field belongs to the published output, not to the canonical record: the archive knows nothing of Hugo (ADR-017 boundary), and other vectors consume `sat:work` directly.

### 8. Generation and validation

Identifiers are generated by SAT tooling at creation or ingress, or by any RFC 9562 compliant UUID v4 generator when tooling is unavailable. Authors do not construct identifiers manually. Documents lacking `dc:identifier`, and mirrored documents lacking `sat:work`, are non-conformant and flagged by validation.

```python
import uuid
identifier = f"urn:uuid:{uuid.uuid4()}"
```

## Alternatives Considered

**A single identifier shared across translations** — the original form of this record: one `sat_uuid`, identical in every translation. Rejected on amendment because an identifier shared by two documents no longer identifies either: per-expression citation becomes impossible (citing the French expression specifically falls back to unstable paths), per-expression fixity has no unique subject, and merge semantics required retiring "identities" that were never singular. The original `sat_uuid` semantics — shared across translations — were in truth work identity, and survive renamed as `sat:work`; expression identity is the new field.

**UUID v7 (time-ordered)** — considered at drafting and re-examined on amendment. Rejected both times: no database index to optimise, and the embedded timestamp misrepresents ingested historical content. UUID v4 provides equivalent collision resistance without encoding a misleading time into identity.

**ULID** — rejected: not an IETF standard, thinner ecosystem, and its sorting advantage is irrelevant for filesystem archives.

**NanoID** — rejected: compactness in a metadata field is not a priority, and it sacrifices the universally recognised UUID format.

**Content-derived hash (SHA-256 of canonical content)** — rejected: identity must be stable across content revisions; a content-derived identifier changes on every edit and breaks correspondence.

**Path-as-identity extended across archives via naming convention** — rejected: cross-archive identity requires a join key independent of path; identical paths across archives contradict ADR-001 and ADR-008.

**`dcterms:relation` / `dcterms:isVersionOf` for correspondence** — rejected: pairwise pointers require each expression to name all others (N-way maintenance on every addition); `sat:work` is a group key stated once per expression. The concept is genuinely SAT's, so it carries the `sat:` prefix honestly.

**Frontmatter as the canonical home** — the original form of this record. Rejected on amendment: binaries have no frontmatter, and ADR-018 moved entity metadata out of content files deliberately. Frontmatter survives as a derived rendition.

**Using Hugo translationKey as the primary field** — rejected: `translationKey` is a Hugo field; coupling archive identity to one vector inverts the ADR-017 dependency direction. Hugo adopts the SAT value, never the reverse.

## Consequences

- Every entity carries `dc:identifier` in its role directory's `identity.yml`; mirrored documents additionally carry `sat:work` there
- Correspondence is computed by joining on `sat:work`; paths and names carry no identity
- Frontmatter copies are derived and regenerable; assets/frontmatter divergence is a validation error
- The Hugo vector emits `translationKey` from `sat:work` at transmog time; the canonical record is vector-ignorant
- `dc:identifier` and `sat:work` join `dc:description` as never-inherits cascade exceptions
- Creation tooling (satlib `plan_archive` and successors) assigns `dc:identifier` at creation; ingress tooling assigns it for ingested content
- Entities lacking `dc:identifier` are non-conformant and flagged by validation
- `dc:identifier` is the stable target for citations; `sat:work` is the stable target for "this document in your language" links
- The former `sat_uuid` field is retired; no migration is required as no conformant archives predate this amendment

## References

- ADR-001: Language as Filesystem Structure
- ADR-007: Entity Naming and Scoping via Hierarchical Semantic Containers
- ADR-008: Top-Level Repository Structure with Language-Scoped Archives
- ADR-011: SAT Collection Model
- ADR-017: Hugo Publishing Vector
- ADR-018: Universal Assets Directory Convention
- satlib Design and Rationale v0.2.0 (ratification rows 13–14)
- Internet Engineering Task Force. (2024). *Universally unique identifiers (UUIDs)* (RFC 9562). https://www.rfc-editor.org/rfc/rfc9562
- Hugo. (2026). *Multilingual mode — translationKey*. The Hugo Authors. https://gohugo.io/content-management/multilingual/

## Changelog

| Version | Status   | Notes                                                        |
| ------- | -------- | ------------------------------------------------------------ |
| 0.1.3   | Proposed | Decision 1 example paths corrected from the assets `dc.yml` to `content/identity.yml`, and the first Consequences bullet aligned to the role-directory identity record — completing the v0.1.2 change so the document agrees with itself throughout. |
| 0.1.2   | Proposed | Added - The canonical home of both identifiers is the entity's identity record: `identity.yml` in the entity's role directory — `.<file_name>.assets/content/identity.yml` for documents (ADR-025). Identity never lives in `dc.yml`: the identifier is tool-minted and immutable, and `dc.yml` is the operator's editable file (ADR-021). |
| 0.1.0   | Proposed | Single shared `sat_uuid` replaced by two-field model: per-expression `dc:identifier` plus shared `sat:work` (FRBR work/expression). Canonical home moved from frontmatter to the assets record per ADR-018, with frontmatter as a derived copy and divergence as a validation error. Identifier form set to `urn:uuid:` lowercase. UUID v4 re-examined against v7 and reaffirmed. Cascade never-inherits exception recorded. Hugo translationKey emission moved to the transmog boundary. |
