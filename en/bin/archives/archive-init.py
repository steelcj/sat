#!/usr/bin/env python3
#
# bin/archives/archive-init.py
import sys
import yaml
from pathlib import Path

def usage():
    print(
        "usage: archive init "
        "--archive-definition-path <archive-definition.yml> "
        "[--archives-parent-definition-path <archives-parent.yml>]"
    )

def create_tree(base: Path, tree):
    if isinstance(tree, dict):
        for name, subtree in tree.items():
            p = base / name
            p.mkdir(parents=True, exist_ok=True)
            create_tree(p, subtree)
    elif isinstance(tree, list):
        for name in tree:
            (base / name).mkdir(parents=True, exist_ok=True)

def main():
    args = sys.argv[1:]

    archive_def_path = None
    archives_parent_def_path = None

    i = 0
    while i < len(args):
        if args[i] == "--archive-definition-path":
            i += 1
            if i >= len(args):
                usage()
                sys.exit(1)
            archive_def_path = Path(args[i]).resolve()
        elif args[i] == "--archives-parent-definition-path":
            i += 1
            if i >= len(args):
                usage()
                sys.exit(1)
            archives_parent_def_path = Path(args[i]).resolve()
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

    # load archive-definition.yml
    with archive_def_path.open() as f:
        archive_def = yaml.safe_load(f)

    archive_name = archive_def.get("archive")
    if not isinstance(archive_name, str):
        print("error: 'archive' must be a string in archive-definition.yml")
        sys.exit(1)

    # tool root: <project-root>/bin/archives
    tool_root = Path(__file__).resolve().parent

    # project root: <project-root>
    project_root = tool_root.parent.parent

    # default archives-parent.yml
    if not archives_parent_def_path:
        archives_parent_def_path = tool_root / "config" / "archives-parent.yml"

    if not archives_parent_def_path.exists():
        print(f"error: missing archives parent definition: {archives_parent_def_path}")
        sys.exit(1)

    # load archives-parent.yml
    with archives_parent_def_path.open() as f:
        parent_def = yaml.safe_load(f)

    archives_root_name = parent_def.get("archives", {}).get("root")
    if not isinstance(archives_root_name, str):
        print("error: invalid archives.root in archives-parent.yml")
        sys.exit(1)

    archives_root = project_root / archives_root_name

    docs_root = archives_root / archive_name / "en" / "docs"
    docs_root.mkdir(parents=True, exist_ok=True)

    create_tree(docs_root, archive_def.get("tree", {}))

    print(f"Archive '{archive_name}' initialized at {docs_root.parent}")

if __name__ == "__main__":
    main()
