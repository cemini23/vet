from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Severity = Literal["pass", "warn", "veto"]
Verdict = Literal["PASS", "WARN", "REJECT", "ERROR"]


@dataclass
class CheckResult:
    name: str
    severity: Severity
    score_weight: float
    score_earned: float
    detail: str
    evidence: list[str] = field(default_factory=list)
    veto_reason: str | None = None


@dataclass
class AuditReport:
    target: str
    profile: str
    verdict: Verdict
    static_score: float
    veto_gates: list[str]
    checks: list[CheckResult]
    summary: str
