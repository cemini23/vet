from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from vet import __version__
from vet.config import AuditConfig
from vet.engine import audit_file
from vet.profiles import available_profiles
from vet.report import render_json, render_json_many, render_text


def _detect_profile(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    if path.name == "SKILL.md" or path.suffix == ".skill.md":
        return "skillmd"
    if "prompt" in path.name.lower() or "prompts" in path.parts:
        return "prompt"
    return "brief"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vet",
        description="Static veto-gate auditor for agent skills, briefs, and prompts.",
    )
    p.add_argument("paths", nargs="+", help="File or directory to audit")
    p.add_argument(
        "--profile",
        choices=available_profiles(),
        help="Audit profile (default: brief, or skillmd for SKILL.md files)",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON report")
    p.add_argument("--strict", action="store_true", help="Treat warnings as veto gates")
    p.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Repository root for cross-link resolution (default: cwd or VET_ROOT)",
    )
    p.add_argument(
        "--link-dir",
        action="append",
        type=Path,
        default=[],
        dest="link_dirs",
        help="Extra directory for @path cross-link resolution (repeatable)",
    )
    p.add_argument(
        "--nv-age-days",
        type=int,
        default=30,
        help="Flag [NEEDS VERIFICATION] tags older than N days (default: 30)",
    )
    p.add_argument(
        "--pass-threshold",
        type=float,
        default=80.0,
        help="Minimum score for PASS when no warnings (default: 80)",
    )
    p.add_argument(
        "--glob",
        default="*.md",
        help="When path is a directory, audit files matching this glob (default: *.md)",
    )
    p.add_argument("--version", action="version", version=f"vet {__version__}")
    return p


_SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".eggs",
    "build",
    "dist",
}


def _collect_paths(paths: list[Path], glob_pattern: str) -> tuple[list[Path], list[Path]]:
    """Split the arguments into (files to audit, paths that do not exist).

    Directory walks skip build trees and virtualenvs, so `vet .` does not audit
    vendored markdown. Missing paths are returned rather than dropped: a silent
    drop let a CI run pass while auditing nothing.
    """
    files: list[Path] = []
    missing: list[Path] = []
    for p in paths:
        if p.is_dir():
            for found in sorted(p.rglob(glob_pattern)):
                if _SKIP_DIRS.isdisjoint(found.parts[:-1]):
                    files.append(found)
        elif p.is_file():
            files.append(p)
        else:
            missing.append(p)
    return files, missing


def _discover_root(paths: list[Path]) -> Path:
    """Nearest ancestor holding .git or CLAUDE.md, else the working directory.

    Without this, link resolution followed the shell's cwd, so the same file
    resolved differently depending on where it was invoked from.
    """
    env = os.environ.get("VET_ROOT")
    if env:
        return Path(env)
    for p in paths:
        node = p.resolve() if p.is_dir() else p.resolve().parent
        while True:
            if (node / ".git").exists() or (node / "CLAUDE.md").is_file():
                return node
            if node.parent == node:
                break
            node = node.parent
    return Path.cwd()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    given = [Path(p) for p in args.paths]
    root = args.root or _discover_root(given)
    config_base = AuditConfig.from_paths(
        root=root,
        extra_link_dirs=args.link_dirs,
        nv_age_days=args.nv_age_days,
        strict=args.strict,
        pass_threshold=args.pass_threshold,
    )

    files, missing = _collect_paths(given, args.glob)

    worst = 0
    for p in missing:
        print(f"ERROR: path does not exist: {p}", file=sys.stderr)
        worst = 3
    if not files:
        if not missing:
            print("ERROR: no files matched", file=sys.stderr)
        return 3

    # pre-commit and GitHub Actions treat any non-zero exit as a failure, so a
    # non-strict WARN must not block. --strict already turns warnings into REJECT.
    exit_map = {"PASS": 0, "WARN": 2 if args.strict else 0, "REJECT": 2, "ERROR": 3}
    reports = []

    for path in files:
        profile = _detect_profile(path, args.profile)
        # Copy every field from the base config. Enumerating fields by hand silently
        # dropped newly added ones (wiki_aliases), so derive the copy instead.
        config = replace(config_base, profile=profile)
        try:
            report = audit_file(path, config)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)
            worst = max(worst, 3)
            continue

        reports.append(report)
        worst = max(worst, exit_map[report.verdict])
        if not args.json:
            if len(files) > 1:
                print()
            print(render_text(report))

    if args.json:
        # Always one document. The old per-file loop concatenated objects, so any
        # multi-file run emitted unparseable JSON.
        print(render_json(reports[0]) if len(reports) == 1 else render_json_many(reports))

    return worst


if __name__ == "__main__":
    raise SystemExit(main())
