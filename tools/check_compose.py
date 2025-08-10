#!/usr/bin/env python3
"""
Compose harmony check:
- Every service in docker-compose.yml must have either a build context with Dockerfile
  or an image specified.
- Each service name must be mentioned at least once in README (Services section or anywhere).

Exits non-zero on violations; prints a concise summary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
README_FILE = REPO_ROOT / "README.md"


def load_yaml(path: Path) -> Dict:
    if yaml is None:
        return {"_error": "pyyaml not installed"}
    if not path.exists():
        return {"_error": f"missing file: {path}"}
    content = path.read_text(encoding="utf-8", errors="ignore")
    return yaml.safe_load(content) or {}


def main() -> int:
    compose = load_yaml(COMPOSE_FILE)
    errors: List[str] = []
    if "_error" in compose:
        print(f"compose check error: {compose['_error']}")
        return 1

    services = compose.get("services", {}) or {}
    if not services:
        print("compose check: no services defined")
        return 1

    readme_text = README_FILE.read_text(encoding="utf-8", errors="ignore") if README_FILE.exists() else ""

    for name, spec in services.items():
        has_image = bool(spec.get("image"))
        has_build = bool(spec.get("build"))
        if not (has_image or has_build):
            errors.append(f"service '{name}' must have image or build")
        if has_build:
            # validate Dockerfile presence
            build = spec.get("build")
            if isinstance(build, dict):
                context = build.get("context", ".")
                dockerfile = build.get("dockerfile", "Dockerfile")
            else:
                context = build
                dockerfile = "Dockerfile"
            context_path = (REPO_ROOT / str(context)).resolve()
            docker_path = context_path / dockerfile
            if not docker_path.exists():
                errors.append(f"service '{name}' build Dockerfile not found at {docker_path.relative_to(REPO_ROOT)}")
        # README mention
        if name.lower() not in readme_text.lower():
            errors.append(f"service '{name}' is not mentioned in README.md")

    if errors:
        print("Compose harmony violations:")
        for e in errors:
            print(f"- {e}")
        return 1

    print("Compose harmony check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
