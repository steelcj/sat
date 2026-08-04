# transmog-readme.md

Prepares clean egress documents for a specific publication platform.

Transmog is Stage 3 of the SAT content pipeline — it sits between content
egress (clean body + dc sidecar) and the final publication tool (MkDocs,
a static site generator, a PDF renderer, etc.).

See the full pipeline: [content-pipeline.md](../docs/architecture/content-pipeline.md)

---

## What it does

For each `.md` document in the source directory, transmog:

1. Reads the `.dc.yml` sidecar (canonical metadata)
2. Generates front matter from the dc sidecar per the front matter spec
3. Generates `.og.yml` and `.schema.yml` sidecars if enabled in the spec
4. Writes the prepared document (front matter + body) to the output directory

Pipeline behaviour is driven entirely by the front matter spec — no separate
pipeline configuration is needed. Enabling or disabling a section in the spec
is all that is required to change what transmog produces.

---

## Arguments

| Argument | Required | Description |
| --- | --- | --- |
| `--definition <path>` | Yes | Transmog definition file |
| `--source <dir>` | Conditional | Source directory (overrides definition) |
| `--output <dir>` | Conditional | Output directory (overrides definition) |
| `--overwrite` | No | Overwrite existing output files |
| `--dry-run` | No | Preview without writing |
| `--help` / `-h` | No | Print usage |

`--source` and `--output` are required if not set in the definition file.

---

## Transmog definition file

Each platform target has a definition file that names the platform and
points to its front matter spec. Source and output directories can be
set in the file or passed at runtime.

```yaml
name: sat-docs-mkdocs
description: "Prepare SAT documentation for MkDocs publication"
platform: mkdocs
frontmatter_spec: frontmatter/mkdocs-frontmatter-spec.yml
source: ""
output: ""
```

Definition files live in `definitions/`:

```
en/bin/transmog/definitions/
├── mkdocs-transmog.yml
└── frontmatter/
    ├── default-frontmatter-spec.yml
    ├── mkdocs-frontmatter-spec.yml
    ├── github-frontmatter-spec.yml
    ├── html-frontmatter-spec.yml
    └── pdf-frontmatter-spec.yml
```

---

## Front matter specs

The front matter spec controls everything transmog produces for a given
platform. Each platform has its own self-contained spec file.

| Platform | Front matter | OG sidecar | Schema sidecar |
| --- | --- | --- | --- |
| mkdocs | `title`, `description`, `tags` | no | yes |
| github | none | no | no |
| html | none | yes | yes |
| pdf | none | no | no |

To add a new platform:

1. Copy `definitions/frontmatter/default-frontmatter-spec.yml`
2. Set `platform` and enable the sections you need
3. Create a `<platform>-transmog.yml` definition file pointing to the new spec

---

## DC → front matter mapping

### MkDocs

| dc sidecar field | front matter field |
| --- | --- |
| `dc:title` | `title` |
| `dc:description` | `description` |
| `dc:subject` | `tags` |

### General

| dc sidecar field | front matter field |
| --- | --- |
| `dc:title` | `Title` |
| `dc:description` | `Description` |
| `dc:creator` | `Author` |
| `dc:contributor` | `Contributor` |
| `dc:publisher` | `Publisher` |
| `dc:date` | `Date` |
| `dc:modified` | `Last_Modified_Date` |
| `dc:rights` | `License` |
| `dc:subject` | `Tags` |
| `dc:keywords` | `Keywords` |
| `dc:language` | `Language` |
| `dc:identifier` | `Identifier` |
| `dc:source` | `Source` |
| `dc:relation` | `Relation` |
| `dc:coverage` | `Coverage` |
| `dc:format` | `Format` |
| `dc:type` | `Type` |

---

## DC → OG and Schema.org mapping

See [dc-as-canonical-metadata-source-of-truth.md](../docs/architecture/metadata/dc-as-canonical-metadata-source-of-truth.md)
for the full derivation mapping and dc:type mapping table.

---

## Usage

Dry run against egress output:

```bash
cd ~/projects/sat/prod/sat
python3 en/bin/transmog/transmog.py \
  --definition en/bin/transmog/definitions/mkdocs-transmog.yml \
  --source archives/test/egress \
  --output archives/test/transmog/mkdocs \
  --dry-run
```

Prepare documents for MkDocs:

```bash
python3 en/bin/transmog/transmog.py \
  --definition en/bin/transmog/definitions/mkdocs-transmog.yml \
  --source archives/test/egress \
  --output archives/test/transmog/mkdocs
```

---

## Output structure

```
archives/test/
└── transmog/
    └── mkdocs/
        ├── my-doc.md                 ← prepared document (mkdocs front matter + body)
        └── .my-doc.schema.yml        ← Schema.org sidecar (if enabled in spec)
```

---

## Pipeline position

```
content-metadata-ingress  →  .dc.yml
content-ingress           →  nursery/
content-egress            →  egress/   (body only + .dc.yml)
transmog                  →  transmog/<platform>/   (prepared document + sidecars)
publication tool          →  final output (mkdocs build, pdf renderer, etc.)
```
