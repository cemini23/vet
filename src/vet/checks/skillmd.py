from __future__ import annotations

import re

from vet.checks._regex import SKILL_NAME_RE
from vet.checks.base import check_prose_quality
from vet.models import CheckResult


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    if not text.startswith("---\n"):
        return {}, "missing opening ---"
    fm_end = text.find("\n---\n", 4)
    if fm_end == -1:
        return {}, "missing closing ---"
    block = text[4:fm_end]
    fields: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            fields[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith("  ") and current_key is not None:
            current_lines.append(line.strip())
            continue
        flush()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        current_lines = [value.strip()]
    flush()
    return fields, None


def check_skillmd_frontmatter(text: str) -> CheckResult:
    fields, err = _parse_frontmatter(text)
    if err:
        return CheckResult(
            name="skillmd_frontmatter",
            severity="veto",
            score_weight=0.35,
            score_earned=0.0,
            detail=f"Invalid SKILL.md frontmatter: {err}",
            veto_reason=f"Operational Stability — SKILL.md frontmatter {err}",
        )

    missing = [k for k in ("name", "description") if not fields.get(k)]
    if missing:
        return CheckResult(
            name="skillmd_frontmatter",
            severity="veto",
            score_weight=0.35,
            score_earned=0.0,
            detail=f"Missing required frontmatter field(s): {missing}",
            evidence=missing,
            veto_reason=(
                "Operational Stability — SKILL.md requires name and description fields"
            ),
        )

    name = fields["name"].strip()
    if not SKILL_NAME_RE.match(name):
        return CheckResult(
            name="skillmd_frontmatter",
            severity="warn",
            score_weight=0.35,
            score_earned=0.20,
            detail=(
                f"name '{name}' should be lowercase kebab-case "
                "(letters, digits, hyphens)"
            ),
        )

    desc = fields["description"].strip()
    if len(desc) < 20:
        return CheckResult(
            name="skillmd_description",
            severity="warn",
            score_weight=0.25,
            score_earned=0.10,
            detail=f"description is short ({len(desc)} chars; target ≥20)",
        )
    if len(desc) > 1024:
        return CheckResult(
            name="skillmd_description",
            severity="warn",
            score_weight=0.25,
            score_earned=0.15,
            detail=f"description is long ({len(desc)} chars; consider trimming)",
        )

    return CheckResult(
        name="skillmd_frontmatter",
        severity="pass",
        score_weight=0.35,
        score_earned=0.35,
        detail=f"Frontmatter OK (name={name})",
    )


def check_skillmd_body(text: str) -> CheckResult:
    fm_end = text.find("\n---\n", 4)
    if fm_end == -1:
        return CheckResult(
            name="skillmd_body",
            severity="veto",
            score_weight=0.25,
            score_earned=0.0,
            detail="Cannot locate skill body after frontmatter",
            veto_reason="Operational Stability — SKILL.md has no parseable body",
        )
    body = text[fm_end + 5 :].strip()
    if len(body) < 40:
        return CheckResult(
            name="skillmd_body",
            severity="warn",
            score_weight=0.25,
            score_earned=0.05,
            detail=f"Skill body is very short ({len(body)} chars)",
        )
    if not re.search(r"^#\s+\S", body, re.MULTILINE):
        return CheckResult(
            name="skillmd_body",
            severity="warn",
            score_weight=0.25,
            score_earned=0.15,
            detail="Skill body has no top-level markdown heading (# Title)",
        )
    return CheckResult(
        name="skillmd_body",
        severity="pass",
        score_weight=0.25,
        score_earned=0.25,
        detail=f"Skill body present ({len(body)} chars)",
    )


def check_skillmd_metadata(text: str) -> CheckResult:
    fields, err = _parse_frontmatter(text)
    if err:
        return CheckResult(
            name="skillmd_metadata",
            severity="pass",
            score_weight=0.20,
            score_earned=0.20,
            detail="Skipped — frontmatter invalid",
        )

    issues: list[str] = []
    license_val = fields.get("license", "").strip()
    if license_val and license_val.lower() in {"unknown", "none", "n/a"}:
        issues.append(f"weak license value: {license_val}")

    author = fields.get("metadata.author", fields.get("author", "")).strip()
    version = fields.get("metadata.version", fields.get("version", "")).strip()
    if not author:
        issues.append("metadata.author missing (recommended)")
    if not version:
        issues.append("metadata.version missing (recommended)")

    if not issues:
        return CheckResult(
            name="skillmd_metadata",
            severity="pass",
            score_weight=0.20,
            score_earned=0.20,
            detail="Recommended metadata fields present",
        )
    return CheckResult(
        name="skillmd_metadata",
        severity="warn",
        score_weight=0.20,
        score_earned=0.12,
        detail="; ".join(issues),
        evidence=issues,
    )


def check_skillmd_prose(text: str) -> CheckResult:
    result = check_prose_quality(text)
    result.name = "skillmd_prose"
    result.score_weight = 0.20
    if result.severity == "pass":
        result.score_earned = 0.20
    elif result.score_earned > 0:
        result.score_earned = min(result.score_earned * 4, 0.10)
    return result
