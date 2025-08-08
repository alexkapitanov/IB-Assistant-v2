#!/usr/bin/env python3
"""
Architecture lint: fail if forbidden historical paths exist.
Examples:
  - backend/old_*
  - frontend/legacy_*
  - prompts/deprecated/*
"""
from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

PATTERNS = [
    "backend/old_*",
    "frontend/legacy_*",
    "prompts/deprecated/*",
]


def main() -> int:
    hits: List[Tuple[str, str]] = []
    for pattern in PATTERNS:
        # Support both files and directories; globbing from repo root
        for p in REPO_ROOT.rglob("*"):
            rel = str(p.relative_to(REPO_ROOT))
            if fnmatch.fnmatch(rel, pattern):
                hits.append((pattern, rel))
    if hits:
        print("Forbidden files/directories found:")
        for pattern, path in hits:
            print(f"- {path} (matched {pattern})")
        return 1
    print("Forbidden paths check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
