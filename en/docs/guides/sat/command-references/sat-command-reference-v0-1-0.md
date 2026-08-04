---
dc:title: "SAT Command Reference"
dcterms:version: "0.1.0"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:description: "A web-ready reference for the SAT command-line tools as they ship in release 0.8.0: each command, its options, and a worked example, with the options and help text captured from each tool's own --help output."
dcterms:created: "2026-08-04"
dcterms:modified: "2026-08-04"
dc:format: "text/markdown"
dc:language: "en"
sat:language_bcp47: "en"
dc:identifier: "sat-command-reference"
dcterms:rightsHolder: "Christopher Steel"
dc:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:version_at_creation: "0.8.0"
sat:changelog:
  - version: "0.1.0"
    date: "2026-08-04"
    author: "Christopher Steel"
    notes: "First version. Options and help text captured from each tool's --help in the installed 0.8.0 artifact on 2026-08-04; examples executed live against a scratch instance where noted; the collection wrapper routing gap and the provisional status of transmog recorded as found."
---

# SAT Command Reference

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## About this reference

This reference covers the SAT command-line tools as they ship in release 0.8.0. The options and descriptions were captured from each tool's own `--help` output in the installed 0.8.0 artifact on 2026-08-04, so the surface described here is the surface the release actually presents, not the surface the source tree may be moving toward.

A note on invocation. In 0.8.0 the standard installer places two dispatchers on your PATH, `sat` and `collection`. The `content` and `transmog` tools are invoked from the tool tree under `en/bin/`. Commands below are written by their tool name for readability; adjust the leading token to match how the tool is reached in your environment.

Three conventions recur across tools:

- `--dry-run` prints the plan and writes nothing. Preview first is the house habit.
- `--version` prints the tool version and exits.
- `--offline-confirm` gives explicit consent to proceed when the IANA subtag registry cannot be validated. Without a cache or a network, language-validating commands stop rather than guess.

## sat

The instance lifecycle tool. In 0.8.0 the wrapped, documented command is `init`.

### sat init

Instantiate a whole SAT instance in one command (ADR-026): the instance sat role, the dual-role collection role, one language archive per declared language, the children indexes at every parent, and seeded documentation, an example collection, and staged samples. An instance is instantiated once; a second run against the same target is refused, and nothing is written on refusal (ADR-021).

```text
sat init [--language TAG]... [--dry-run] [--offline-confirm] [--version] [path]
```

| Option | Meaning |
| --- | --- |
| `path` | target directory for the instance |
| `--language TAG` | language tag for an archive, repeatable |
| `--dry-run` | print the plan without writing |
| `--offline-confirm` | proceed without registry validation |
| `--version` | print the tool version and exit |

Example, preview then create:

```bash
sat init --dry-run --language en demo-instance
sat init --language en demo-instance
```

The operator identity fields (`dc:creator`, `dc:publisher`, `dc:rights`) come from the instantiation preseed at `~/.config/sat/instantiate-preseed.yml` if present, read once at creation; otherwise they remain `<calculated>` tripwires for you to resolve in the instance role's `dc.yml`. Below the instance there is no preseed: the cascade is the preseed.

## content

The document tool. Two subcommands: `init` mints an organizing directory's records, and `ingress` brings an arriving document under management.

### content init

Deliberately mint a content organizing directory's records (ADR-025): its content role identity, provenance, and sparse `dc.yml`, and a refresh of the enclosing archive's children index. A bare `mkdir` stays legal; this is the deliberate path.

```text
content init [--dry-run] [--version] [directory]
```

| Option | Meaning |
| --- | --- |
| `directory` | the content organizing directory |
| `--dry-run` | print the plan without writing |
| `--version` | print the tool version and exit |

Example:

```bash
content init en/docs/handbooks
```

### content ingress

Bring an arriving document under SAT management. It reads the document's frontmatter, catalogs its metadata against the resolved cascade (ADR-023), mints a write-once identity (ADR-021, ADR-022), writes the descriptive sidecar, provenance, and fixity, records the ingress event, and updates the work index. Markdown normalization (ADR-030) is not yet applied in 0.8.0.

```text
content ingress [--to DIR] [--expression-of ADDR] [--tree PATH | --archive LANG | --collection]
                [--date VALUE] [--dry-run] [--version] [document]
```

| Option | Meaning |
| --- | --- |
| `document` | a single document to catalog |
| `--to DIR` | promote a staged file into an archive location, then catalog it there (ADR-029). A directory path, not an archive tag; the filename is appended |
| `--expression-of ADDR` | declare the work this document expresses, as a file path, `dc:identifier`, or `sat:work` UUID |
| `--tree PATH` | batch: every document under a path |
| `--archive LANG` | batch: an entire language archive |
| `--collection` | batch: every archive in the collection |
| `--date VALUE` | operator-supplied `dc:date` fallback |
| `--dry-run` | print the plan and write nothing |
| `--version` | print the tool version and exit |

Example, catalog a single staged document into the top-level archive:

```bash
content ingress ../messy-source-sample.md --to en
```

Example, place a document into a nested path inside a collection's own language archive. The intermediate directories need not exist; SAT creates them and mints the content role on each on the way down:

```bash
content ingress ../messy-source-sample.md --to collections/test-collection/en/docs/my-directory
```

Where a document lands decides what it inherits: a document under a collection resolves the collection's metadata (cascade Tier 2), which a top-level document never sees. A document that states a field in its own frontmatter overrides any inherited value; the ingress record marks each field as `transcribed` from the document or `supplied` by the cascade. If a required field is `<calculated>` at every layer, ingress refuses and writes nothing.

The `dc:date` fallback resolves in order: transcribed from frontmatter, then `--date`, then the file's birth time where the platform exposes it, then ingress-time UTC recorded as a noted line.

## collection

The collection lifecycle and work-index tool.

Routing note for 0.8.0: the `collection` wrapper dispatches only `init` and `work`. The `reconcile`, `fixity`, and `mv` operations ship as scripts under `en/bin/collection/` but are not reachable through the `collection` command in this release; run them directly, for example `python en/bin/collection/collection-fixity.py --check`. Their options are documented below as captured from those scripts. Wiring these subcommands into the dispatcher is tracked as a Near-term item in the project ROADMAP.md.

### collection init

Create an additional single-role collection inside an existing instance (ADR-026): its collection role records, its declared archives, its children index, and a sparse `dc.yml` that inherits through the cascade. It refreshes the instance's children index to record the new collection.

```text
collection init [--language TAG]... [--dry-run] [--offline-confirm] [--version] [path]
```

| Option | Meaning |
| --- | --- |
| `path` | target directory for the collection |
| `--language TAG` | language tag for an archive, repeatable |
| `--dry-run` | print the plan without writing |
| `--offline-confirm` | proceed without registry validation |
| `--version` | print the tool version and exit |

Example:

```bash
collection init --language en collections/handbooks
```

### collection work

Work assignment, expression joining, and the work index (ADR-022). Three sub-actions: `join`, `find`, and `index`.

```text
collection work [--offline-confirm] {join,find,index} ...
```

| Sub-action | Meaning |
| --- | --- |
| `join` | join an existing document to a work; dry-run by default |
| `find` | find works by path or `dc:title` substring |
| `index --rebuild` | rebuild the work index |
| `index --check` | check the work index without writing |

Examples:

```bash
collection work join fr/produits/guide-rasoir.md --expression-of en/products/razor-guide.md
collection work find razor
collection work index --check
collection work index --rebuild
```

### collection reconcile

Repair a pairing that a plain `mv` broke (ADR-024). When an entity was renamed with plain `mv` and its assets kept the old name, reconciliation gathers evidence and proposes the repair; only `--apply` performs it. Dry-run by default.

```text
collection reconcile [--apply] [--version] [path]
```

| Option | Meaning |
| --- | --- |
| `path` | the tree to reconcile, default `.` |
| `--apply` | perform the proposed repairs |
| `--version` | print the tool version and exit |

Example (invoke the script directly in 0.8.0):

```bash
python en/bin/collection/collection-reconcile.py           # gather evidence, propose
python en/bin/collection/collection-reconcile.py --apply    # perform the repairs
```

### collection fixity

Check recorded digests, or export the manifest (ADR-027). Checking is deliberate and never writes; findings are classified. Export derives a `SHA256SUMS` manifest from the content sidecars, for use with coreutils and rclone.

```text
collection fixity [--check] [--export] [--version] [path]
```

| Option | Meaning |
| --- | --- |
| `path` | the tree to check or export, default `.` |
| `--check` | compare digests and report findings |
| `--export` | print `SHA256SUMS` to stdout |
| `--version` | print the tool version and exit |

Example (invoke the script directly in 0.8.0):

```bash
python en/bin/collection/collection-fixity.py --check
python en/bin/collection/collection-fixity.py --export > SHA256SUMS
```

### collection mv

Rename a collection safely (ADR-024): the collection and its assets directory move as one act, and the records that reference them, `sat:name` and the instance's children index, are maintained. Digests never change. Plain `mv` stays legal, and reconciliation repairs it. Dry-run by default.

```text
collection mv [--apply] [--version] [old] [new]
```

| Option | Meaning |
| --- | --- |
| `old` | the collection directory |
| `new` | the new collection name |
| `--apply` | perform the rename |
| `--version` | print the tool version and exit |

Example (invoke the script directly in 0.8.0):

```bash
python en/bin/collection/collection-mv.py collections/old-name new-name --apply
```

## transmog

The publishing vector (ADR-017): it transforms cataloged content into a chosen output format defined by a transmog definition file. This surface is provisional in 0.8.0, invoked from `en/bin/transmog/transmog.py` and driven by a definition rather than by named subcommands.

```text
transmog.py --definition PATH [--source DIR] [--output DIR] [--overwrite] [--dry-run]
```

| Option | Meaning |
| --- | --- |
| `--definition PATH` | the transmog definition file (`transmog.yml`) |
| `--source DIR` | override the source directory |
| `--output DIR` | override the output directory |
| `--overwrite` | overwrite existing output files |
| `--dry-run` | preview without writing |

Example:

```bash
python en/bin/transmog/transmog.py --definition en/bin/transmog/definitions/mkdocs-transmog.yml --dry-run
```

Confirm the definition path and behavior for your environment before relying on this in a demonstration; the transmog surface is expected to change.

## Other tools present in 0.8.0

These ship in the tool tree and are noted for completeness. Their surfaces are not covered in full here and were not exercised for this reference.

- `en/bin/archives/archive-init.py --archive-definition-path PATH [--dry-run]` — initialize an archive from a definition file.
- `en/bin/sat/sat-licence-check.py` and `en/bin/sat/sat-migrate.py` — licence checking and migration helpers, present alongside `sat init`.

## Verification status

Every options table and description in this reference was captured from the named tool's `--help` in the installed 0.8.0 artifact on 2026-08-04. The `sat init`, `content ingress` (single and nested `--to`), and `collection init` examples were executed live against a scratch instance on the same date. The `collection reconcile`, `fixity`, and `mv` help was captured by invoking the scripts directly, because the 0.8.0 `collection` wrapper does not route to them; that routing gap is stated in the collection section as found, not as a recommendation. The `transmog` surface is labelled provisional in place. The tools listed under "Other tools present" were not exercised.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | First version. Captured from each tool's `--help` in the installed 0.8.0 artifact; core examples executed live; the collection wrapper routing gap and transmog's provisional status recorded as found. |

## License

This document, *SAT Command Reference*, by **Christopher Steel**, with AI assistance from **Claude Opus 4.8 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).
