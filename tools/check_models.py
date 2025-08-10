#!/usr/bin/env python3
"""
Architecture lint: enforce only allowed model names in source code.

Allowed models:
  - o3-mini
  - gpt-4.1
  - gpt-4.1-mini

Scan source directories and fail if other model-like tokens are found.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Set, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories to scan (to avoid docs/dashboards noise)
SCAN_DIRS = [
    REPO_ROOT / "backend",
    REPO_ROOT / "agents",
    REPO_ROOT / "scripts",
    REPO_ROOT / "proto",
    REPO_ROOT / "frontend" / "src",
]

TEXT_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yml", ".yaml", ".toml"}

ALLOWED: Set[str] = {"o3-mini", "gpt-4.1", "gpt-4.1-mini"}

# Match common OpenAI model-like tokens (gpt-*, o*)
MODEL_RE = re.compile(r"\b(?:gpt-[\w\.-]+|o\d(?:[\.-]\d+)?(?:-[\w\.-]+)?)\b", re.IGNORECASE)

IGNORE_DIR_NAMES = {"node_modules", ".venv", "dist", "build", ".vite", "__pycache__", ".ruff_cache", ".pytest_cache"}


def iter_files() -> Iterable[Path]:
    for base in SCAN_DIRS:
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_dir():
                if p.name in IGNORE_DIR_NAMES:
                    # Skip subtrees
                    continue
                else:
                    continue
            if p.suffix in TEXT_EXTS:
                yield p


def main() -> int:
    violations: List[Tuple[str, int, str]] = []
    for p in iter_files():
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in MODEL_RE.finditer(text):
            token = m.group(0)
            # Normalize case for comparison
            token_norm = token.lower()
            if token_norm not in ALLOWED:
                # Record line and short context
                line_no = text.count("\n", 0, m.start()) + 1
                violations.append((str(p.relative_to(REPO_ROOT)), line_no, token))

    if violations:
        print("Disallowed model names found (only allowed: o3-mini, gpt-4.1, gpt-4.1-mini):")
        for file, line, token in violations:
            print(f"  {file}:{line}: {token}")
        return 1

    print("Model check passed: only allowed models are referenced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
