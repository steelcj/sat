# sat-testing-command-examples

```bash
set +e
ART=~/.local/share/sat-tool/0.8.0
PY="$ART/.venv/bin/python"
CONTENT="$ART/en/bin/content/content.py"
REPO=/home/initial/2-areas/development/sat

echo "=== preseed present? ==="
if [ -f ~/.config/sat/instantiate-preseed.yml ]; then echo "yes: $(grep -c . ~/.config/sat/instantiate-preseed.yml) lines"; else
  echo "no -> installing demo preseed"; cp "$REPO/en/docs/demos/sat-capabilities-showcase/resources/demo-preseed.yml" ~/.config/sat/instantiate-preseed.yml
fi

echo "=== fresh scratch ==="
cd /tmp && rm -rf sat-demo && mkdir sat-demo && cd sat-demo
cp "$REPO/en/docs/demos/sat-capabilities-showcase/resources/messy-source-sample.md" .

echo "=== sat init ==="
sat init --language en demo-instance 2>&1 | tail -8

echo "=== ingress ==="
cd demo-instance
"$PY" "$CONTENT" ingress ../messy-source-sample.md --to en 2>&1 | tail -5

echo "=== BASELINE document dc.yml ==="
cat en/.messy-source-sample.md.assets/content/dc.yml
```

demo inheritance

```bash
set +e
ART=~/.local/share/sat-tool/0.8.0; PY="$ART/.venv/bin/python"; CONTENT="$ART/en/bin/content/content.py"
cd /tmp/sat-demo/demo-instance
INST=.demo-instance.assets/sat/dc.yml

echo "########## DEMO A: parent-layer inheritance (edit instance, ingress a NEW doc) ##########"
"$PY" - <<'PYEOF'
import yaml
p=".demo-instance.assets/sat/dc.yml"; d=yaml.safe_load(open(p))
d["dc:rights"]="https://creativecommons.org/licenses/by/4.0/"
yaml.safe_dump(d,open(p,"w"),default_flow_style=False,sort_keys=False)
print("instance dc:rights changed to CC BY 4.0")
PYEOF
printf 'A second note\n\nNo metadata of its own.\n' > ../second-note.md
"$PY" "$CONTENT" ingress ../second-note.md --to en 2>&1 | tail -2
echo "--- second doc dc.yml (inherits the NEW instance rights) ---"
grep 'dc:rights' en/.second-note.md.assets/content/dc.yml

echo; echo "########## DEMO B: document override via frontmatter (Tier 5 beats Tier 1) ##########"
printf -- '---\ndc:title: "Locally Licensed Note"\ndc:rights: "https://creativecommons.org/publicdomain/zero/1.0/"\n---\n\nThis one carries its own rights.\n' > ../own-rights.md
"$PY" "$CONTENT" ingress ../own-rights.md --to en 2>&1 | tail -2
echo "--- own-rights doc dc.yml (its own CC0 wins over the instance CC BY) ---"
grep -E 'dc:rights|dc:title' en/.own-rights.md.assets/content/dc.yml
echo "--- origins in its ingress record (transcribed vs supplied) ---"
grep -A12 '^origins:' en/.own-rights.md.assets/content/ingress/*.yml | grep -E 'dc:rights|dc:title|dc:creator' | head

echo; echo "########## DEMO C: the <calculated> tripwire refuses to guess ##########"
"$PY" - <<'PYEOF'
import yaml
p=".demo-instance.assets/sat/dc.yml"; d=yaml.safe_load(open(p))
d["dc:rights"]="<calculated>"
yaml.safe_dump(d,open(p,"w"),default_flow_style=False,sort_keys=False)
print("instance dc:rights set to <calculated> (a hole at the top layer)")
PYEOF
printf 'A third note with no rights anywhere.\n' > ../third-note.md
echo "--- ingress a plain doc (expect refusal, no records written) ---"
"$PY" "$CONTENT" ingress ../third-note.md --to en 2>&1 | tail -3
echo "--- did it write anything? ---"
ls en/.third-note.md.assets 2>&1 | head -1
```

```bash
set +e
ART=~/.local/share/sat-tool/0.8.0; PY="$ART/.venv/bin/python"; CONTENT="$ART/en/bin/content/content.py"
REPO=/home/initial/2-areas/development/sat
cd /tmp && rm -rf sat-demo3 && mkdir sat-demo3 && cd sat-demo3
cp "$REPO/en/docs/demos/sat-capabilities-showcase/resources/messy-source-sample.md" .
printf 'A top-level note.\n' > toplevel-note.md
sat init --language en demo-instance 2>&1 | tail -2
cd demo-instance

echo "=== set a DISTINCT licence on the collection tier (Tier 2) ==="
COLL=collections/test-collection/.test-collection.assets/collection/dc.yml
"$PY" - <<PYEOF
import yaml
p="$COLL"; d=yaml.safe_load(open(p)) or {}
d["dc:rights"]="https://creativecommons.org/licenses/by-nc/4.0/"
yaml.safe_dump(d,open(p,"w"),default_flow_style=False,sort_keys=False)
print("collection dc:rights = CC BY-NC 4.0 (instance default is CC BY-SA 4.0)")
PYEOF

echo "=== ingress INTO the collection's nested archive path ==="
"$PY" "$CONTENT" ingress ../messy-source-sample.md --to collections/test-collection/en/docs/my-directory 2>&1 | tail -1
echo "resolved rights (expect COLLECTION = by-nc):"
grep dc:rights collections/test-collection/en/docs/my-directory/.messy-source-sample.md.assets/content/dc.yml

echo "=== ingress a doc into the TOP-LEVEL archive for contrast ==="
"$PY" "$CONTENT" ingress ../toplevel-note.md --to en 2>&1 | tail -1
echo "resolved rights (expect INSTANCE = by-sa):"
grep dc:rights en/.toplevel-note.md.assets/content/dc.yml
```

