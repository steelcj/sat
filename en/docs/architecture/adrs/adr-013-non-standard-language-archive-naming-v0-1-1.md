# ADR-013: Non-Standard Language Archive Naming Convention

```yaml
status: Accepted
date: 2026-05-20
amended: 2026-07-10 (assets convention; ratified vocabulary; language field dropped; see Amendments)
version: 0.1.1
```

## Context

ADR-001 establishes that language is declared by the filesystem directory name at the archive root. ADR-003 establishes the IANA Language Subtag Registry as the authoritative validation source. ADR-005 defines the non-authority path for archives whose language cannot be validated against the IANA registry — cases where `sat:authority: none` applies and an authority note documents the reason.

What none of the earlier ADRs defines is what the directory name itself should look like when the language is outside the IANA registry. This gap has consequences at every layer of the system:

- The directory name is the structural language declaration (ADR-001). Its form must be consistent and unambiguous.
- The `dc:language_bcp47` field in the archive's language record must carry a valid BCP 47 representation. For non-IANA languages this requires a private-use tag. The relationship between the directory name and the BCP 47 tag must be defined.
- Discovery (ADR-005) identifies language archive roots by their names. Non-standard archives must be identifiable as roots without a registry hit, or created archives become undiscoverable.
- ADR-002's mixed-language archive naming convention uses underscore as the separator between language tags. Any non-standard language identifier must compose cleanly with that convention.
- The validation pipeline must be able to identify non-standard archives without a registry lookup, both for efficiency and for offline operation.

The cases that require a non-standard naming convention include:

- **Dialect and regional variants with no registered subtag** — a regional variant of American Sign Language, a dialectal variant of Scots Gaelic, community-identified language forms that predate or fall outside standardisation.
- **Constructed and institutional languages** — Esperanto is registered (`eo`); a community-specific constructed language may not be.
- **Historical and extinct languages not in the registry** — some historical forms have registered codes; others do not.
- **Non-human communication systems** — the humpback songs case. BCP 47 explicitly scopes language tags to human communication. SAT takes a broader archival view — non-human communication systems are valid archive subjects, and BCP 47 private-use tags are the appropriate mechanism even where BCP 47's own scope excludes the subject.
- **Mixed-authority content** — a bilingual archive containing both an IANA-registered language and a non-standard one, requiring the mixed naming convention from ADR-002 to accommodate both.

## The BCP 47 Private-Use Mechanism

BCP 47 (RFC 5646) provides a private-use tag mechanism via the singleton `x`. There are two forms:

**Whole-tag private use** — `x` as the primary subtag, followed by one or more private-use subtags, each separated by hyphens: `x-asl-west`, `x-humpback-songs`. The interpretation of all subsequent subtags is entirely by private agreement.

**Appended private use** — private-use subtags appended to an existing registered tag: `en-x-twain`, `und-x-asl-west`. The registered tag provides the base; the private subtags narrow it by private agreement.

Private-use subtags must consist solely of letters and digits and must not exceed eight characters per subtag. `x-humpback-songs` is valid: `humpback` is eight characters, `songs` is five.

### The CLDR constraint

BCP 47 permits whole-tag private use with `x` as the primary subtag. However, the Unicode Common Locale Data Repository (CLDR) imposes an additional restriction: a tag must not start with the subtag `x`. A private-use sequence is only accepted after a language subtag such as `und`. CLDR-based tools — most internationalisation libraries and browser implementations — may reject `x-asl-west` and require `und-x-asl-west`, where `und` is the IANA-registered tag for undetermined language.

This is a significant practical constraint. SAT archives feed publishing vectors, and publishing vectors use web standards tooling. A `dc:language_bcp47` of `x-asl-west` may fail in exactly the systems the interoperability field exists to serve.

### W3C guidance

The W3C advises that private-use subtags be used with great care and avoided where possible, since they interfere with the interoperability BCP 47 exists to promote. SAT's use of private-use tags for genuine non-standard cases is exactly the scenario the mechanism exists for, but the guidance reinforces the principle that IANA-registered tags are used wherever they exist.

## Decision

### 1. Non-standard archive directory names use the sat-x- prefix

Non-standard language archive directories — those whose language cannot be validated against the IANA registry — use the prefix `sat-x-` followed by the community name of the language, with hyphens as word separators:

```text
sat-x-asl-west/
sat-x-humpback-songs/
sat-x-ulster-scots-gaelic/
```

The `sat-x-` prefix is a SAT-specific convention that is visually distinct from IANA-registered tags (`en/`, `fr-CA/`) and from BCP 47 whole-tag private-use tags (`x-asl-west`). It signals immediately in the filesystem that this is a SAT non-standard archive without requiring any file to be opened — ADR-001's declare-through-structure principle applied to non-standardness itself.

The community's name for the language survives inside the tag body (underscores become hyphens per the character constraints); the exact original spelling may be recorded in `dc:title` or the authority note.

### 2. Rationale for sat-x- over x-

Using the BCP 47 whole-tag private-use form directly as the directory name — `x-asl-west/` — was the primary alternative considered, and was briefly the implemented behaviour. It is rejected for three reasons.

First, the CLDR constraint. If `dc:language_bcp47` carries `x-asl-west`, publishing vectors using CLDR-based internationalisation libraries fail. This affects Hugo, browser rendering, and most modern web tooling.

Second, separator collision with ADR-002. Community names may themselves contain underscores (`humpback_songs`), and underscore is ADR-002's tag separator. A mixed archive `en_humpback_songs/` is genuinely ambiguous — two tags or three? The `sat-x-` form uses only hyphens internally, so `en_sat-x-humpback-songs/` parses without ambiguity.

Third, discovery. A bare community name (`humpback_songs/`) fails the language pattern test, so the discovery walk (ADR-005) passes over the very archive the tool created — created but not rediscoverable. The `sat-x-` prefix is a structural marker the pattern test recognises without a registry lookup.

### 3. The dc:language_bcp47 field carries the und-x- form

The archive's language record carries the CLDR-compatible representation: the IANA-registered `und` (undetermined) as the primary subtag, followed by the private-use sequence.

```yaml
# sat-x-asl-west/.sat-x-asl-west.assets/language.yml
dc:language: "und"
dc:language_bcp47: "und-x-asl-west"
sat:authority: "none"
sat:authority_note: "Regional ASL variant, no registered subtag exists"
```

```yaml
# sat-x-humpback-songs/.sat-x-humpback-songs.assets/language.yml
dc:language: "und"
dc:language_bcp47: "und-x-humpback-songs"
sat:authority: "none"
sat:authority_note: "Humpback whale vocalisation archive — outside BCP 47 human communication scope"
```

`dc:language` defaults to `und` — the honest machine value when no ISO 639-2 mapping exists; the tool never guesses. Where a close registered code exists (for `sat-x-asl-west`, `ase` approximates American Sign Language broadly), the operator may set it explicitly, with the authority note documenting the precision of the approximation. The tool proposes, the operator refines.

The directory name is the canonical SAT identifier and is not duplicated into the record: the assets pairing (ADR-018) already binds record to archive, and a third copy of the name inside a file is a divergence waiting to happen. SAT tools operate on the directory name; publishing vectors consume `dc:language_bcp47` for HTML `lang` attributes, hreflang links, and search indexing.

### 4. The assets directory follows the archive directory name

The universal assets convention (ADR-018) applies unchanged. The assets directory name is derived mechanically from the archive directory name; renames are tool-mediated and atomic across the pairing.

```text
sat-x-asl-west/
  .sat-x-asl-west.assets/
    dc.yml
    language.yml
    provenance.yml
```

### 5. Mixed archives containing non-standard languages

ADR-002's underscore separator applies as with any other tag:

```text
en_sat-x-asl-west/           ← English and non-standard ASL variant
fr-CA_sat-x-ulster-scots/    ← Quebec French and non-standard Ulster Scots
```

The underscore remains unambiguous as the tag separator because `sat-x-` names use only hyphens internally. The corresponding assets directory follows mechanically:

```text
en_sat-x-asl-west/
  .en_sat-x-asl-west.assets/
```

### 6. Validation pipeline identification

The validation pipeline identifies non-standard archives by the `sat-x-` prefix without a registry lookup. Any directory name beginning with `sat-x-` is routed directly to the non-authority path: `sat:authority: none`, `dc:language_bcp47` in `und-x-` form, note required. This holds online and offline. All other directory names take the registry-backed path.

### 7. Character constraints

Non-standard language names in the `sat-x-` system satisfy constraints derived from BCP 47 private-use subtag rules and filesystem portability:

- Each hyphen-separated component after `sat-x-` consists solely of ASCII letters and digits
- Each component does not exceed eight characters
- The full directory name is valid on all major filesystems: Linux, macOS, Windows, and common archive formats
- Spaces are not permitted
- Lowercase by convention, consistent with BCP 47 primary subtag casing

```text
sat-x-asl-west            valid: asl (3), west (4)
sat-x-humpback-songs      valid: humpback (8), songs (5)
sat-x-new-guinea-pidgin   valid: new (3), guinea (6), pidgin (6)
sat-x-verylongname        invalid: verylongname (12) exceeds eight characters —
                          use sat-x-verylong or find a shorter community-agreed name
```

## Alternatives Considered

**`x-asl-west/` as the directory name directly** — rejected, after briefly being the implemented behaviour (satlib, 2026-07). CLDR-based tools reject whole-tag private use; community names containing underscores collide with the ADR-002 separator; and no structural marker distinguishes the form for discovery.

**`und-x-asl-west/` as the directory name** — considered because it is the CLDR-compatible form. Rejected because `und` signals undetermined language, which is not accurate for an archive whose language is known — it is simply unregistered. The `sat-x-` prefix is semantically accurate: a SAT-defined non-standard identifier, not an undetermined language. The `und-x-` form is the correct *field* representation, not the correct *name*.

**Community name without any prefix (`asl_west/`, `humpback_songs/`)** — briefly the implemented behaviour, valued for community sovereignty over the name. Rejected because no structural marker distinguishes it from a future registered tag or from a mixed expression; it is invisible to discovery; and underscores in community names are ambiguous against ADR-002. Community sovereignty survives inside the tag body and in `dc:title`.

**`local-` or `private-` prefixes** — rejected because they are not grounded in any external standard. `sat-x-` is grounded in BCP 47's `x-` private-use convention, making the lineage explicit.

**Requiring registration of private-use tags** — not actionable. BCP 47 private-use tags require no registration; the mechanism is designed for private agreement, and SAT's use is exactly that.

## Consequences

- Non-standard language archives use `sat-x-{community-name}/` as the directory name
- `dc:language_bcp47` carries `und-x-{community-name}` for CLDR compatibility; `dc:language` defaults to `und` with operator refinement permitted
- The directory name is the canonical SAT identifier; it is not duplicated into any record
- The validation pipeline routes `sat-x-` names to the non-authority path without a registry lookup; discovery recognises them as language archive roots structurally
- Mixed archives combine `sat-x-` names with standard tags using the ADR-002 underscore separator without ambiguity
- The assets directory name follows mechanically per ADR-018; renames are tool-mediated
- Name components are ASCII letters and digits, maximum eight characters per hyphen-separated component
- satlib requires alignment: the non-authority generator emits `sat-x-` directories and `und-x-` tags; the parser accepts appended private use; discovery short-circuits on the prefix (queued with the ISO 639-2 membership fix)
- The language validation specification section 4 and ratification row 8 are superseded accordingly

## Amendments

| Date | Change |
|------|--------|
| 2026-07-10 | Metadata structure updated from `.{name}_meta/` to the assets convention (ADR-018); `language_authority` vocabulary replaced by ratified `sat:authority` levels; redundant `language:` field dropped — the directory name is the sole declaration; `dc:language` rule stated as default `und` with explicit operator refinement; separator-collision and discovery arguments added to the rationale from implementation experience; satlib alignment recorded as a consequence. Status Proposed → Accepted. |
| 2026-07-12 | `born.yml` renamed to `provenance.yml` per ADR-020. |

## References

- ADR-001: Language as Filesystem Structure
- ADR-002: Mixed Language Archive Naming Convention
- ADR-003: IANA Language Subtag Registry as Authoritative Source
- ADR-005: Tool Self-Discovery from Filesystem Context (as amended)
- ADR-011: SAT Collection Model (as amended)
- ADR-018: Universal Assets Directory Convention
- SAT Language Validation and Offline Registry Cache Specification v0.1.0 (section 4 superseded)
- Internet Engineering Task Force. (2009). *Tags for identifying languages* (RFC 5646 / BCP 47). https://www.rfc-editor.org/rfc/rfc5646
- World Wide Web Consortium. (2024). *Choosing a language tag*. https://www.w3.org/International/questions/qa-choosing-language-tags
- Unicode Consortium. (2024). *Unicode locale data markup language (LDML)*. https://www.unicode.org/reports/tr35/
