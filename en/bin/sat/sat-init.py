#!/usr/bin/env python3

from pathlib import Path

def main():
    sat_root = Path(__file__).resolve().parents[3]

    archive_root = sat_root / "archive" / "en"
    docs_dir = archive_root / "docs"

    docs_dir.mkdir(parents=True, exist_ok=True)

    print(f"SAT initialized at: {sat_root}")

if __name__ == "__main__":
    main()
