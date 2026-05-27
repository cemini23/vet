from __future__ import annotations

from pathlib import Path

from vet.config import AuditConfig
from vet.engine import audit_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_pass_brief():
    report = audit_file(
        FIXTURES / "pass_brief.md",
        AuditConfig.from_paths(FIXTURES, profile="brief"),
    )
    assert report.verdict == "PASS"
    assert report.static_score >= 80


def test_fail_missing_target():
    report = audit_file(
        FIXTURES / "fail_missing_target.md",
        AuditConfig.from_paths(FIXTURES, profile="brief"),
    )
    assert report.verdict == "REJECT"
    assert any("required_sections" in c.name for c in report.checks if c.severity == "veto")


def test_fail_dangling_link():
    report = audit_file(
        FIXTURES / "fail_dangling_link.md",
        AuditConfig.from_paths(FIXTURES, profile="brief"),
    )
    assert report.verdict == "REJECT"
    assert "crosslinks" in {c.name for c in report.checks if c.severity == "veto"}


def test_pass_skillmd():
    report = audit_file(
        FIXTURES / "pass_skillmd" / "SKILL.md",
        AuditConfig.from_paths(FIXTURES, profile="skillmd"),
    )
    assert report.verdict == "PASS"


def test_fail_skillmd_no_description():
    report = audit_file(
        FIXTURES / "fail_skillmd_no_description" / "SKILL.md",
        AuditConfig.from_paths(FIXTURES, profile="skillmd"),
    )
    assert report.verdict == "REJECT"


def test_strict_upgrades_warnings(tmp_path: Path):
    brief = tmp_path / "warn.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\nTODO: fix later\n",
        encoding="utf-8",
    )
    report = audit_file(
        brief,
        AuditConfig.from_paths(tmp_path, profile="brief", strict=True),
    )
    assert report.verdict == "REJECT"
