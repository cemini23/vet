from __future__ import annotations

import re

from vet.checks._regex import SKILL_NAME_RE
from vet.checks.base import check_prose_quality
from vet.models import CheckResult


_FM_END_RE = re.compile(r"\n---[ \t]*\r?\n")
_BLOCK_SCALAR = {">", ">-", ">+", "|", "|-", "|+"}


def _clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str | None]:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---"):
        return {}, "missing opening ---"
    end = _FM_END_RE.search(text, 3)
    if end is None:
        return {}, "missing closing ---"
    block = text[3:end.start()]
    fields: dict[str, str] = {}
    parents: dict[int, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
        nonlocal current_key, current_lines
        if current_key is not None:
            fields[current_key] = "\n".join(current_lines).strip()
        current_key = None
        current_lines = []

    for raw in block.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if current_key is not None and indent > 0:
            current_lines.append(stripped)   # block scalar or list body
            continue
        key, sep, value = stripped.partition(":")
        if not sep:
            continue
        flush()
        key = _clean_scalar(key)
        value = value.strip()
        prefix = parents.get(indent - 2, "") if indent >= 2 else ""
        for level in [lvl for lvl in parents if lvl >= indent]:
            del parents[level]
        full = f"{prefix}.{key}" if prefix else key
        if value in _BLOCK_SCALAR:
            current_key = full               # following lines carry the value
        elif value:
            fields[full] = _clean_scalar(value)
        else:
            parents[indent] = full           # nested mapping follows
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
