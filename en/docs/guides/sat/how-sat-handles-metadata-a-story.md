# how SAT handles metadata: a story

You configure SAT with Dublin Core as the canonical metadata because it is easy to write, well-standardized, and covers the basics, a great MVP setting.

SAT then accumulates and resolves content metadata *as* DC, and every generated shape (Hugo frontmatter, Open Graph, Schema.org, a PDF's XMP) is derived from that canonical DC metadata by default.

But SAT needs to know things about itself, and about your content, that Dublin Core has no vocabulary for.

Those live in SAT's own namespace, `sat:`, the operational and infrastructure metadata for SAT itself.

Here is an example of some SAT metadata:

```yaml
# SAT's own metadata, the sat: namespace
sat:uuid: "7f3ac291-4b2e-4d1a-9c8f-3e2b1a0d5c6e"  # stable identity
sat:repository: "sat"                             # which repo it lives in
sat:path: "en/docs/design/"                       # where in the archive
sat:language_bcp47: "en"                          # archive language tag
sat:work: "translation-join-key"                  # joins expressions across languages (ADR-022)
sat:version_at_creation: "0.7.0"                  # SAT version when created
sat:migration_status: "pre-sat"                   # ingress/migration state
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-04"
    author: "Christopher Steel"
    notes: "…"
```

And here is some Dublin Core metadata, the `cascade.yml` under `dublin-core/` that sets the SAT-level defaults:

```yaml
# .<instance>.assets/sat/metadata/dublin-core/cascade.yml
# SAT-level Dublin Core defaults, the top of the cascade.
# Sparse on purpose: only the values every document should inherit
# unless it decides otherwise.
dc:publisher: "UniversalCake"
dcterms:rightsHolder: "Christopher Steel"
dc:rights: >
  CC-BY-SA-4.0
```

These three are not a random pick. Publisher and rights, and the rights-holder that travels with them, are exactly the fields SAT's cataloging policy expects the *cascade* to supply rather than the document to carry. A document almost never restates its publisher; it inherits it. Set these once here, at the top, and every piece of content below gets them for free.

## one file per tier, and why the root is not resolved

Every tier writes exactly one file per metadata family, and it is always the same file: `cascade.yml`, the values that tier *states*. It is sparse, you write only what this tier decides, and it is the one thing that lives on disk. There is no second `resolved.yml` sitting beside it, and that is deliberate.

The resolved metadata, the full answer after inheritance, is not stored at all. It is computed at read time, in memory, whenever something actually needs it. Storing it would just be a cache that can drift out of step with the sources, which is the exact problem the cascade exists to prevent.

This is also why the root has no resolved anything. SAT is the ultimate parent; nothing sits above it, so there is nothing for it to resolve *from*. The root's `cascade.yml` is simply *set*, by automation, by an operator, or from SAT's built-in defaults. Because everything lives below it, what it states is the defaults for the whole instance. A collection, an archive, a directory, and a document each add their own `cascade.yml` on top; the root just happens to be the one with no parent to inherit from.

The same logic governs SAT's own namespace. At the root, the `sat:` values are configuration and defaults, set, not resolved. Further down, a document's `sat:` metadata is mostly its own per-entity facts (its `sat:uuid`, its `sat:path`), which is why some of it never cascades at all: a uuid is nobody's default but its own.

## how the cascade actually runs

The cascade is a running fold, one tier at a time:

```text
resolved(tier) = merge( resolved(parent) , cascade.yml(tier) )
```

Each tier takes its parent's resolved view, carried in memory, lays its own `cascade.yml` on top, and passes the result down to its children. The root is the base case: it has no parent, so `resolved(root)` is just its own `cascade.yml`. Every tier's resolved view becomes the inherited baseline for the tier below it, which is the precise sense in which defaults flow downward.

The merge is not pure replacement. Scalar values (title, publisher, rights) override, deepest-stated-wins: the nearest tier to state a value owns it. List values (`dc:subject`, `dc:relation`) accumulate: a lower tier's entries append to what it inherited rather than replacing them. So as metadata flows down, some fields get overwritten and others collect.

```text
root/cascade.yml        publisher=UniversalCake, rights=CC-BY-SA-4.0, subject=[archives]
  en/cascade.yml        language=en
    design/cascade.yml   (empty, pure inherit)
      my-document        title=…, creator=…, subject=[metadata]

resolved(my-document) =  publisher=UniversalCake, rights=CC-BY-SA-4.0,
                         language=en, title=…, creator=…,
                         subject=[archives, metadata]   (accumulated, not replaced)
```

Where the resolved view is actually *consumed* is egress: when SAT generates an output for a document, it resolves down to that document and hands the in-memory result to the generator, which shapes it into Hugo frontmatter, DC HTML, a PDF's XMP, or whatever the vector needs.

One footnote for the implementer: you can compute that fold from either end and get the identical answer: stream *down* from the root accumulating, or start at the target document and walk *up* gathering each ancestor's `cascade.yml`, then apply deepest-stated-wins. SAT's resolver walks up, because that way it only computes the tiers the target actually depends on.

## the same shape as ingress, transmog, egress

Here is the pleasing part, and it is not a coincidence. Look at what one tier does: something arrives (the parent's resolved view), the tier reshapes it by folding in its own contribution, and it produces a new view for whatever comes next. That is ingress, transmog, egress, in miniature, the same three-beat move SAT makes at its outer boundary, running once per tier on the inside.

And it carries the same recursive signature we met at the system edge. Out there, one system's egress is the next system's ingress: the frontmatter SAT emits is what a downstream consumer captures. In here, one tier's egress is the next tier's ingress: the resolved view a tier produces is exactly what its child receives. The boundary pattern and the cascade pattern are the same pattern at two scales, across systems and across tiers, which is why once you understand the border you already understand the cascade.

## License

This document, *How SAT Handles Metadata: A Story*, by **Christopher Steel**, with AI assistance from **Claude (Anthropic)**, is licensed under the [Creative Commons Attribution-ShareAlike 4.0 License](https://creativecommons.org/licenses/by-sa/4.0/).
