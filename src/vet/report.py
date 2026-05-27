from __future__ import annotations

import json
from dataclasses import asdict

from vet.models import AuditReport


def render_text(report: AuditReport) -> str:
    lines = [
        "=" * 78,
        f"vet  ::  {report.target}  [profile={report.profile}]",
        "=" * 78,
        "",
        f"VERDICT: {report.verdict}",
        f"SCORE:   {report.static_score}/100",
        "",
    ]
    if report.veto_gates:
        lines.append("VETO GATES TRIGGERED:")
        for vg in report.veto_gates:
            lines.append(f"  x {vg}")
        lines.append("")
    lines.append("CHECKS:")
    for c in report.checks:
        glyph = {"pass": "+", "warn": "!", "veto": "x"}[c.severity]
        lines.append(f"  {glyph} [{c.severity.upper():4}] {c.name}: {c.detail}")
        for e in c.evidence[:5]:
            lines.append(f"      - {e}")
        if len(c.evidence) > 5:
            lines.append(f"      ... and {len(c.evidence) - 5} more")
    lines.extend(["", f"=> {report.summary}"])
    return "\n".join(lines)


def render_json(report: AuditReport) -> str:
    return json.dumps(asdict(report), indent=2)
