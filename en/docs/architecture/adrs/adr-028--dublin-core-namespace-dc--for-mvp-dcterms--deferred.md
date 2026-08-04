# ADR-028: Dublin Core Namespace — dc: for MVP, dcterms: Deferred

Version: 0.1.0
Status: Proposed
Style Guide: web-ready-unrendered-markdown-using-apa-7-v0.2.0.md

---

## Context

SAT content currently carries a mix of `dc:` and `dcterms:` prefixed metadata across its corpus. Two conflicting sources of truth exist for which namespace should be used:

1. The versioned-documents guide (v0.3.0) states directly: "Use `dcterms:` throughout. The legacy `dc:` prefix is deprecated in SAT."
2. The MVP decision, confirmed by the project owner, was `dc:` throughout, on the grounds that SAT metadata is stored as YAML, not RDF.

No record of the `dcterms:` deprecation decision could be located in this project's accessible history. The `dc:` decision is independently supported by a standing radar entry, *Dublin Core Metadata Usage in SAT*, which documents the namespace choice and its rationale in detail (see References), and which has been promoted from `assess` to `adopt` on that basis.

The technical distinction between the two namespaces is real, not cosmetic. `dc:` (`http://purl.org/dc/elements/1.1/`) is the original fifteen-property Dublin Core Metadata Element Set, defined without domains or ranges. `dcterms:` (`http://purl.org/dc/terms/`) is a parallel, formally-typed set of the same fifteen properties, introduced by DCMI in 2008 specifically so that RDF implementations gained typed properties without breaking existing `dc:` consumers. Certain `dcterms:` properties carry real obligations if honored — `dcterms:creator` and `dcterms:contributor` are typed as `Agent`, meaning a describable resource with its own identifier, not a plain string — and several others (`date`, `type`, `format`, `language`) carry recommended encoding schemes (W3C-DTF, DCMI Type Vocabulary, IMT, BCP 47).

None of this typed machinery currently applies to SAT. Content is YAML frontmatter read by a regex-based conformance checker, not RDF, XML, or JSON-LD. Every `dcterms:creator` value in the corpus today is a plain literal string. Adopting `dcterms:` names without adopting RDF serialization or Agent-typed values would use the more precise namespace's vocabulary while ignoring the precision it exists to provide.

## Decision

SAT uses the `dc:` namespace prefix throughout its metadata for the MVP.

Where a needed term has no `dc:` equivalent — `dcterms:created` for creation dates is the current example — the `dcterms:` refinement is used explicitly, with its full prefix, and the exception is noted at the point of use rather than treated as a silent default.

This decision supersedes the versioned-documents guide's current statement that `dc:` is deprecated. The guide is to be corrected to reflect this ADR (see follow-up).

Two related questions are explicitly deferred, not resolved here:

- **Agent-typed properties.** Whether `dc:creator` / `dc:contributor` should ever be modeled as resources with identifiers rather than plain strings is an open question, tracked separately, not blocking this decision.
- **Encoding schemes.** Adoption of W3C-DTF, DCMI Type Vocabulary, IMT, and BCP 47 as formal encoding conventions for `date`, `type`, `format`, and `language` is tracked as a set of tooling-correction backlog items (see References), not as a namespace decision.

## Consequences

**Positive:**

- Removes the direct contradiction between the versioned-documents guide and actual repository practice before the metadata project begins building on it.
- Avoids RDF-conformance obligations (Agent typing, encoding-scheme validation) that SAT's YAML/regex tooling is not built to honor, without pretending those obligations don't exist — they're deferred and named, not ignored.
- `dc:` is shorter, more widely recognized outside RDF contexts, and sufficient for a YAML key-value system that makes no RDF-compliance claim.

**Negative / trade-offs:**

- If SAT metadata is ever serialized as real RDF, XML, or JSON-LD, this decision will need formal revisiting, and any content written under it will need review for `Agent`-typing and encoding-scheme compliance at that point.
- The mixed presence of `dcterms:created` alongside `dc:` elsewhere means SAT is not purely single-namespace; this must be documented clearly wherever the convention is taught, to avoid the appearance of inconsistency.
- The `dcterms:`-only style already present in some newer documents (e.g. `uc-radar-entry-template-v0.2.0.md`) will need reconciliation — either migrated to `dc:` for consistency, or explicitly scoped as belonging to a different, non-SAT-MVP document family. This ADR does not resolve which.

## Follow-up

- Correct the versioned-documents guide (v0.3.0) to remove the `dc:` deprecation language and cite this ADR.
- Reconcile the `dcterms:`-only radar/uc-radar templates against this decision, or document why they're out of scope.
- Track Agent-typing and encoding-scheme items as they surface; six known tooling-correction items are already logged on the UC Kanban backlog (tag `sat`).

## References

- Radar entry (adopted): *Dublin Core Metadata Usage in SAT*, `uc-radar/en/docs/radar/adopt/metadata/dublin-core-metadata-usage-in-sat-v0.1.2.md` (radar entries live in the separate uc-radar project)
- DCMI Usage Board. (2020). *DCMI metadata terms*. Dublin Core Metadata Initiative. https://www.dublincore.org/specifications/dublin-core/dcmi-terms/
- Hillmann, D. (2005). *Using Dublin Core: The elements*. Dublin Core Metadata Initiative. https://www.dublincore.org/specifications/dublin-core/usageguide/elements/
- ADR-003: IANA Language Subtag Registry as Authoritative Source (referenced precedent for encoding-scheme handling)

---

## Changelog

| Version | Status | Notes |
|---------|--------|-------|
| 0.1.0 | Proposed | Initial draft, citing adopted radar entry as evidentiary basis |

---

**License**

This document, *ADR-028: Dublin Core Namespace — dc: for MVP, dcterms: Deferred*, by Christopher Steel, with AI assistance from Claude, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).