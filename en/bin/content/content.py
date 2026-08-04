#!/usr/bin/env python3
#
# source
#   project: sat
#   path: en/bin/content/content.py
#
"""content — the content tier dispatcher.

A cross-platform Python entry point (content-ingress implementation plan
Decision 3): it runs on Linux, macOS, and Windows without a per-OS wrapper,
and resolves its own interpreter in process rather than through a fixed
`.venv` path, sidestepping the venv-path discrepancy the bash tier
dispatchers carry.

It routes the first argument to a subcommand and calls that tool's main():

    content init <directory> [...]
    content ingress <document.md> [...]

content is the first Python-dispatched tier; back-porting the pattern to the
other tiers (sat, collection) is a tracked follow-on, not done here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_HERE = Path(__file__).resolve().parent

# Subcommand -> the hyphenated script that implements it. The scripts are not
# importable by name (the hyphen is not a legal module identifier), so they
# are loaded from their file path.
_SUBCOMMANDS = {
    "init": "content-init.py",
    "ingress": "content-ingress.py",
}

_USAGE = "usage: content <init|ingress> [options]"


def _load(filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"content_sub_{filename.replace('-', '_').removesuffix('.py')}",
        _HERE / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if not argv:
        print(_USAGE, file=sys.stderr)
        return 1
    if argv[0] in ("-h", "--help"):
        print(_USAGE)
        print("\nsubcommands:")
        print("  init     mint a content organizing directory's records")
        print("  ingress  bring an arriving document under SAT management")
        return 0

    subcommand, rest = argv[0], argv[1:]
    script = _SUBCOMMANDS.get(subcommand)
    if script is None:
        print(f"[CONTENT ERROR] unknown subcommand: {subcommand!r}. "
              f"{_USAGE}", file=sys.stderr)
        return 2

    module = _load(script)
    # Present the subcommand's own argv to it. content-init.py reads sys.argv;
    # content-ingress.py accepts argv but defaults to sys.argv when None. Set
    # both cleanly so either style works.
    saved_argv = sys.argv
    sys.argv = [f"content {subcommand}"] + rest
    try:
        return int(module.main() or 0)
    finally:
        sys.argv = saved_argv


if __name__ == "__main__":
    sys.exit(main())
