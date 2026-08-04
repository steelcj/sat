---
dc:title: "SAT Initialization Guide"
dc:description: "How to instantiate a SAT instance with sat init: prerequisites, a write-free preview, the creation run, verification of the resulting records, the optional instantiation preseed, and cleanup of a test instance."
dc:creator: "Christopher Steel"
dc:contributor: "Claude Opus 5 (Anthropic)"
dc:publisher: "Christopher Steel"
dc:date: "2026-08-04"
dc:modified: "2026-08-04"
dc:type: "Text"
dc:format: "text/markdown"
dc:language: "en"
dc:language_bcp47: "en"
dc:rights: "https://creativecommons.org/licenses/by-sa/4.0/"
dc:subject:
  - SAT
  - initialization
  - sat init
  - instantiation
  - user guide
dc:identifier: "sat-initialization-guide"
---

# SAT Initialization Guide

Version 0.1.1. Status: Draft.

## Description

`sat init` instantiates a SAT instance as a whole chain in one command: the instance's sat role, the dual-role collection role, one language archive per declared language, the children indexes at every parent, and seeded content. It is governed by [ADR-026](../../architecture/adrs/adr-026-full-chain-creation-the-instantiation-preseed-and-seeding-v0-2-3.md).

Two things happen that are worth knowing before you run it.

The command always seeds an example collection, and by default also seeds documentation and staged sample content. We keep this on by default because a fresh install doubles as a standing integration test — if seeding fails, the install is broken and you want to know immediately, not later. The preseed can turn the documentation and sample content off; the example collection is created either way.

An instance can be instantiated exactly once. `sat init` refuses to run against a directory that already holds a sat-role `identity.yml` or `provenance.yml`, and writes nothing when it refuses ([ADR-021](../../architecture/adrs/adr-021-stable-identity-at-creation.md)). Re-initialisation is an error, not a merge.

There are two ways to supply the instance's answers. Without a preseed, `sat init` uses command-line arguments and tool self-discovery, and leaves operator identity fields as `<calculated>` tripwires for you to fill in. With an instantiation preseed at `~/.config/sat/instantiate-preseed.yml`, those answers arrive already resolved in the instance role's `dc.yml`. The preseed is read once, at creation, and never again — it is not part of read-time resolution. Start without one; add it when you are creating instances often enough that retyping the answers is a nuisance.

## Before you start

### Ensure for venv

The `sat` dispatcher requires a Python virtual environment at the repository root, not inside `en/`. Ensure that it exists:

```bash
SAT_ROOT=`pwd`
echo $SAT_ROOT
python3 -m venv ${SAT_ROOT}/.venv/bin/sat --prompt "sat"
source .venv/bin/sat/bin/activate
pip install -r ./en/lib/satlib/satlib.requirements.txt
which pip
sat --version
```

#### venv confirmation

```bash
content
```

expected output

```bash
usage: content <init|ingress> [options]
```

### Ensure for python

The `sat` dispatcher requires a Python virtual environment at the repository root, not inside `en/`. Check that it exists:

```bash
ls "$SAT_ROOT/.venv/bin/python3"
```

Replace `$SAT_ROOT` with the repository root — the directory three levels above `en/bin/sat/`. If this path does not exist, the dispatcher fails immediately; see the troubleshooting section.

The repository root must contain a `VERSION` file. Its contents are written into every provenance record as `tool_version`. Check it:

```bash
cat "$SAT_ROOT/VERSION"
```

The IANA Language Subtag Registry cache must be present, or the machine must have network access. Language tags are validated against it and creation stops if validation cannot be performed. Check the cache:

```bash
ls -la ~/.config/sat/cache/iana-registry.txt ~/.config/sat/cache/iana-registry-meta.yml
```

A cache older than 30 days is refreshed automatically when the network is reachable; if the refresh fails, the stale cache is used with a warning, because a stale cache is better than no validation.

The target directory must not already be a SAT instance. Check that no sat-role identity record exists:

```bash
ls "<target>/.<target-name>.assets/sat/identity.yml"
```

The assets directory name is the literal transform of the target directory's own name — a directory called `demo-instance` carries `.demo-instance.assets` ([ADR-018](../../architecture/adrs/adr-018-universal-assets-directory-convention-v0-1-1.md)). A "No such file or directory" result here is what you want.

## Preview the instantiation

`sat init` creates directories and records outside the target as well as inside it — the example collection lands under the instance's collections home. Always preview first. `--dry-run` prints the full plan and writes nothing.

```bash
sat init --dry-run --language en <target>
```

Captured output from a real run against a scratch directory:

```text
registry:  fresh (File-Date: 2026-06-14)
PLAN: instantiate SAT instance at /tmp/scratchpad/demo-instance
  /tmp/scratchpad/demo-instance/.demo-instance.assets/sat/          identity, provenance, dc, children, fixity (instance role)
  /tmp/scratchpad/demo-instance/.demo-instance.assets/collection/   identity, provenance, dc (sparse), collection.yml, children, fixity
  /tmp/scratchpad/demo-instance/en/  archive: eng / en
  /tmp/scratchpad/demo-instance/en/docs/  seeded documentation
  /tmp/scratchpad/demo-instance/collections/test-collection/  example collection (always), staged samples
registry File-Date: 2026-06-14
No records were written (--dry-run).
```

The instance path in this capture has been shortened for readability; everything else is verbatim.

A correct plan ends with `No records were written (--dry-run).` and names every location the real run will touch. Read the list and confirm you recognise each path — particularly the collections home line, since that is the one outside the target directory you named.

Signs something is wrong: a `registry:` line reading anything other than `fresh` or `stale` warrants a look at the cache before continuing; an archive line missing for a language you passed means the tag did not validate; no plan at all means the command exited before planning, and the error text above it explains why.

Confirm the preview wrote nothing:

```bash
ls <target>
```

This should report that the directory does not exist, unless you created it yourself beforehand.

## Create the instance

Run the same command without `--dry-run`:

```bash
sat init --language en <target>
```

Pass `--language` once per archive you want. Omit it entirely and the tool self-discovers the language from its own filesystem context, printing `language: <tag> (tool self-discovery)` when it does; if self-discovery finds nothing, the command stops and asks you to pass `--language`.

Captured output from a real run:

```text
registry:  fresh (File-Date: 2026-06-14)
INSTANTIATED: SAT instance at /tmp/scratchpad/demo-instance
  en: [unresolved: dc:creator, dc:publisher, dc:rights]
  collections/test-collection/  seeded
registry File-Date: 2026-06-14
NOTE: <calculated> fields remain; set instance defaults in /tmp/scratchpad/demo-instance/.demo-instance.assets/sat/dc.yml
```

The `unresolved` list and the closing `NOTE` are expected on a first run without a preseed. They are not errors. They report that three fields are still `<calculated>` tripwires — a hole no shallower layer may cover, which the cascade will keep reporting until you state a value.

## Verify the result

Check that the records were written where they belong:

```bash
find <target> -maxdepth 3 -name "*.assets" -o -maxdepth 3 -name "*.yml" | sort
```

Captured from the real run above, abridged to the record files:

```text
./.demo-instance.assets/collection/children.yml
./.demo-instance.assets/collection/collection.yml
./.demo-instance.assets/collection/dc.yml
./.demo-instance.assets/collection/fixity.yml
./.demo-instance.assets/collection/identity.yml
./.demo-instance.assets/collection/provenance.yml
./.demo-instance.assets/sat/children.yml
./.demo-instance.assets/sat/dc.yml
./.demo-instance.assets/sat/fixity.yml
./.demo-instance.assets/sat/identity.yml
./.demo-instance.assets/sat/provenance.yml
./en/.en.assets/archive
./en/docs/.docs.assets
./en/docs/.getting-started.md.assets
```

Two things to confirm here. The root carries two role directories — `sat` and `collection` — because the instance root is dual-role. And every assets directory is named after the entity it belongs to: `.demo-instance.assets` inside the instance, `.en.assets` inside the archive, `.getting-started.md.assets` beside the seeded document.

Now resolve the tripwires. Open the instance role's canonical metadata record:

```bash
$EDITOR <target>/.<target-name>.assets/sat/dc.yml
```

Captured contents immediately after creation:

```text
sat:name: demo-instance
sat:collections_home: collections
dc:creator: <calculated>
dc:publisher: <calculated>
dc:rights: <calculated>
dc:description: ''
```

Replace each `<calculated>` with a real value. These are operator identity fields, and they inherit down the whole tree — what you write here is what every archive, collection, and document below the instance resolves to unless it states otherwise.

The values you set here become part of the published metadata of everything in the instance. `dc:creator` and `dc:publisher` are attribution written into records that travel with the archive; `dc:rights` is the licence those records assert. Set them deliberately rather than copying an example, and treat them as public.

## Using an instantiation preseed

Skip this section on a first install. It is worth setting up once you are creating instances repeatedly.

Create the preseed file:

```bash
$EDITOR ~/.config/sat/instantiate-preseed.yml
```

The keys `sat init` actually reads are the following. This list is taken from the tool's source rather than from a shipped template, because no `instantiate-preseed.yml.example` ships today — the examples directory contains `sat-preseed.yml.example` and `collection-preseed.yml.example`, which are different files serving different purposes.

```yaml
languages:
  - en
  - fr
dc:creator: "Your Name"
dc:publisher: "Your Name"
dc:rights: "https://creativecommons.org/licenses/by-sa/4.0/"
collections_home: collections
seed:
  documentation: true
  sample_content: true
```

Every key is optional. `languages` is used only when you pass no `--language` argument, since command-line arguments override the preseed, which overrides self-discovery. The three `dc:` fields fill the tripwires you would otherwise edit by hand. `collections_home` sets where the example collection and future collections live, relative to the instance. Setting either `seed` key to `false` skips that seeding; the example collection itself is created regardless.

This file holds your name and licence choice in plain text in your home directory, and those values are copied into records that ship with every instance you create. That is the point of it, but it means the file is operator identity, not configuration trivia — keep it out of any directory you sync or publish.

A malformed preseed does not stop creation. The tool prints a warning to stderr and proceeds as though the file were absent, which means an instance created from a broken preseed looks successful but carries `<calculated>` tripwires instead of your values. Watch for a `[SAT WARNING] could not read` line, and verify `dc.yml` after any run where you changed the preseed.

## Troubleshooting

### The dispatcher cannot find its interpreter

Symptom, captured verbatim:

```text
en/bin/sat/sat: line 14: /home/initial/2-areas/development/sat-mapping/.venv/bin/python3: No such file or directory
```

The exit status is 127.

Cause: the `sat` dispatcher hardcodes `$SAT_ROOT/.venv/bin/python3`, where `$SAT_ROOT` is three directories above `en/bin/sat/`. This was reproduced in a checkout that has a virtual environment at `en/lib/satlib/.venv` but none at the repository root. The dispatcher does not fall back to a system interpreter or to the satlib environment.

Fix: create the virtual environment at the repository root, with `satlib` installed into it.

### Provenance records say the tool version is unknown

Symptom: a freshly created `provenance.yml` reads, captured verbatim:

```text
created: '2026-08-04T16:52:26+00:00'
tool: sat init
tool_version: unknown
registry_file_date: '2026-06-14'
```

Cause: the tool reads its version from a `VERSION` file at the repository root, and returns the literal string `unknown` when that file is absent. This was reproduced in a checkout with no root-level `VERSION` file. Creation succeeds, so nothing warns you at the time.

Fix: add the `VERSION` file before creating instances you intend to keep. This repository now carries one declaring `0.7.0`; a run against it records `tool_version: 0.7.0`, confirmed by creating a scratch instance after the file was added. Records written before the fix keep `unknown` — provenance is write-once, so the value is not corrected by a later run.

### The target is already an instance

Symptom, captured verbatim:

```text
[SAT ERROR] REFUSED: /tmp/scratchpad/demo-instance/.demo-instance.assets/sat/identity.yml exists. An instance is instantiated once (ADR-021). No records were written.
```

The exit status is 1. The instance path in this capture has been shortened for readability.

Cause: `sat init` was run a second time against a directory that already holds a sat-role identity record. This is the designed refusal, not a fault.

Fix: choose a different target directory, or remove the existing instance first — see cleanup below. The refusal message is accurate that nothing was written, so the existing instance is untouched.

### Language validation cannot be performed

This entry is derived from reading the tool's source and has not been reproduced. Treat the exact output as unconfirmed.

With no registry cache present and no network access, `sat init` stops rather than guessing. Without `--offline-confirm` it exits with an error naming the cache and suggesting the flag. With `--offline-confirm` it does not currently succeed either: the code path that would proceed unvalidated returns no registry content, and the command then reports that unvalidated operation is not yet supported by this CLI and exits 1.

The practical consequence is that a working registry cache or a reachable network is a hard requirement today, and `--offline-confirm` does not substitute for one. Restore network access or copy a valid `iana-registry.txt` and its meta file into `~/.config/sat/cache/`.

## Cleanup

A test instance leaves two things behind: the instance directory itself, and the example collection under its collections home. When the collections home is inside the instance directory — the default `collections` — removing the instance directory removes both.

Remove a test instance:

```bash
rm -rf <target>
```

Confirm the removal took effect, including the records that make the directory an instance:

```bash
ls -d <target> 2>&1
find "$(dirname <target>)" -maxdepth 2 -name ".*.assets" 2>/dev/null
```

The first command should report that the directory does not exist. The second should print nothing; if it prints an assets directory, an instance or collection survived the removal — most likely because the preseed set `collections_home` to a path outside the instance directory, in which case remove that path separately.

Do not use this on an instance holding real content. There is no undo, and the identity and provenance records are write-once — a removed instance cannot be recreated with the same identity.

## Verification status

The procedure sections were executed against a scratch directory on 2026-08-04: the dry run, the creation run, the re-run refusal, and the resulting record tree are captured output from those runs, with instance paths shortened for readability. The preseed section was not executed; its key list is read from the tool's source. The language-validation troubleshooting entry was not reproduced and is labelled as such in place.

## Changelog

| Version | Status | Notes |
| --- | --- | --- |
| 0.1.0 | Draft | First version. Procedure verified against a scratch instance; preseed keys taken from `sat-init.py`; three troubleshooting entries reproduced, one derived from source and flagged. |
| 0.1.1 | Draft | Version troubleshooting entry updated: the repository now carries a root `VERSION` file declaring `0.7.0`, verified to reach `tool_version` in a fresh provenance record. |

## Licence

Copyright (C) 2026 Christopher Steel

This file is part of SAT (Source Archive Tools).

SAT is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

SAT is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License along with SAT. If not, see <https://www.gnu.org/licenses/>.

This document was prepared with AI assistance from **Claude (Anthropic)**.
