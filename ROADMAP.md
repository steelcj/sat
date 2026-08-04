# ROADMAP

Version: 0.1.0
Status: Draft

## Near term

- Wire the remaining collection subcommands into the `collection` dispatcher. As of 0.8.0, `en/bin/collection/collection` routes only `init` and `work`; `reconcile`, `fixity`, and `mv` ship as working scripts under `en/bin/collection/` but are unreachable through the `collection` command, which falls through to `collection-init.py --help`. Add dispatch cases so `collection reconcile`, `collection fixity`, and `collection mv` reach their scripts, matching the way `init` and `work` are routed. Until then these operations are script-only (for example `python en/bin/collection/collection-fixity.py --check`), and the SAT Capabilities Showcase demo's integrity beat depends on `collection fixity --check` resolving.
