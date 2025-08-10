#!/usr/bin/env python3
"""
Repo sweep (dry-run): gathers candidates without deleting anything.
- Python: unused imports/vars via ruff (F401,F841) and unused code via vulture
- TypeScript: unused exports via ts-prune, extra deps via depcheck
- Forbidden model mentions (configurable regex)
- Dangling files: files not referenced by imports or common configs

Outputs JSON report to tools/sweep-report.json and prints a readable summary.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
REPORT_PATH = REPO_ROOT / "tools" / "sweep-report.json"

# Build forbidden regex without placing forbidden tokens verbatim in the source
_p1 = "gpt-" + "4" + "o"
_p2 = "4" + "o-" + "mini"
FORBIDDEN_MODELS_REGEX = re.compile(r"\b(" + _p1 + r"|" + _p2 + r")\b", re.IGNORECASE)

# Directories and file patterns to ignore when scanning
IGNORE_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    "coverage",
    ".vite",
    "__pycache__",
}

CODE_DIRS = ["backend", "agents", "scripts", os.path.join("frontend", "src")]

PY_EXTS = {".py"}
TS_EXTS = {".ts", ".tsx", ".js", ".jsx"}
TEXT_EXTS = PY_EXTS | TS_EXTS | {".json", ".yml", ".yaml", ".md", ".toml", ".ini", ".cfg", ".txt", ".html", ".css"}


@dataclass
class CmdResult:
    ok: bool
    code: int
    stdout: str
    stderr: str


def run_cmd(cmd: List[str] | str, cwd: Optional[Path] = None, timeout: int = 120) -> CmdResult:
    if isinstance(cmd, str):
        cmd_list = shlex.split(cmd)
    else:
        cmd_list = cmd
    try:
        proc = subprocess.run(
            cmd_list,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            check=False,
        )
        return CmdResult(ok=(proc.returncode == 0), code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)
    except FileNotFoundError as e:
        return CmdResult(ok=False, code=127, stdout="", stderr=str(e))
    except subprocess.TimeoutExpired as e:
        return CmdResult(ok=False, code=124, stdout=e.stdout or "", stderr="timeout")


def run_ruff() -> Dict:
    # Unused imports/variables
    res = run_cmd(["ruff", "check", "--select", "F401,F841", "--output-format", "json", "."], cwd=REPO_ROOT)
    if not res.ok and res.code == 127:
        return {"error": "ruff not found"}
    try:
        data = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        data = []
    return {"ok": res.ok, "code": res.code, "findings": data}


def run_vulture() -> Dict:
    # Try JSON output first
    res = run_cmd(["vulture", ".", "--json"], cwd=REPO_ROOT, timeout=300)
    if not res.ok and res.code == 127:
        return {"error": "vulture not found"}
    findings: List = []
    if res.stdout.strip():
        try:
            findings = json.loads(res.stdout)
        except json.JSONDecodeError:
            # fallback: parse lines "path:line: message"
            lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
            for ln in lines:
                findings.append({"raw": ln})
    return {"ok": res.ok, "code": res.code, "findings": findings}


def run_ts_prune() -> Dict:
    if not FRONTEND_DIR.exists():
        return {"skipped": "no frontend dir"}
    # Prefer local install via npx; try with explicit tsconfig and JSON output
    attempts = [
        ["-y", "ts-prune", "-p", "tsconfig.json", "-j"],
        ["-y", "ts-prune", "--json"],
        ["-y", "ts-prune", "-j"],
    ]
    last: Optional[CmdResult] = None
    for args in attempts:
        res = run_cmd(["npx", *args], cwd=FRONTEND_DIR, timeout=300)
        last = res
        if res.ok:
            try:
                return {"ok": True, "code": 0, "findings": json.loads(res.stdout or "[]")}
            except json.JSONDecodeError:
                # some versions may not support JSON; fall back to raw text parsing
                lines = [ln.strip() for ln in (res.stdout or "").splitlines() if ln.strip()]
                return {"ok": True, "code": 0, "findings": lines}
        if res.code == 127 or "command not found" in res.stderr.lower():
            return {"error": "npx/ts-prune not found"}
    return {"ok": False, "code": (last.code if last else 1), "stdout": (last.stdout if last else ""), "stderr": (last.stderr if last else "")}


def run_depcheck() -> Dict:
    if not FRONTEND_DIR.exists():
        return {"skipped": "no frontend dir"}
    res = run_cmd(["npx", "-y", "depcheck", "--json"], cwd=FRONTEND_DIR, timeout=300)
    if not res.ok and (res.code == 127 or "command not found" in res.stderr.lower()):
        return {"error": "npx/depcheck not found"}
    try:
        data = json.loads(res.stdout or "{}")
    except json.JSONDecodeError:
        data = {"raw": res.stdout}
    return {"ok": res.ok, "code": res.code, "findings": data}


def iter_files(base: Path, include_exts: Set[str] | None = None) -> Path:
    for root, dirs, files in os.walk(base):
        # prune ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            p = Path(root) / f
            if include_exts and p.suffix not in include_exts:
                continue
            yield p


def scan_forbidden_models() -> List[Dict[str, str]]:
    hits = []
    include_dirs = [REPO_ROOT]
    for d in include_dirs:
        for p in iter_files(d, include_exts=TEXT_EXTS):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in FORBIDDEN_MODELS_REGEX.finditer(text):
                # capture line number
                line_no = text.count("\n", 0, m.start()) + 1
                snippet = text[max(0, m.start() - 40) : m.end() + 40].replace("\n", " ")
                hits.append({"file": str(p.relative_to(REPO_ROOT)), "line": line_no, "match": m.group(0), "context": snippet})
    return hits


# --- Dangling files approximation ---

def build_python_module_map(files: List[Path]) -> Dict[str, Path]:
    mod_map: Dict[str, Path] = {}
    for p in files:
        rel = p.relative_to(REPO_ROOT)
        parts = list(rel.parts)
        if parts and parts[0] not in {"backend", "agents", "scripts", "tests"}:
            continue
        if p.name == "__init__.py":
            # package module name, e.g., backend.utils.__init__ -> backend.utils
            mod_name = ".".join(parts[:-1])
        else:
            mod_name = ".".join(parts)[:-3]  # strip .py
        mod_name = mod_name.replace("/", ".").replace("\\", ".")
        mod_map[mod_name] = p
    return mod_map


def parse_python_imports(py_files: List[Path]) -> Set[str]:
    imported: Set[str] = set()
    imp_re = re.compile(r"^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.MULTILINE)
    for p in py_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in imp_re.finditer(txt):
            mod = m.group(1) or m.group(2)
            if mod:
                imported.add(mod)
    return imported


def parse_ts_imports(ts_files: List[Path]) -> Set[str]:
    specs: Set[str] = set()
    # import ... from '...'; require('...')
    imp_re = re.compile(r"(?:import\s+[^;]*?from\s+['\"]([^'\"]+)['\"]|require\(\s*['\"]([^'\"]+)['\"]\s*\))")
    for p in ts_files:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in imp_re.finditer(txt):
            spec = m.group(1) or m.group(2)
            if spec:
                specs.add(spec)
    return specs


def resolve_ts_spec_to_files(base_file: Path, spec: str) -> List[Path]:
    if not spec.startswith("."):
        return []
    base_dir = base_file.parent
    candidates: List[Path] = []
    base = (base_dir / spec).resolve()
    # try as file with various extensions
    for ext in [".ts", ".tsx", ".js", ".jsx", ".json"]:
        p = Path(str(base) + ext)
        if p.exists():
            candidates.append(p)
    # try as directory index
    for ext in [".ts", ".tsx", ".js", ".jsx", ".json"]:
        p = base / ("index" + ext)
        if p.exists():
            candidates.append(p)
    return candidates


def find_dangling_files() -> Dict[str, List[str]]:
    # Collect candidate files
    py_files = [p for d in CODE_DIRS for p in iter_files(REPO_ROOT / d, include_exts=PY_EXTS) if (REPO_ROOT / d).exists()]
    ts_files = [p for d in CODE_DIRS for p in iter_files(REPO_ROOT / d, include_exts=TS_EXTS) if (REPO_ROOT / d).exists()]

    # Build python reference map
    mod_map = build_python_module_map(py_files)
    imported_mods = parse_python_imports(py_files)

    referenced_py_paths: Set[Path] = set()
    for mod in imported_mods:
        # exact match or prefix for submodules
        if mod in mod_map:
            referenced_py_paths.add(mod_map[mod])
        else:
            # try progressively trimming
            parts = mod.split(".")
            while parts:
                candidate = ".".join(parts)
                if candidate in mod_map:
                    referenced_py_paths.add(mod_map[candidate])
                    break
                parts.pop()

    # Entrypoints considered referenced
    for name in ["main.py", "__init__.py"]:
        for p in py_files:
            if p.name == name:
                referenced_py_paths.add(p)

    # TS referenced via relative imports
    ts_import_specs_by_file: Dict[Path, Set[str]] = {}
    for p in ts_files:
        ts_import_specs_by_file[p] = parse_ts_imports([p])
    referenced_ts_paths: Set[Path] = set()
    for p, specs in ts_import_specs_by_file.items():
        for spec in specs:
            for target in resolve_ts_spec_to_files(p, spec):
                referenced_ts_paths.add(target)

    # Build text corpus for coarse references (configs & docs)
    corpus_files: List[Path] = []
    for rel in [
        "docker-compose.yml",
        "README.md",
        "README.rst",
        ".github",
        "grafana",
        "prometheus",
        "helm",
    ]:
        path = REPO_ROOT / rel
        if path.exists():
            if path.is_dir():
                corpus_files.extend([p for p in iter_files(path, include_exts=TEXT_EXTS)])
            else:
                corpus_files.append(path)

    corpus_text = "\n".join(
        (
            (p.read_text(encoding="utf-8", errors="ignore") if p.exists() else "")
            for p in corpus_files
        )
    )

    def is_coarsely_referenced(p: Path) -> bool:
        return p.name in corpus_text

    dangling_py = [str(p.relative_to(REPO_ROOT)) for p in py_files if p not in referenced_py_paths and p.name != "__init__.py"]
    dangling_ts = [str(p.relative_to(REPO_ROOT)) for p in ts_files if p not in referenced_ts_paths]

    # Filter out those that appear in corpus
    dangling_py = [f for f in dangling_py if not is_coarsely_referenced(REPO_ROOT / f)]
    dangling_ts = [f for f in dangling_ts if not is_coarsely_referenced(REPO_ROOT / f)]

    return {"python": dangling_py, "typescript": dangling_ts}


def main() -> int:
    started = time.time()
    report: Dict[str, object] = {"metadata": {"started": started, "root": str(REPO_ROOT)}}

    # Run external tools
    report["ruff"] = run_ruff()
    report["vulture"] = run_vulture()
    report["ts_prune"] = run_ts_prune()
    report["depcheck"] = run_depcheck()

    # Grep forbidden models
    report["forbidden_models"] = scan_forbidden_models()

    # Dangling files
    report["dangling_files"] = find_dangling_files()

    report["metadata"]["finished"] = time.time()

    # Ensure output directory exists
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    # Human-readable summary
    def summarize_count(title: str, value) -> str:
        if isinstance(value, dict) and "findings" in value:
            findings = value["findings"]
            if isinstance(findings, dict):
                # depcheck structure
                unused_deps = len(findings.get("dependencies", []))
                unused_dev = len(findings.get("devDependencies", []))
                return f"{title}: deps={unused_deps}, devDeps={unused_dev} (ok={value.get('ok', False)})"
            return f"{title}: {len(findings)} findings (ok={value.get('ok', False)})"
        if isinstance(value, list):
            return f"{title}: {len(value)} hits"
        if isinstance(value, dict) and "python" in value and "typescript" in value:
            return f"{title}: py={len(value['python'])}, ts={len(value['typescript'])}"
        if isinstance(value, dict) and "error" in value:
            return f"{title}: error: {value['error']}"
        if isinstance(value, dict) and "skipped" in value:
            return f"{title}: skipped: {value['skipped']}"
        return f"{title}: n/a"

    lines = [
        "Repo sweep (dry-run) summary:",
        summarize_count("ruff (F401,F841)", report.get("ruff")),
        summarize_count("vulture", report.get("vulture")),
        summarize_count("ts-prune", report.get("ts_prune")),
        summarize_count("depcheck", report.get("depcheck")),
        summarize_count("forbidden models", report.get("forbidden_models")),
        summarize_count("dangling files", report.get("dangling_files")),
        f"JSON report: {REPORT_PATH.relative_to(REPO_ROOT)}",
    ]
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
