dc:title: "Setting Up and Ingressing a Test Instance"
dcterms:version: "0.1.0"
dc:creator: "Christopher Steel"
dc:description: "A focused, task-first walkthrough: instantiate a SAT test instance with sat init, resolve its calculated instance defaults, and bring a directory of content under management with content ingress."
dcterms:created: "2026-08-02"
dcterms:modified: "2026-08-02"
dc:format: "text/markdown"
dc:language: "en"
sat:language_bcp47: "en"
dc:identifier: "setting-up-and-ingressing-a-test-instance"
dcterms:rightsHolder: "Christopher Steel"
dc:rights: >
  Copyright 2026 Christopher Steel.
  SPDX-License-Identifier: AGPL-3.0-or-later
sat:uuid: ""
sat:changelog:
  - version: "0.1.0"
    note: "First draft, validated against sat-tools 0.7.3."

# Setting Up and Ingressing a Test Instance

## Overview

This guide walks through three tasks end to end on an installed copy of SAT Tools: instantiating a throwaway test instance with `sat init`, resolving the instance defaults that instantiation leaves as holes, and bringing a whole directory of content under SAT management with `content ingress`. By the end you will have a working instance on disk, its descriptive defaults set once at the top so every document beneath inherits them, and a directory of markdown catalogued with identity, provenance, and fixity records written beside each file. The commands and output shown here were validated against `sat-tools 0.7.3`.

The instance created here is disposable. Everything lives under a single directory you choose (this guide uses `/tmp/test-instance`), so cleanup is a single `rm -rf` at the end and nothing outside that directory is touched.

## Prerequisites

Before starting, confirm the following:

- **SAT Tools 0.7.2 or later installed**, with the `sat` wrapper on your `PATH`. Verify with `sat init --version`, which should print `sat-tools 0.7.3` or newer. If it does not, install a current version with `install-sat.py --install`.
- **A validated language registry**, meaning either network access on first run so `sat init` can download the IANA Language Subtag Registry, or an existing cache at `~/.config/sat/cache/iana-registry.txt`. Instantiation refuses to write records against an unvalidated registry.
- **A shell with `~/.config/sat-tool/sat-tool.env` present**, written by the installer. The content commands below source it to find the active version.

## Create the test instance

Instantiate a new instance in one command, declaring `en` as its language:

```bash
sat init --language en /tmp/test-instance
```

A successful run reports the registry it resolved, the instance it created, and a note that some fields remain unresolved:

```text
registry:  fresh (File-Date: 2026-06-14)
INSTANTIATED: SAT instance at /tmp/test-instance
  en: [unresolved: dc:creator, dc:publisher, dc:rights]
  collections/test-collection/  seeded
registry File-Date: 2026-06-14
NOTE: <calculated> fields remain; set instance defaults in /tmp/test-instance/.test-instance.assets/sat/dc.yml
```

A fresh install is treated as a standing integration test, so `sat init` seeds a working whole rather than an empty shell. The important parts of the tree are:

```text
/tmp/test-instance/
  .test-instance.assets/
    sat/          instance role records (identity, provenance, dc.yml, ...)
    collection/   the instance is also a collection (dual role)
  en/             the instance's own language archive, with seeded docs/
  collections/
    test-collection/
      en/         a language archive holding sample.md
      staging/    arriving files awaiting promotion
```

Records live in hidden sibling directories named `.<name>.assets/<role>/`, never inside the content itself. The instance root carries two roles at once, `sat` and `collection`, which is why you see both under `.test-instance.assets/`.

## Configure the instance defaults

The `unresolved` line above is deliberate. Three descriptive fields, `dc:creator`, `dc:publisher`, and `dc:rights`, cannot be inferred by tooling, so instantiation records them as the placeholder `<calculated>` rather than guessing. Open the instance role's `dc.yml`:

```bash
$EDITOR /tmp/test-instance/.test-instance.assets/sat/dc.yml
```

Replace each `<calculated>` placeholder with a concrete value:

**Creators Note: Why is sat:collections_home: collections here?**

```yaml
sat:name: test-instance
sat:collections_home: collections
dc:creator: "Jane Operator"
dc:publisher: "Example Org"
dc:rights: "Copyright 2026 Example Org. SPDX-License-Identifier: CC-BY-4.0"
dc:description: 'A test instance for evaluating SAT content ingress.'
```

Setting these once at the instance root is enough for everything below it. SAT resolves descriptive metadata through a cascade, so a value stated at the instance is inherited by every collection, archive, and document beneath it unless a deeper layer overrides it. A field left as `<calculated>` at every layer is an unresolved hole, and verification surfaces it as an error, so resolving the three holes here is what makes the instance ready to catalog against.

If you would rather answer these before instantiation instead of after, write them into `~/.config/sat/instantiate-preseed.yml` as `dc:creator`, `dc:publisher`, and `dc:rights` keys, and `sat init` will fold them into the instance `dc.yml` at creation time. The preseed is read only at the instance level; below the instance, the cascade is the preseed.

## Ingress a directory of content

Ingress reads a document's frontmatter, catalogs it against the resolved cascade, mints its identity, and writes its descriptive sidecar, provenance, fixity, and an ingress record, then updates the work index. Arriving content is catalogued where it rests inside a language archive, so first place the directory you want to manage inside one. This guide uses a new `articles/` directory inside the seeded collection's `en` archive:

```bash
mkdir -p /tmp/test-instance/collections/test-collection/en/articles
# copy or write your .md files into that directory
```

The `content` tier is dispatched by Python and is not wrapped on your `PATH` (the installer wraps only `sat` and `collection`), so invoke it through the active version's virtual environment. Define a small helper for the session by sourcing the environment file the installer wrote:

```bash
. "$HOME/.config/sat-tool/sat-tool.env"
content() { "$SAT_TOOL_ROOT/.venv/bin/python3" "$SAT_TOOL_ROOT/en/bin/content/content.py" "$@"; }
```

Preview the batch first. The `--tree` scope walks every markdown document under a path, and `--dry-run` prints the plan while writing nothing:

```bash
content ingress --tree /tmp/test-instance/collections/test-collection/en/articles --dry-run
```

For each document the plan shows the descriptive fields it resolved and the records it would write:

```text
PLAN: content ingress .../articles/first-post.md
  frontmatter present: True
  descriptive fields:  dc:creator, dc:description, dc:date, dc:publisher, dc:rights, dc:language, dc:language_bcp47, dc:type
  would write: content/identity.yml, dc.yml, provenance.yml, fixity.yml, an ingress record, and the work index
No changes were made (--dry-run).
```

When the plan looks right, run it for real by dropping `--dry-run`:

```bash
content ingress --tree /tmp/test-instance/collections/test-collection/en/articles
```

```text
6 documents processed
0 documents skipped (already identified)
```

Ingress writes the records into a hidden sidecar beside each file. 

```bash
ls -al /tmp/test-instance/collections/test-collection/en/articles
```

For my articles I have

```bash
total 16
drwxrwxr-x 4 initial initial 4096 Aug  2 00:54 .
drwxrwxr-x 5 initial initial 4096 Aug  2 00:48 ..
drwxrwxr-x 3 initial initial 4096 Aug  2 00:54 .articles.assets
drwxrwxr-x 5 initial initial 4096 Aug  2 00:54 audio
```

```bash
ls -al /tmp/test-instance/collections/test-collection/en/articles/audio
```

 `first-post.md` you now have:

```text
articles/
  first-post.md
  .first-post.md.assets/
    content/
      identity.yml
      dc.yml
      provenance.yml
      fixity.yml
      ingress/ingress-2026-08-02T04-41-05Z.yml
```

Open the descriptive sidecar to confirm the cascade did its job. The creator, publisher, and rights you set once at the instance flow into every ingested document:

```bash
cat /tmp/test-instance/collections/test-collection/en/articles/.first-post.md.assets/content/dc.yml
```

```text
dc:creator: Jane Operator
dc:publisher: Example Org
dc:rights: 'Copyright 2026 Example Org. SPDX-License-Identifier: CC-BY-4.0'
dc:language: eng
dc:language_bcp47: en
dc:type: Collection
```

Ingress is idempotent by identity. Running the same batch again catalogs nothing new, because each document already carries an identity:

```text
0 documents processed
2 documents skipped (already identified)
```

A document's `dc:date` is resolved on a fallback chain: a date transcribed from the document's own frontmatter is preferred, then an operator-supplied `--date VALUE`, then the file's creation time where the platform exposes it, and finally the ingress moment recorded as a noted value. Pass `--date 2026-07-01` to the batch when you want one explicit date applied to documents that declare none.

## Recap and cleanup

You instantiated an instance, resolved its three calculated defaults so the cascade could carry them downward, and catalogued a directory of content in place, each file gaining identity, descriptive, provenance, and fixity records plus an ingress event. The same `content ingress --tree PATH` pattern scales to any directory inside an archive, and the wider batch scopes `--archive LANG` and `--collection` apply the same operation to an entire archive or every archive in the collection.

Because everything lives under one directory, cleanup is a single command:

```bash
rm -rf /tmp/test-instance
```
