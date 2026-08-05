---
dc:title: "SAT Capabilities Showcase: Demo Runbook"
dcterms:version: "0.1.1"
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
  - version: "0.1.1"
    date: "2026-08-04"
    author: "Christopher Steel"
    notes: "Captured real command outputs through the ingress beat; added the metadata-cascade section (parent-layer inheritance, per-document override, and the <calculated> tripwire) and a section on placing content into a collection's nested language archive with the collection-tier cascade contrast, all verified live against a scratch instance created with the installed 0.8.0 tool."
  - version: "0.1.0"
    date: "2026-08-04"
    author: "Christopher Steel"
    notes: "First version. Beats and talking points authored for a mixed decision-maker audience; commands taken from the tool sources and the SAT Initialization Guide, with a verification-status section flagging the steps to confirm live."
---

# SAT Capabilities Showcase: Demo Runbook

Version: 0.1.1
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

### venv setup

Make certain to set up your venv before the demo starts: [sat-initialization-guide.md](../../guides/sat/sat-initialization-guide.md#ensure-for-venv)

#### venv confirmation

```bash
content
```

Output

```bash
usage: content <init|ingress> [options]
```

Confirm SAT tools are is installed and reporting the expected version:

```bash
sat --version
```

You should see the current release. This runbook was written against 0.8.0.

```bash
sat-tools 0.8.0
```
Move into your sat repo

example:
```bash
cd /home/initial/2-areas/development/sat
```
Save repo home 

```bash
SAT_REPO=`pwd`
echo ${SAT_REPO}
```

Work in a scratch directory so cleanup is a single delete:

```bash
cd /tmp && rm -rf sat-demo && mkdir sat-demo
cd -
cd /tmp/sat-demo
```

Copy the two demo resources next to your scratch directory so they are within reach during the show. Both ship beside this runbook:

Copy our messy example:

```bash
cp ${SAT_REPO}/en/docs/demos/sat-capabilities-showcase/resources/messy-source-sample.md .
```

Copy our preseed

```bash
cp ${SAT_REPO}/en/docs/demos/sat-capabilities-showcase/resources/demo-preseed.yml ~/.config/sat/instantiate-preseed.yml
```

The preseed answers the operator identity questions ahead of time so the creation run does not stop to ask. Review its values first; it is described in its own header comment.

Have a look at the preseed:

```bash
nano ~/.config/sat/instantiate-preseed.yml
```

Rehearse the whole arc once end to end against the scratch directory, then reset. Never demonstrate a path you have not just walked yourself.

## Beat one, the problem, one minute

Open the folder holding `messy-source-sample.md`. Show it plainly.

```bash
typora messy-source-sample.md
```

 Say this:

"Here is a real document. Nobody knows who wrote it, when, under what license, or whether it has been altered since. Multiply that by ten thousand files and you have most organizations' source material. Watch what SAT does to it."

Do not fix anything yet. The mess is the setup.

## Beat two, initialize, two minutes

Preview first. SAT writes nothing on a dry run, and it shows the full plan:

```bash
sat init --dry-run --language en demo-instance
```

Dry run output

```bash
registry:  fresh (File-Date: 2026-06-14)
preseed:   /home/initial/.config/sat/instantiate-preseed.yml
PLAN: instantiate SAT instance at demo-instance
  demo-instance/.demo-instance.assets/sat/          identity, provenance, dc, children, fixity (instance role)
  demo-instance/.demo-instance.assets/collection/   identity, provenance, dc (sparse), collection.yml, children, fixity
  demo-instance/en/  archive: eng / en
  demo-instance/en/docs/  seeded documentation
  demo-instance/collections/test-collection/  example collection (always), staged samples
registry File-Date: 2026-06-14
No records were written (--dry-run).
```

Point at the plan. Say this:

"One command lays down a complete, language-scoped archive. The `en` here is not a folder someone remembered to make. Language is the structure. And nothing has been written yet, so I can look before I leap."

Now create it for real:

```bash
sat init --language en demo-instance
```

Output example:

```bash
registry:  fresh (File-Date: 2026-06-14)
preseed:   /home/initial/.config/sat/instantiate-preseed.yml
INSTANTIATED: SAT instance at demo-instance
  en: [clean]
  collections/test-collection/  seeded
registry File-Date: 2026-06-14
```

Then introduce the governing idea in one breath:

"Everything under here is now bound by what SAT calls automa.



> automa: standing rules the tools apply automatically, every time, to everyone, human or machine. That is the difference between a policy and a guarantee."

### Create instance

```bash
tree
.
├── demo-instance
│   ├── collections
│   │   └── test-collection
│   │       ├── en
│   │       │   └── sample.md
│   │       └── staging
│   │           ├── bienvenue.md
│   │           ├── note-de-service.md
│   │           └── welcome.md
│   └── en
│       └── docs
│           └── getting-started.md
└── messy-source-sample.md

```

## Beat three, ingress, four minutes, first peak

This is the heart of the demo. Preview the ingress so the room sees intent before effect:

Show our messy example document

```bash
ls -al 
```

output:

```bash
drwxrwxr-x  3 initial initial  4096 Aug  4 22:33 .
drwxrwxrwt 31 root    root    32768 Aug  4 22:30 ..
drwxrwxr-x  5 initial initial  4096 Aug  4 22:33 demo-instance
-rw-rw-r--  1 initial initial  1426 Aug  4 22:29 messy-source-sample.md
```



Now lets ingress our messy document:

```bash
# ingress to sat instance: demo-instance/en
content ingress messy-source-sample.md --to demo-instance/en/my-directory --dry-run

# ingress to test collection: demo-instance/collections/test-collection/en
content ingress messy-source-sample.md --to demo-instance/collections/test-collection/en --dry-run
```

Output example:  Ingress to a the SAT instances archive

```bash
PLAN: promote /tmp/sat-demo/messy-source-sample.md -> demo-instance/en/messy-source-sample.md, then catalog
No changes were made (--dry-run).
```

Output example: Ingress to English archive in an archive collection

```bash
PLAN: promote /tmp/sat-demo/messy-source-sample.md -> demo-instance/collections/test-collection/en/messy-source-sample.md, then catalog
No changes were made (--dry-run).
```

Then perform it:

```bash
content ingress messy-source-sample.md --to demo-instance/en/my-directory
```

Output

```bash
CATALOGED: /tmp/sat-demo/demo-instance/en/my-directory/messy-source-sample.md
```

Lets take a peek at our file 

```bash
typora /tmp/sat-demo/demo-instance/en/my-directory/messy-source-sample.md
```



### Automa cascade

That simple command above hides a lot of details of exactly what happens with a document is ingressed.

A process of normalization takes place its generated records side by side. Walk through what appeared without anyone typing it:

Set our sidecar file path

```bash
SIDECAR_PATH=/tmp/sat-demo/demo-instance/en/my-directory/.messy-source-sample.md.assets
echo ${SIDECAR_PATH}
```



#### metadata

Our SAT is configured to use Dublin Core Metadata, lets take a look at it:

##### dublin core

```bash
cat ${SIDECAR_PATH}/content/dc.yml
```

##### dublin core output example just after ingress:

> dublin core formatting was normalized to the house standard. A metadata record was catalogued, title, creator, date, language, rights, in a standard vocabulary."

```bash
dc:creator: SAT Demo Presenter
dc:description: ''
dc:date: '2026-08-04'
dc:publisher: SAT Demo Presenter
dc:rights: https://creativecommons.org/licenses/by-sa/4.0/
dc:language: eng
dc:language_bcp47: en
dc:type: Collection
```

#### fixity

```bash
cat ${SIDECAR_PATH}/content/fixity.yml
```

Output example:

```bash
# messy-source-sample.md/.messy-source-sample.md.assets/content/fixity.yml
#
#   Written at creation, updated by deliberate operations.
#   Recorded digests; a mismatch is a fixity finding (ADR-027).
#
records:
  identity.yml:
    algorithm: sha256
    digest: 4ed00bad0781cb9727bf4937c2f3d99ac4200d9246a67caef1e8ffa7ad0420ec
  provenance.yml:
    algorithm: sha256
    digest: 46eec274866ca99d4f2c9ab0d0f10a4a0a931ed34c2575ff0871f480c3ff15e7
content:
  algorithm: sha256
  digest: 7104a90f12cf47b4421334cf60377f3be6dfdc580a8be14ab1bd5d24ace35c06
  size: 1495
recorded: '2026-08-04T20:33:47Z'
recorded_by:
  command: content ingress
  version: 0.8.0
```

#### an identity

```bash
cat ${SIDECAR_PATH}/content/identity.yml
```

output example:

````bash
dc:identifier: urn:uuid:a49a2b5c-4aaf-4bc9-b3c6-acf2c1bbc305
sat:work: urn:uuid:b29707c1-de6e-4e76-a500-08d66d1ecb3b
````

#### ingress

We have a record of ingress for the document

```bash
cat ${SIDECAR_PATH}/content/ingress/ingress-2026-08-04T20-33-47Z.yml 
```

Content example:

```bash
sat_version: '0.1'
recorded: '2026-08-04T20:33:47Z'
recorded_by:
  command: content ingress
  version: 0.8.0
source: en/messy-source-sample.md
frontmatter_present: false
origins:
  dc:creator: supplied
  dc:description: supplied
  dc:date: supplied
  dc:publisher: supplied
  dc:rights: supplied
  dc:language: supplied
  dc:language_bcp47: supplied
  dc:type: supplied
noted:
  date_fallback:
    value: '2026-08-04'
    source: ingress-time-utc
    reason: no transcribed dc:date, no --date, st_birthtime unavailable
findings:
- kind: markdown-hard-line-wrap
  what: a paragraph is hard-wrapped across multiple source lines
  means: prose should flow on one line per paragraph; mdformat preserves manual line
    breaks rather than reflowing them
  evidence:
    line: 1
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
- kind: markdown-hard-line-wrap
  what: a paragraph is hard-wrapped across multiple source lines
  means: prose should flow on one line per paragraph; mdformat preserves manual line
    breaks rather than reflowing them
  evidence:
    line: 14
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
- kind: markdown-hard-line-wrap
  what: a paragraph is hard-wrapped across multiple source lines
  means: prose should flow on one line per paragraph; mdformat preserves manual line
    breaks rather than reflowing them
  evidence:
    line: 20
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
- kind: markdown-horizontal-rule
  what: a horizontal rule appears in content
  means: horizontal rules are presentational and not used in well-formed SAT markdown
    content
  evidence:
    line: 36
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
- kind: markdown-hard-line-wrap
  what: a paragraph is hard-wrapped across multiple source lines
  means: prose should flow on one line per paragraph; mdformat preserves manual line
    breaks rather than reflowing them
  evidence:
    line: 40
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
- kind: markdown-hard-line-wrap
  what: a paragraph is hard-wrapped across multiple source lines
  means: prose should flow on one line per paragraph; mdformat preserves manual line
    breaks rather than reflowing them
  evidence:
    line: 44
  do: normalize the prose to well-formed SAT markdown, or leave as a recorded finding
    for author attention
  severity: soft
original_frontmatter: ''
```

#### provenance

```bash
cat ${SIDECAR_PATH}/content/provenance.yml 
```

Output example:

```bash
created: '2026-08-04T20:33:47+00:00'
tool: content ingress
tool_version: 0.8.0
registry_file_date: null
```

"The formatting was normalized to the house standard. A metadata record was catalogued, title, creator, date, language, rights, in a standard vocabulary. The document was given a stable identity that will never change, and a cryptographic fingerprint. And a license was attached. All of that happened at the door. No one will have to go back and do it later, because later never comes."

Let that sit. This is the moment the value is obvious even to someone who will never touch a terminal.

## Beat three deepened, steer the metadata through the cascade

The records you just saw were not typed by hand, and they were not read from the file. The document arrived with no frontmatter, `frontmatter_present: false` in its ingress record, yet its `dc.yml` came out with a creator, a publisher, a date, a licence, and a language. Those values resolved down what SAT calls the metadata cascade, and the cascade is where you steer a document's description without touching the document body. For a fifteen-minute run, show one of the three adjustments below; for a longer session, show all three.

### How the cascade resolves

SAT resolves a document's metadata through ordered layers, shallow to deep, and the deepest concrete value wins (ADR-025):

| Tier | Layer | Where you set it |
| --- | --- | --- |
| 1 | Instance | the sat role's `dc.yml` at the instance root |
| 2 | Collection | the owning collection's `dc.yml` |
| 3 | Archive | the language archive's `dc.yml`, with its `language.yml` |
| 4 | Content directories | any organizing directory's `dc.yml` below the archive |
| 5 | The document | the document's own `content/dc.yml`, beside the file |

#### Examples:

```bash
# SAT Instance
nano demo-instance/.demo-instance.assets/sat/dc.yml
# SAT Demo Collection
demo-instance/.demo-instance.assets/collection/dc.yml
# Demo Test Collection
demo-instance/collections/test-collection/.test-collection.assets/collection/dc.yml
# Demo Test English Archive
demo-instance/collections/test-collection/en/.en.assets/archive/dc.yml
# Ingress Demo
demo-instance/en/my-directory/.my-directory.assets/content/dc.yml
```

Three field states travel through those layers, and this is worth saying out loud to the room:

- A concrete value resolves, and a deeper layer can override it.
- An empty string is a real, deliberate value that wins like any other.
- `<calculated>` is a hole, a deliberate tripwire. It never wins over a concrete value, and if it is still a hole after every layer, SAT refuses rather than guesses.

One field is exempt on purpose. `dc:description` is never inherited, because a description describes one thing, not its descendants. That is why the ingressed document showed `dc:description: ''`. The cascade will fill a licence for you; it will never invent a description.

### Adjustment one, change a default once, and every document below follows

Suppose the licence for everything in this instance should change. Set it in one place, the instance layer, then ingress a fresh document that says nothing of its own:

```bash
$EDITOR .demo-instance.assets/sat/dc.yml     # set dc:rights to CC BY 4.0
printf 'A second note\n\nNo metadata of its own.\n' > ../second-note.md
content ingress ../second-note.md --to en
```

The new document inherits the new default, without being told:

```bash
grep dc:rights en/.second-note.md.assets/content/dc.yml
```

```text
dc:rights: https://creativecommons.org/licenses/by/4.0/
```

Say this:

"I changed the licence in one place, at the top, and every document that does not say otherwise now resolves to it. That is policy by inheritance, not a find and replace across ten thousand files."

### Adjustment two, let a single document speak for itself

A document overrides any inherited value by carrying its own. Ingress one that states its licence in frontmatter:

```bash
cat > ../own-rights.md <<'EOF'
---
dc:title: "Locally Licensed Note"
dc:rights: "https://creativecommons.org/publicdomain/zero/1.0/"
---

This one carries its own rights.
EOF
content ingress ../own-rights.md --to en
```

Its own licence wins over the instance default, and the ingress record marks where each value came from:

```bash
grep -E 'dc:rights|dc:title' en/.own-rights.md.assets/content/dc.yml
```

```text
dc:title: Locally Licensed Note
dc:rights: https://creativecommons.org/publicdomain/zero/1.0/
```

```text
origins:
  dc:title: transcribed
  dc:rights: transcribed
  dc:creator: supplied
```

Say this:

"The deepest layer wins, so a document can always speak for itself. And SAT records the provenance of every field, transcribed from the document or supplied by the cascade. You can always answer where a value came from."

Because ingress freezes the resolved record into the document's own `dc.yml`, and fixity guards the identity, provenance, and content but not the metadata record, you can also adjust one document after the fact by editing its `dc.yml` directly. That is the right place, and the only place, to give a document the description the cascade will not infer for you.

### Adjustment three, the tripwire that refuses to guess

This is the governance point that lands hardest. Make the instance licence a hole, then try to ingress a document that states no licence of its own:

```bash
$EDITOR .demo-instance.assets/sat/dc.yml     # set dc:rights to <calculated>
printf 'A third note with no rights anywhere.\n' > ../third-note.md
content ingress ../third-note.md --to en
```

```text
[CONTENT ERROR] cascade tripwire: dc:rights: still <calculated> after cascade resolution — a tooling error, not a fallback
```

Nothing was written; there is no `en/.third-note.md.assets` to find. Say this:

"A required field had no answer at any layer. SAT did not invent one, and it did not quietly leave it blank. It stopped, named the field, and wrote nothing. A system that fills holes silently is a system you cannot trust. This one refuses."

Restore the instance licence before you move on:

```bash
$EDITOR .demo-instance.assets/sat/dc.yml     # restore dc:rights to a real value
```

## Beat four, collect, three minutes

Group related material into a collection:

```bash
collection init --language en
```

Say this:

"A single document is a start. Real archives are sets: a report and its appendices, a series, a project's whole output. A collection is how SAT holds related items together as one governed thing, with its own identity and its own record of what belongs."

If you ingressed more than one sample, this is where you show them landing together.

### Placing content inside a collection, and the collection tier of the cascade

Content does not only land in the top-level archive. A collection has its own language archive, and `--to` takes a directory path, not just an archive tag, so a document can go anywhere beneath it. The intermediate directories need not exist: SAT creates them and mints the content role on each directory on the way down. Give `--to` the directory only; the file keeps its own name.

```bash
content ingress ../messy-source-sample.md --to collections/test-collection/en/docs/my-directory
```

```text
CATALOGED: .../collections/test-collection/en/docs/my-directory/messy-source-sample.md
```

Here is the point worth making, and it is the cascade again. A document inside a collection resolves the collection's own metadata (Tier 2), which a top-level document never sees. Set a licence on the collection, then ingress one document into the collection and one into the top-level archive:

```bash
$EDITOR collections/test-collection/.test-collection.assets/collection/dc.yml   # set dc:rights to CC BY-NC 4.0
content ingress ../messy-source-sample.md --to collections/test-collection/en/docs/my-directory
printf 'A top-level note.\n' > ../toplevel-note.md
content ingress ../toplevel-note.md --to en
```

The two documents, in the same instance, resolve different licences, decided entirely by where they live:

```text
# collections/test-collection/en/docs/my-directory/.messy-source-sample.md.assets/content/dc.yml
dc:rights: https://creativecommons.org/licenses/by-nc/4.0/

# en/.toplevel-note.md.assets/content/dc.yml
dc:rights: https://creativecommons.org/licenses/by-sa/4.0/
```

Say this:

"Same instance, two documents, two different licences, and nobody set the licence on either document. Where a document lives decides what it inherits. That is how you govern a whole set of related material by describing the set once, at the collection, instead of every file by hand."

## BEGIN UNTESTED AND UNIMPLEMENTED TERRITORY

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

The initialize, verify, and teardown commands are taken from the SAT Initialization Guide, which records them as executed against a scratch instance on 2026-08-04. The ingress, collection, and fixity command shapes are taken from the tool sources (`content-ingress.py`, `collection-init.py`, `collection-reconcile.py`, `collection-fixity.py`) on 2026-08-04. The publish step names the transmog vector but does not pin a subcommand, because the exact form was not executed for this document; confirm it with `transmog --help` and update this runbook in place once verified for the demo environment. The metadata-cascade section was executed live on 2026-08-04 against a scratch instance created with the installed 0.8.0 tool; the inheritance, override, and tripwire outputs shown there are captured from that run.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.2 | Draft | Added additional information and cleaned up tests and added examples of where the cascade for metadata can be altered |
| 0.1.1 | Draft | Captured real command outputs through the ingress beat; added the metadata-cascade section (inheritance, per-document override, and the `<calculated>` tripwire) and a section on placing content into a collection's nested language archive with the collection-tier contrast, verified live against a scratch 0.8.0 instance. |
| 0.1.0 | Draft | First version. Fifteen-minute arc, beats, talking points, and reset for a mixed audience; commands sourced from tool code and the Initialization Guide, with the publish step flagged for live confirmation. |

## License

This document, *SAT Capabilities Showcase: Demo Runbook*, by **Christopher Steel**, with AI assistance from **Claude Opus 4.8 (Anthropic)**, is licensed under the [GNU Affero General Public License v3.0 or later](https://www.gnu.org/licenses/agpl-3.0.html).
