---
dc:title: "SAT Capabilities Showcase: Demo Runbook"
dcterms:version: "0.1.0"
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 4.8 (Anthropic)"
dc:description: "A timed fifteen-minute presenter script for a mixed decision-maker audience, covering the beats, the exact commands, the talking points, and the reset steps for demonstrating the SAT lifecycle from an empty directory to a published, integrity-checked archive."
dcterms:created: "2026-08-04"
dcterms:modified: "2026-08-04"
dc:format: "text/markdown"
dc:language: "en"
sat:language_bcp47: "en"
dc:identifier: "sat-capabilities-showcase--demo-runbook"
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
    notes: "First version. Beats and talking points authored for a mixed decision-maker audience; commands taken from the tool sources and the SAT Initialization Guide, with a verification-status section flagging the steps to confirm live."
---

# SAT Capabilities Showcase: Demo Runbook

Version: 0.1.0
Status: Draft
Style Guide: style-guide--versioned-documents-in-unrendered-markdown

## Audience and goal

This runbook drives a fifteen-minute live demonstration of SAT (Source Archive Tools) for a mixed, mostly non-technical audience: decision-makers, records owners, and the occasional engineer. The goal is not to teach the command line. The goal is to make one idea land: with SAT, governance happens at the moment content enters the archive, and the result is provably intact, richly described, correctly licensed, and ready to publish, without a cleanup project afterwards.

The narrative follows a single messy document through the whole lifecycle. Every step produces a visible, defensible outcome you can point at on screen. Keep the terminal large, the typing slow, and the talking points forward.

## The fifteen-minute arc

| Beat | Time | On screen | The point for the room |
| --- | --- | --- | --- |
| The problem | 0:00 to 1:00 | A folder of loose files with no metadata, no integrity, unclear rights | This is what unmanaged source costs you |
| Initialize | 1:00 to 3:00 | `sat init` builds a language-scoped archive; introduce automa | Rules that apply to everything, enforced, not a wiki nobody reads |
| Ingress | 3:00 to 7:00 | One messy document is normalized, catalogued, fingerprinted, and licensed automatically | Governance at the door, not as later cleanup |
| Collect | 7:00 to 10:00 | Related items grouped into a collection | Structure that scales past one file |
| Prove integrity | 10:00 to 12:00 | Tamper a file, SAT detects it | Provable trust and an audit trail |
| Publish | 12:00 to 14:00 | The same governed source becomes a browsable site | One trustworthy source, many outputs |
| Close | 14:00 to 15:00 | The same rules bind a human or an AI editor | Governance that travels with the content |

The two emotional peaks are Ingress (automatic cataloging) and Prove integrity (tamper detection). Slow down for both.

## Before you start

Do all of this before the audience is in the room. A cold start on stage is the most common way this demo fails.

Confirm the tool is installed and reporting the expected version:

```bash
sat --version
```

You should see the current release. This runbook was written against 0.8.0.

Work in a scratch directory so cleanup is a single delete:

```bash
cd /tmp && rm -rf sat-demo && mkdir sat-demo && cd sat-demo
```

Copy the two demo resources next to your scratch directory so they are within reach during the show. Both ship beside this runbook:

```bash
cp <this-repo>/en/docs/demos/sat-capabilities-showcase/resources/messy-source-sample.md .
cp <this-repo>/en/docs/demos/sat-capabilities-showcase/resources/demo-preseed.yml ~/.config/sat/instantiate-preseed.yml
```

The preseed answers the operator identity questions ahead of time so the creation run does not stop to ask. Review its values first; it is described in its own header comment.

Rehearse the whole arc once end to end against the scratch directory, then reset. Never demonstrate a path you have not just walked yourself.

## Beat one, the problem, one minute

Open the folder holding `messy-source-sample.md`. Show it plainly. Say this:

"Here is a real document. Nobody knows who wrote it, when, under what license, or whether it has been altered since. Multiply that by ten thousand files and you have most organizations' source material. Watch what SAT does to it."

Do not fix anything yet. The mess is the setup.

## Beat two, initialize, two minutes

Preview first. SAT writes nothing on a dry run, and it shows the full plan:

```bash
sat init --dry-run --language en demo-instance
```

Point at the plan. Say this:

"One command lays down a complete, language-scoped archive. The `en` here is not a folder someone remembered to make. Language is the structure. And nothing has been written yet, so I can look before I leap."

Now create it for real:

```bash
sat init --language en demo-instance
```

Then introduce the governing idea in one breath:

"Everything under here is now bound by what SAT calls automa: standing rules the tools apply automatically, every time, to everyone, human or machine. That is the difference between a policy and a guarantee."

## Beat three, ingress, four minutes, first peak

This is the heart of the demo. Preview the ingress so the room sees intent before effect:

```bash
content ingress ../messy-source-sample.md --to en --dry-run
```

Then perform it:

```bash
content ingress ../messy-source-sample.md --to en
```

Now show the result: the normalized document and its generated records side by side. Walk through what appeared without anyone typing it:

"The formatting was normalized to the house standard. A metadata record was catalogued, title, creator, date, language, rights, in a standard vocabulary. The document was given a stable identity that will never change, and a cryptographic fingerprint. And a license was attached. All of that happened at the door. No one will have to go back and do it later, because later never comes."

Let that sit. This is the moment the value is obvious even to someone who will never touch a terminal.

## Beat four, collect, three minutes

Group related material into a collection:

```bash
collection init --language en
```

Say this:

"A single document is a start. Real archives are sets: a report and its appendices, a series, a project's whole output. A collection is how SAT holds related items together as one governed thing, with its own identity and its own record of what belongs."

If you ingressed more than one sample, this is where you show them landing together.

## Beat five, prove integrity, two minutes, second peak

Ask the reconciler what it knows, then verify fingerprints:

```bash
collection reconcile
collection fixity --check
```

Everything reports clean. Now quietly tamper with a file. Change one character in the ingressed document in your editor, save, and run the check again:

```bash
collection fixity --check
```

It fails, and it names the file. Say this:

"I changed one character. SAT caught it and told me exactly where. This is what provable integrity means. You are not trusting that nothing was altered; you can demonstrate it, on demand, to an auditor or to yourself in five years."

Restore the file (or note that you will reset), and move on while the point is still ringing.

## Beat six, publish, two minutes

Turn the governed source into something a reader opens. SAT's publishing step (the transmog vector, ADR-017) transforms the same records into a chosen output format such as a static site:

```bash
transmog --help
```

Show the available output vectors, run the one you rehearsed, and open the result in a browser. Say this:

"Same source, one command, a browsable site. And because the metadata and licensing travel with the content, the published output carries them too. One trustworthy source, many outputs, nothing retyped."

Confirm the exact transmog subcommand and flags during rehearsal, and pin them into this runbook once verified for your environment.

## Beat seven, close, one minute

Land the through-line:

"You watched a loose, anonymous file become a described, fingerprinted, licensed, publishable archive object, in one sitting, with almost no manual work. The rules that made that happen apply the same way whether a person or an AI does the next edit. That is governance that travels with the content, instead of living in a document nobody reads. That is SAT."

Stop there. Do not add a features list. The demonstration was the argument.

## Reset and teardown

Between runs, and at the end, remove the scratch instance and its collection in one step, because the default collections home sits inside the instance:

```bash
cd /tmp && rm -rf sat-demo
```

Confirm nothing survived:

```bash
find /tmp -maxdepth 3 -name ".*.assets" 2>/dev/null
```

This should print nothing. If a preseed pointed the collections home outside the instance, remove that path separately. Do not run the teardown against any directory holding real content: instance identity and provenance records are write-once, and there is no undo.

## If something goes wrong

If `sat --version` fails, the repository-root virtual environment is missing or the wrong one is active; see the SAT Initialization Guide's troubleshooting section before the audience arrives, never during.

If ingress or a collection command is not found on the path, invoke the tool from the repository (the `sat` and `collection` dispatchers install as wrappers, while `content` and `transmog` may be run from `en/bin/`); confirm the exact form during rehearsal.

If the integrity check does not fail after you tamper, you edited a copy rather than the ingressed file under the instance; edit the file inside the instance tree and re-run.

Have a screen recording of a clean run ready as a silent fallback. A recorded success beats a live failure.

## Command verification status

The initialize, verify, and teardown commands are taken from the SAT Initialization Guide, which records them as executed against a scratch instance on 2026-08-04. The ingress, collection, and fixity command shapes are taken from the tool sources (`content-ingress.py`, `collection-init.py`, `collection-reconcile.py`, `collection-fixity.py`) on 2026-08-04. The publish step names the transmog vector but does not pin a subcommand, because the exact form was not executed for this document; confirm it with `transmog --help` and update this runbook in place once verified for the demo environment.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | First version. Fifteen-minute arc, beats, talking points, and reset for a mixed audience; commands sourced from tool code and the Initialization Guide, with the publish step flagged for live confirmation. |

## License

This document, *SAT Capabilities Showcase: Demo Runbook*, by **Christopher Steel**, with AI assistance from **Claude Opus 4.8 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).
