---
dc:title: "SAT Capabilities Showcase: Value Brief"
dcterms:version: "0.1.0"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:description: "A one-page, plain-language brief for the room during a SAT demonstration: the problem SAT solves, the guarantees it provides, the five things the audience will see, and why each one matters to a decision-maker. No command line."
dcterms:created: "2026-08-04"
dcterms:modified: "2026-08-04"
dc:format: "text/markdown"
dc:language: "en"
sat:language_bcp47: "en"
dc:identifier: "sat-capabilities-showcase--demo-value-brief"
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
    notes: "First version. Plain-language, no-CLI brief for a mixed decision-maker audience, paired with the demo runbook."
---

# SAT Capabilities Showcase: Value Brief

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## The problem

Most organizations sit on a large pile of source material: reports, guides, records, published pages, and the documents behind them. For most of it, four simple questions have no reliable answer. Who created this? When? Under what license may we use it? Has it been altered since? When those answers are missing, every downstream use carries risk, and cleaning it up later becomes a project that is always scheduled and never done.

## What SAT does

SAT (Source Archive Tools) applies governance at the moment content enters the archive, not as a cleanup afterwards. The rules are called automa: standing rules the tools apply automatically, every time, to everyone, whether a person or an AI system is doing the work. The result is source material that is described, intact, correctly licensed, and ready to publish, by default rather than by effort.

## What you will see

In about fifteen minutes, one deliberately messy document walks the full lifecycle, and each step leaves a visible result.

- **A governed home appears.** One command builds a structured, language-aware archive. Structure is not left to whoever remembered to make a folder.
- **The document is catalogued at the door.** As it enters, SAT normalizes its formatting, records its metadata in a standard vocabulary, gives it a permanent identity, and attaches the right license, automatically.
- **Related items become a set.** A collection holds related documents together as one governed thing, so the model scales past a single file.
- **Integrity is provable.** A single altered character is detected and named. You do not have to trust that nothing changed; you can demonstrate it, on demand.
- **Publishing is one step.** The same governed source becomes a browsable site, carrying its metadata and licensing with it. One source, many outputs, nothing retyped.

## Why it matters

| The guarantee | What it removes |
| --- | --- |
| Metadata captured at ingress | The cleanup project that never happens |
| Permanent identity and provenance | Ambiguity about what a document is and where it came from |
| Cryptographic integrity checking | Blind trust that nothing has been altered |
| License attached at ingress | Uncertainty about how content may be used |
| Rules applied to human and AI alike | Governance that depends on everyone remembering |

## The one idea to take away

Governance that happens at the door is cheaper, safer, and more trustworthy than governance you promise to do later. SAT makes the door the enforcement point, and the guarantees travel with the content from there on.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | First version. One-page value brief for a mixed audience, paired with the demo runbook. |

## License

This document, *SAT Capabilities Showcase: Value Brief*, by **Christopher Steel**, with AI assistance from **Claude Opus 4.8 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).
