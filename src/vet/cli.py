from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from vet import __version__
from vet.config import AuditConfig
from vet.engine import audit_file
from vet.profiles import available_profiles
from vet.report import render_json, render_text


def _detect_profile(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    if path.name == "SKILL.md" or path.suffix == ".skill.md":
        return "skillmd"
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


def _collect_paths(paths: list[Path], glob_pattern: str) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        if p.is_dir():
            files.extend(sorted(p.rglob(glob_pattern)))
        elif p.is_file():
            files.append(p)
    return files


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root or Path(os.environ.get("VET_ROOT", Path.cwd()))
    config_base = AuditConfig.from_paths(
        root=root,
        extra_link_dirs=args.link_dirs,
        nv_age_days=args.nv_age_days,
        strict=args.strict,
        pass_threshold=args.pass_threshold,
    )

    files = _collect_paths([Path(p) for p in args.paths], args.glob)
    if not files:
        print("ERROR: no files matched", file=sys.stderr)
        return 3

    worst = 0
    exit_map = {"PASS": 0, "WARN": 1, "REJECT": 2, "ERROR": 3}

    for path in files:
        profile = _detect_profile(path, args.profile)
        config = AuditConfig(
            root=config_base.root,
            link_dirs=config_base.link_dirs,
            profile=profile,
            nv_age_days=config_base.nv_age_days,
            strict=config_base.strict,
            pass_threshold=config_base.pass_threshold,
        )
        try:
            report = audit_file(path, config)
        except OSError as exc:
            print(f"ERROR: could not read {path}: {exc}", file=sys.stderr)
            worst = max(worst, 3)
            continue

        if args.json:
            print(render_json(report))
        else:
            if len(files) > 1:
                print()
            print(render_text(report))

        worst = max(worst, exit_map[report.verdict])

    return worst


if __name__ == "__main__":
    raise SystemExit(main())
