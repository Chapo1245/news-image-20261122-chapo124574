#!/usr/bin/env python3
"""news-image-20261122 entrypoint.

Writes the pre-rendered one-page summary of Sunday 22 November 2026's
world news to the output directory as entry.png.

The image is a fixed, deterministic artifact: the program only copies the
bytes of entry.png shipped beside this script, so two runs always produce
byte-identical output. No network access, no randomness, no clock reads.
Standard library only.
"""

import os
import shutil
import sys
from pathlib import Path

IMAGE_NAME = "entry.png"


def output_dir() -> Path:
    target = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    return Path(target)


def main() -> int:
    here = Path(__file__).resolve().parent
    source = here / IMAGE_NAME
    if not source.is_file():
        print(f"missing {IMAGE_NAME} next to main.py", file=sys.stderr)
        return 1
    dest_dir = output_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / IMAGE_NAME
    if source.resolve() != dest.resolve():
        shutil.copyfile(source, dest)
    # Confirm the copy landed whole before reporting success.
    if dest.stat().st_size != source.stat().st_size:
        print(f"size mismatch after copy: {dest}", file=sys.stderr)
        return 1
    print(f"wrote {dest} ({dest.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
