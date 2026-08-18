from __future__ import annotations

import argparse
from pathlib import Path

from caselight.app import run


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-platform Gigabyte case-light controller")
    parser.add_argument("--minimized", action="store_true", help="start minimized after restoring the saved lights")
    parser.add_argument("--state-dir", type=Path, help="use this shared state folder")
    args = parser.parse_args()
    run(minimized=args.minimized, state_directory=args.state_dir)


if __name__ == "__main__":
    main()
