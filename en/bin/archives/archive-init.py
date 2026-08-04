#!/usr/bin/env python3
#
# bin/archives/archive-init.py

import sys
import yaml
import os
from pathlib import Path


def usage():
    print(
        "usage: archive-init.py "
        "--archive-definition-path <archive-definition.yml> "
        "[--dry-run]"
    )


def error(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def create_tree(base: Path, tree: dict, dry_run=False):
    """
    Recursively create filesystem structure from YAML tree.
    """

    if not isinstance(tree, dict):
        error("tree must be a mapping")

    for name, value in tree.items():

        path = base / name

        # file
        if value == "file" or value is None:

            if dry_run:
                print(f"[dry-run] create file: {path}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch(exist_ok=True)

        # directory
        elif isinstance(value, dict):

            if dry_run:
                print(f"[dry-run] create directory: {path}")
            else:
                path.mkdir(parents=True, exist_ok=True)

            if value:
                create_tree(path, value, dry_run=dry_run)

        else:
            error(f"invalid node definition for '{name}'")


def main():

    args = sys.argv[1:]

    archive_def_path = None
    dry_run = False

    i = 0
    while i < len(args):

        if args[i] == "--archive-definition-path":
            i += 1

            if i >= len(args):
                usage()
                sys.exit(1)

            archive_def_path = Path(args[i]).resolve()

        elif args[i] == "--dry-run":
            dry_run = True

        elif args[i] in ("--help", "-h"):
            usage()
            sys.exit(0)

        else:
            usage()
            sys.exit(1)

        i += 1

    if not archive_def_path:
        usage()
        sys.exit(1)

    if not archive_def_path.exists():
        error(f"archive definition file not found: {archive_def_path}")

    # load YAML
    try:
        with archive_def_path.open("r", encoding="utf-8") as f:
            archive_def = yaml.safe_load(f) or {}
    except Exception as e:
        error(f"failed to read archive definition: {e}")

    archive_name = archive_def.get("archive_name")
    parent_directory = archive_def.get("parent_directory")
    archive_root = archive_def.get("archive_root")
    language = archive_def.get("language")
    tree = archive_def.get("tree")

    if not archive_name:
        error("archive_name is required")

    if not parent_directory:
        error("parent_directory is required")

    if not archive_root:
        error("archive_root is required")

    if not isinstance(language, dict):
        error("language section missing or invalid")

    if not isinstance(tree, dict):
        error("tree section missing or invalid")

    parent_path = Path(os.path.expandvars(parent_directory)).expanduser().resolve()

    archive_root_path = parent_path / archive_root

    language_file = archive_root_path / ".language.yml"

    print(f"Archive name: {archive_name}")
    print(f"Archive root: {archive_root_path}")

    if dry_run:
        print("[dry-run] create directory:", archive_root_path)
    else:
        try:
            archive_root_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            error(f"failed to create archive root: {e}")

    # write language metadata

    if dry_run:
        print(f"[dry-run] write language metadata: {language_file}")
        print(f"[dry-run] content: {language}")
    else:
        try:
            with language_file.open("w", encoding="utf-8") as f:
                yaml.safe_dump(language, f, sort_keys=False)
        except Exception as e:
            error(f"failed to write language metadata: {e}")

    create_tree(archive_root_path, tree, dry_run=dry_run)

    if dry_run:
        print("[dry-run] no filesystem changes were made")
    else:
        print(f"Archive '{archive_name}' initialized at {archive_root_path}")


if __name__ == "__main__":
    main()
