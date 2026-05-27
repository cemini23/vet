from __future__ import annotations

from pathlib import Path

from vet.checks.base import parse_document
from vet.config import AuditConfig
from vet.models import AuditReport, CheckResult
from vet.profiles import run_profile_checks


def audit_file(path: Path, config: AuditConfig) -> AuditReport:
    text = path.read_text(encoding="utf-8")
    sections = parse_document(text)
    checks = run_profile_checks(
        config.profile,
        text=text,
        sections=sections,
        target=str(path),
        config=config,
    )
    return assemble_report(str(path), config.profile, checks, config)


def assemble_report(
    target: str,
    profile: str,
    checks: list[CheckResult],
    config: AuditConfig,
) -> AuditReport:
    veto_gates = [c.veto_reason for c in checks if c.severity == "veto" and c.veto_reason]
    static_score = round(sum(c.score_earned for c in checks) * 100, 1)

    if veto_gates:
        verdict = "REJECT"
        summary = f"REJECT — {len(veto_gates)} veto gate(s) triggered. Score irrelevant."
    elif config.strict and any(c.severity == "warn" for c in checks):
        verdict = "REJECT"
        summary = f"REJECT (--strict) — score {static_score}/100, warnings treated as veto"
    elif any(c.severity == "warn" for c in checks):
        verdict = "WARN"
        summary = f"WARN — score {static_score}/100, warnings present but no veto"
    elif static_score >= config.pass_threshold:
        verdict = "PASS"
        summary = f"PASS — score {static_score}/100, all checks clean"
    else:
        verdict = "WARN"
        summary = (
            f"WARN — score {static_score}/100 below "
            f"{config.pass_threshold}-point pass threshold"
        )

    return AuditReport(
        target=target,
        profile=profile,
        verdict=verdict,
        static_score=static_score,
        veto_gates=veto_gates,
        checks=checks,
        summary=summary,
    )
