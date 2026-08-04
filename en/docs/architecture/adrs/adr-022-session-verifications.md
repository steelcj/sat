# ADR-022 session verifications

Almost — one distinction from your own workflow first: Claude Code finishing means the *work commits* exist, but between work and release sits **verification of what landed**. The ADR-021 round taught this: verify the session's report before trusting it. So the sequence:

**1. Verify the handoff's own checklist** (it was required to report five items — confirm you saw them): full suite green with the expected count (baseline + 21), the smoke transcript including the stale-path finding and its repair, the index header shape, dry-run writing nothing, `VERSION` untouched.

**2. Then the release ritual** per commit-and-versioning v0.2.2 — and this is **0.6.0** (MINOR: the work/join/index capability is new):

```bash
# bump VERSION to 0.6.0, update changelog
git add VERSION <changelog>          # never git add .
git commit -m "release 0.6.0"
git show HEAD:VERSION                # must print 0.6.0 — if not, STOP
git tag -a v0.6.0 -m "version 0.6.0"
git show v0.6.0:VERSION              # must print 0.6.0 — if not, delete tag, STOP
git push && git push origin v0.6.0
```

**3. Install:** `python3 install-sat.py --install 0.6.0` from the installer repo — its version-verification gate does its usual job.

**4. Test for real** — the smoke sequence from the handoff, but in your installed instance rather than a temp dir, exercising the actual payload:

```bash
cd <your-sat-instance>/<a-collection>
# two docs, en + fr, identity assigned fresh (via however the session wired assignment)
collection work join fr/<doc> --expression-of en/<doc>     # dry-run: PLAN prints, nothing written
collection work join fr/<doc> --expression-of en/<doc> --apply
cat fr/.<doc>.assets/sat/identity.yml                      # sat:work moved; sat:work_retired has {uuid, retired, by}
collection work index --rebuild
head -8 .<collection>.assets/sat/work-index.yml            # header: path line, remedy, generated_by mapping
mv fr/<doc> fr/<doc-renamed>  # plus its assets dir
collection work index --check                              # stale-path finding, nonzero exit
collection work index --rebuild && collection work index --check   # clean
```

That last triplet — break it, detect it, repair it — is the canonical/derived contract proven in your real instance, which is the whole point of the release.

One caveat to carry: if the handoff session deferred or reshaped anything (the `collection work find` title search was allowed to be cheap; suggestion machinery was explicitly deferrable), the release changelog should say what shipped versus what's still owed, so 0.6.0's claims match its contents.

Report the verification and we resume the paper trail: ADR-023 review, then vocabulary v0.4.0, then phase two — `content ingress` with cataloging — gets built on top of a verified 0.6.0.