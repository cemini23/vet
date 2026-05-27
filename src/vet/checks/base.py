from __future__ import annotations

import re
from datetime import date, datetime

from vet.checks._regex import (
    ARCHITECTURE_SECTION_TITLES,
    CITATION_RE,
    COMMITS_RE,
    CRITICAL_SECTIONS,
    CROSSLINK_RE,
    EFFORT_HINT_RE,
    EMOJI_RE,
    LICENSE_CLAIM_RE,
    LICENSE_SECTION_TITLES,
    NEEDS_VERIF_RE,
    PHASE_SECTION_RE,
    REGIME_DISCLOSURE_PATTERNS,
    REGIME_SCOPE_NARROWING,
    REGIME_TRIGGER_PATTERNS,
    RELEASE_DATE_RE,
    RISK_SECTION_TITLES,
    SECTION_HEAD_RE,
    SOURCES_SECTION_ALIASES,
    STAR_COUNT_RE,
    SUCCESS_CRITERIA_RE,
    TODO_RE,
    VERDICT_LINE_RE,
    VERDICT_OPENER_RE,
    VERIFIED_ANCHOR_RE,
    VERSION_RE,
)
from vet.config import AuditConfig
from vet.models import CheckResult


def parse_document(text: str) -> list[str]:
    return SECTION_HEAD_RE.findall(text)


def check_required_sections(
    text: str, sections: list[str], *, strict_critical: bool
) -> CheckResult:
    section_set = set(sections)
    missing_critical = CRITICAL_SECTIONS - section_set
    has_sources = bool(SOURCES_SECTION_ALIASES & section_set)

    if strict_critical and missing_critical:
        return CheckResult(
            name="required_sections",
            severity="veto",
            score_weight=0.25,
            score_earned=0.0,
            detail=f"Missing critical section(s): {sorted(missing_critical)}",
            evidence=sorted(missing_critical),
            veto_reason=(
                "Operational Stability — missing required sections "
                f"{sorted(missing_critical)}"
            ),
        )
    if not has_sources and strict_critical:
        return CheckResult(
            name="required_sections",
            severity="warn",
            score_weight=0.25,
            score_earned=0.17,
            detail=(
                "No Sources/References section found. "
                f"Expected one of: {sorted(SOURCES_SECTION_ALIASES)}"
            ),
            evidence=sections,
        )
    if not strict_critical and not sections:
        return CheckResult(
            name="required_sections",
            severity="warn",
            score_weight=0.10,
            score_earned=0.05,
            detail="No ## sections found",
        )
    return CheckResult(
        name="required_sections",
        severity="pass",
        score_weight=0.25 if strict_critical else 0.10,
        score_earned=0.25 if strict_critical else 0.10,
        detail=f"Section structure OK ({len(sections)} ## headings)",
    )


def check_crosslinks(text: str, config: AuditConfig) -> CheckResult:
    matches = CROSSLINK_RE.findall(text)
    if not matches:
        return CheckResult(
            name="crosslinks",
            severity="pass",
            score_weight=0.15,
            score_earned=0.15,
            detail="No @path cross-links to validate",
        )

    dangling = sorted({m for m in matches if not config.resolve_link(m)})
    if dangling:
        return CheckResult(
            name="crosslinks",
            severity="veto",
            score_weight=0.15,
            score_earned=0.0,
            detail=f"{len(dangling)} dangling cross-link(s) of {len(matches)} total",
            evidence=dangling,
            veto_reason=(
                f"Scientific Integrity — {len(dangling)} cross-link(s) "
                "point to non-existent files"
            ),
        )
    return CheckResult(
        name="crosslinks",
        severity="pass",
        score_weight=0.15,
        score_earned=0.15,
        detail=f"{len(matches)} cross-link(s) all resolve",
    )


def check_citations(text: str, sections: list[str]) -> CheckResult:
    inline_matches = CITATION_RE.findall(text)
    has_sources_section = bool(SOURCES_SECTION_ALIASES & set(sections))

    if has_sources_section and not inline_matches:
        return CheckResult(
            name="citations",
            severity="pass",
            score_weight=0.10,
            score_earned=0.10,
            detail="Sources section present; inline citations optional",
        )
    if not inline_matches and not has_sources_section:
        return CheckResult(
            name="citations",
            severity="warn",
            score_weight=0.10,
            score_earned=0.03,
            detail="No Sources section and no inline [Source: ...] tags",
        )
    weak = [c for c in inline_matches if len(c.strip()) < 8]
    if weak:
        return CheckResult(
            name="citations",
            severity="warn",
            score_weight=0.10,
            score_earned=0.05,
            detail=f"{len(weak)} suspiciously short citation(s) of {len(inline_matches)} total",
            evidence=weak[:5],
        )
    return CheckResult(
        name="citations",
        severity="pass",
        score_weight=0.10,
        score_earned=0.10,
        detail=f"{len(inline_matches)} inline citation(s)"
        + (" + Sources section" if has_sources_section else ""),
    )


def check_needs_verification(
    text: str, max_age_days: int, today: date | None = None
) -> CheckResult:
    today = today or date.today()
    matches = NEEDS_VERIF_RE.findall(text)
    if not matches:
        return CheckResult(
            name="needs_verification_freshness",
            severity="pass",
            score_weight=0.10,
            score_earned=0.10,
            detail="No [NEEDS VERIFICATION] tags",
        )
    stale = []
    for d in matches:
        try:
            tag_date = datetime.strptime(d, "%Y-%m-%d").date()
            age = (today - tag_date).days
            if age > max_age_days:
                stale.append(f"{d} ({age}d old)")
        except ValueError:
            stale.append(f"{d} (unparseable date)")
    if stale:
        return CheckResult(
            name="needs_verification_freshness",
            severity="warn",
            score_weight=0.10,
            score_earned=0.05,
            detail=f"{len(stale)}/{len(matches)} NV tag(s) older than {max_age_days}d",
            evidence=stale,
        )
    return CheckResult(
        name="needs_verification_freshness",
        severity="pass",
        score_weight=0.10,
        score_earned=0.10,
        detail=f"{len(matches)} NV tag(s), all fresh (≤{max_age_days}d)",
    )


def check_prose_quality(text: str) -> CheckResult:
    emojis = EMOJI_RE.findall(text)
    todos = TODO_RE.findall(text)
    issues = []
    if emojis:
        issues.append(f"{len(emojis)} emoji character(s)")
    if todos:
        issues.append(f"{len(todos)} TODO/FIXME/XXX marker(s)")
    if not issues:
        return CheckResult(
            name="prose_quality",
            severity="pass",
            score_weight=0.05,
            score_earned=0.05,
            detail="No emoji or TODO/FIXME markers",
        )
    return CheckResult(
        name="prose_quality",
        severity="warn",
        score_weight=0.05,
        score_earned=0.015 if len(issues) > 1 else 0.025,
        detail="; ".join(issues),
    )


def check_frontmatter(text: str) -> CheckResult:
    if not text.startswith("---\n"):
        return CheckResult(
            name="frontmatter",
            severity="pass",
            score_weight=0.05,
            score_earned=0.05,
            detail="No YAML frontmatter (optional)",
        )
    fm_end = text.find("\n---\n", 4)
    if fm_end == -1:
        return CheckResult(
            name="frontmatter",
            severity="warn",
            score_weight=0.05,
            score_earned=0.0,
            detail="Frontmatter opener present but no closing ---",
        )
    return CheckResult(
        name="frontmatter",
        severity="pass",
        score_weight=0.05,
        score_earned=0.05,
        detail=f"Frontmatter parses ({fm_end - 4} chars)",
    )


def check_regime_disclosure(text: str) -> CheckResult:
    triggered = any(re.search(p, text, re.IGNORECASE) for p in REGIME_TRIGGER_PATTERNS)
    if not triggered:
        return CheckResult(
            name="regime_disclosure",
            severity="pass",
            score_weight=0.10,
            score_earned=0.10,
            detail="No evaluation-comparison claims detected",
        )
    disclosed = any(re.search(p, text, re.IGNORECASE) for p in REGIME_DISCLOSURE_PATTERNS)
    if disclosed:
        return CheckResult(
            name="regime_disclosure",
            severity="pass",
            score_weight=0.10,
            score_earned=0.10,
            detail="Evaluation-comparison claim with regime disclosure",
        )
    narrowed = any(re.search(p, text, re.IGNORECASE) for p in REGIME_SCOPE_NARROWING)
    if narrowed:
        return CheckResult(
            name="regime_disclosure",
            severity="warn",
            score_weight=0.10,
            score_earned=0.05,
            detail="Comparison claim narrowed but no formal regime disclosure",
        )
    return CheckResult(
        name="regime_disclosure",
        severity="veto",
        score_weight=0.10,
        score_earned=0.0,
        detail="Evaluation-comparison claim without regime disclosure",
        veto_reason=(
            "Scientific Integrity — comparison claim lacks regime disclosure "
            "(per-regime breakdown or explicit scope narrowing)"
        ),
    )


def _is_adoption_brief(text: str, target: str) -> bool:
    name = target.lower()
    if "adoption" in name or "prod-adoption" in name:
        return True
    if PHASE_SECTION_RE.search(text):
        return True
    if VERDICT_LINE_RE.search(text):
        return True
    return False


def _section_title_match(sections: list[str], candidates: tuple[str, ...]) -> bool:
    candidates_lower = tuple(c.lower() for c in candidates)
    for s in sections:
        s_lower = s.lower()
        for c in candidates_lower:
            if (
                s_lower == c
                or s_lower.startswith(c + " ")
                or s_lower.startswith(c + "—")
                or s_lower.startswith(c + " —")
            ):
                return True
    return False


def _section_body(text: str, title_candidates: tuple[str, ...]) -> str | None:
    pattern = re.compile(
        r"^##\s+(" + "|".join(re.escape(t) for t in title_candidates) + r")\s*$",
        re.MULTILINE | re.IGNORECASE,
    )
    m = pattern.search(text)
    if not m:
        return None
    start = m.end()
    next_section = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_section.start() if next_section else len(text)
    return text[start:end]


def check_brief_completeness(text: str, sections: list[str], target: str) -> CheckResult:
    if not _is_adoption_brief(text, target):
        return CheckResult(
            name="brief_completeness",
            severity="pass",
            score_weight=0.05,
            score_earned=0.05,
            detail="N/A — not an adoption-decision brief",
        )

    items = {
        "risks_section": _section_title_match(sections, RISK_SECTION_TITLES),
        "phase_section": bool(PHASE_SECTION_RE.search(text)),
        "architecture_section": _section_title_match(sections, ARCHITECTURE_SECTION_TITLES),
        "verdict_line": bool(VERDICT_LINE_RE.search(text)),
        "license_section": _section_title_match(sections, LICENSE_SECTION_TITLES),
    }
    present = sum(items.values())
    missing = sorted(k for k, v in items.items() if not v)
    score_earned = round((present / 5) * 0.05, 3)
    if present == 5:
        return CheckResult(
            name="brief_completeness",
            severity="pass",
            score_weight=0.05,
            score_earned=0.05,
            detail="All 5 completeness items present",
        )
    return CheckResult(
        name="brief_completeness",
        severity="warn",
        score_weight=0.05,
        score_earned=score_earned,
        detail=f"{present}/5 completeness items present; missing: {missing}",
        evidence=missing,
    )


def check_risk_discipline(text: str, target: str) -> CheckResult:
    if not _is_adoption_brief(text, target):
        return CheckResult(
            name="risk_discipline",
            severity="pass",
            score_weight=0.03,
            score_earned=0.03,
            detail="N/A — not an adoption-decision brief",
        )

    body = _section_body(text, RISK_SECTION_TITLES)
    if body is None:
        return CheckResult(
            name="risk_discipline",
            severity="warn",
            score_weight=0.03,
            score_earned=0.0,
            detail="No Risks & mitigations section found",
        )

    table_lines = [
        ln for ln in body.splitlines() if ln.strip().startswith("|") and ln.strip().endswith("|")
    ]
    if len(table_lines) < 3:
        bullet_re = re.compile(r"^-\s+\*\*[^*]+\*\*\s*[:—\-]", re.MULTILINE)
        bullets = bullet_re.findall(body)
        if len(bullets) >= 2:
            return CheckResult(
                name="risk_discipline",
                severity="warn",
                score_weight=0.03,
                score_earned=0.02,
                detail=f"{len(bullets)} risk bullets (table format earns full credit)",
            )
        return CheckResult(
            name="risk_discipline",
            severity="warn",
            score_weight=0.03,
            score_earned=0.01,
            detail="Risks section present but no parseable table or structured bullets",
        )

    header = table_lines[0].lower()
    has_severity = "severity" in header
    has_mitigation = "mitigation" in header or "mitigations" in header
    rows = table_lines[2:]
    risk_count = len(rows)

    empty_mitigations = 0
    if has_mitigation:
        for r in rows:
            cells = [c.strip() for c in r.strip("|").split("|")]
            if cells and not cells[-1]:
                empty_mitigations += 1

    score = 0.03
    issues: list[str] = []
    if not has_severity:
        score -= 0.01
        issues.append("no Severity column")
    if not has_mitigation:
        score -= 0.01
        issues.append("no Mitigation column")
    if risk_count < 2:
        score -= 0.005
        issues.append(f"only {risk_count} risk row(s) (expected ≥2)")
    if empty_mitigations > 0:
        score -= 0.005
        issues.append(f"{empty_mitigations} risk row(s) with empty mitigation")
    score = max(0.0, round(score, 3))

    if not issues:
        return CheckResult(
            name="risk_discipline",
            severity="pass",
            score_weight=0.03,
            score_earned=0.03,
            detail=f"{risk_count} risk rows with Severity + Mitigation columns",
        )
    return CheckResult(
        name="risk_discipline",
        severity="warn",
        score_weight=0.03,
        score_earned=score,
        detail=f"{risk_count} risk rows; issues: {issues}",
        evidence=issues,
    )


def check_phasing(text: str, sections: list[str], target: str) -> CheckResult:
    del sections  # phase headings detected from full text
    if not _is_adoption_brief(text, target):
        return CheckResult(
            name="phasing",
            severity="pass",
            score_weight=0.02,
            score_earned=0.02,
            detail="N/A — not an adoption-decision brief",
        )

    phase_count = len(PHASE_SECTION_RE.findall(text))
    has_success_criteria = bool(SUCCESS_CRITERIA_RE.search(text))

    if phase_count == 0:
        return CheckResult(
            name="phasing",
            severity="warn",
            score_weight=0.02,
            score_earned=0.0,
            detail="No Phase 1/2/3 scoping sections found",
        )
    if phase_count >= 2 and has_success_criteria:
        return CheckResult(
            name="phasing",
            severity="pass",
            score_weight=0.02,
            score_earned=0.02,
            detail=f"{phase_count} Phase sections + success/promotion criteria",
        )
    if phase_count >= 2:
        return CheckResult(
            name="phasing",
            severity="pass",
            score_weight=0.02,
            score_earned=0.015,
            detail=f"{phase_count} Phase sections (no explicit success criteria section)",
        )
    if has_success_criteria:
        return CheckResult(
            name="phasing",
            severity="warn",
            score_weight=0.02,
            score_earned=0.01,
            detail=f"Only {phase_count} Phase section (consider Phase 2/3 scoping)",
        )
    return CheckResult(
        name="phasing",
        severity="warn",
        score_weight=0.02,
        score_earned=0.005,
        detail=f"Only {phase_count} Phase section, no success/promotion criteria",
    )


def _claim_has_anchor_nearby(text: str, span: tuple[int, int], radius_chars: int = 240) -> bool:
    lo = max(0, span[0] - radius_chars)
    hi = min(len(text), span[1] + radius_chars)
    return bool(VERIFIED_ANCHOR_RE.search(text[lo:hi]))


def check_claim_evidence(text: str, target: str) -> CheckResult:
    if not _is_adoption_brief(text, target):
        return CheckResult(
            name="claim_evidence",
            severity="pass",
            score_weight=0.06,
            score_earned=0.06,
            detail="N/A — not an adoption-decision brief",
        )

    scan_text = re.sub(r"```[\s\S]*?```", "", text)
    claim_patterns = [
        ("license", LICENSE_CLAIM_RE),
        ("stars", STAR_COUNT_RE),
        ("version", VERSION_RE),
        ("commits", COMMITS_RE),
        ("release", RELEASE_DATE_RE),
    ]
    claims_by_value: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for label, pat in claim_patterns:
        for m in pat.finditer(scan_text):
            canonical = m.group(0).lower().replace(" ", "").replace("-", "")
            claims_by_value.setdefault((label, canonical), []).append(m.span())

    total_claims = len(claims_by_value)
    anchored = 0
    unanchored_samples: list[str] = []
    for (label, _canonical), spans in claims_by_value.items():
        if any(_claim_has_anchor_nearby(scan_text, sp) for sp in spans):
            anchored += 1
        else:
            sp0 = spans[0]
            snippet = scan_text[max(0, sp0[0] - 20) : sp0[1] + 20].replace("\n", " ").strip()
            unanchored_samples.append(f"{label}: …{snippet}…")

    if total_claims == 0:
        return CheckResult(
            name="claim_evidence",
            severity="pass",
            score_weight=0.06,
            score_earned=0.06,
            detail="No license/star/version/commit claims to verify",
        )

    coverage = anchored / total_claims
    if coverage >= 0.90:
        score, sev = 0.06, "pass"
    elif coverage >= 0.70:
        score, sev = 0.04, "warn"
    elif coverage >= 0.50:
        score, sev = 0.02, "warn"
    else:
        score, sev = 0.0, "warn"

    return CheckResult(
        name="claim_evidence",
        severity=sev,
        score_weight=0.06,
        score_earned=score,
        detail=f"{anchored}/{total_claims} claims anchored ({coverage:.0%})",
        evidence=unanchored_samples[:5],
    )


def check_abstract_synthesis(text: str, target: str) -> CheckResult:
    if not _is_adoption_brief(text, target):
        return CheckResult(
            name="abstract_synthesis",
            severity="pass",
            score_weight=0.04,
            score_earned=0.04,
            detail="N/A — not an adoption-decision brief",
        )

    summary_body = _section_body(text, ("Summary", "TL;DR", "Tldr", "TLDR"))
    if not summary_body or not summary_body.strip():
        return CheckResult(
            name="abstract_synthesis",
            severity="warn",
            score_weight=0.04,
            score_earned=0.0,
            detail="No ## Summary section body to evaluate",
        )

    body_clean = re.sub(r"[|*`]", " ", summary_body)
    words = [w for w in re.split(r"\s+", body_clean) if w]
    n_words = len(words)
    in_length_window = 50 <= n_words <= 400
    has_effort = bool(EFFORT_HINT_RE.search(summary_body))
    has_verdict_opener = bool(VERDICT_OPENER_RE.search(summary_body))

    signals_present = sum([in_length_window, has_effort, has_verdict_opener])
    missing = []
    if not in_length_window:
        missing.append(f"length={n_words}w (target 50-400)")
    if not has_effort:
        missing.append("no effort estimate")
    if not has_verdict_opener:
        missing.append("no verdict-flavored opener")

    if signals_present == 3:
        return CheckResult(
            name="abstract_synthesis",
            severity="pass",
            score_weight=0.04,
            score_earned=0.04,
            detail=f"Summary {n_words}w + effort estimate + verdict opener",
        )
    if signals_present == 2:
        return CheckResult(
            name="abstract_synthesis",
            severity="warn",
            score_weight=0.04,
            score_earned=0.025,
            detail=f"2/3 abstract signals; missing: {missing}",
            evidence=missing,
        )
    if signals_present == 1:
        return CheckResult(
            name="abstract_synthesis",
            severity="warn",
            score_weight=0.04,
            score_earned=0.01,
            detail=f"1/3 abstract signals; missing: {missing}",
            evidence=missing,
        )
    return CheckResult(
        name="abstract_synthesis",
        severity="warn",
        score_weight=0.04,
        score_earned=0.0,
        detail=f"0/3 abstract signals; missing: {missing}",
        evidence=missing,
    )
