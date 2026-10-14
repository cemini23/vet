"""Regression tests for the 2026-10-13 audit findings.

Each test pins a failure that shipped in 0.2.1. Most assert that a BENIGN
input passes — the gate had no false-positive coverage before this file.
"""

from __future__ import annotations

from pathlib import Path

from vet.checks._regex import LICENSE_CLAIM_RE
from vet.checks.base import (
    check_citations,
    check_crosslinks,
    check_needs_verification,
    check_phasing,
    check_prose_quality,
    check_regime_disclosure,
    check_required_sections,
    check_risk_discipline,
)
from vet.checks.skillmd import _parse_frontmatter
from vet.cli import main as cli_main
from vet.config import AuditConfig
from vet.engine import audit_file

FIXTURES = Path(__file__).parent / "fixtures"


_DEFAULT_META = 'license: MIT\nmetadata:\n  author: cemini23\n  version: "1.0.0"'


def _skill(name: str, body: str, meta: str = _DEFAULT_META) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        "description: A long enough description for the frontmatter check to be satisfied.\n"
        f"{meta}\n"
        "---\n\n"
        f"# {name.replace('-', ' ').title()}\n\n"
        f"{body}\n"
    )


# --- F-01: nested YAML frontmatter -----------------------------------------


def test_nested_yaml_metadata_is_parsed():
    fields, err = _parse_frontmatter(_skill("nested-check", "Body."))
    assert err is None
    assert fields["metadata.author"] == "cemini23"
    assert fields["metadata.version"] == "1.0.0"


def test_quoted_scalar_loses_its_quotes():
    fields, _ = _parse_frontmatter(_skill("quoted", "Body.", meta='name: "quoted"\nlicense: "MIT"'))
    assert fields["license"] == "MIT"


def test_block_scalar_description_is_captured():
    text = "---\nname: x\ndescription: >-\n  Line one.\n  Line two.\n---\n\n# X\n\nBody.\n"
    fields, err = _parse_frontmatter(text)
    assert err is None
    assert "Line one." in fields["description"]


def test_nested_metadata_does_not_warn(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(_skill("nested-check", "Body text that is long enough to satisfy the body check."))
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="skillmd"))
    metadata = [c for c in report.checks if c.name == "skillmd_metadata"][0]
    assert metadata.severity == "pass"


# --- F-02: TODO/FIXME marker detection -------------------------------------


def test_todo_in_prose_is_not_a_marker():
    result = check_prose_quality("NO PLACEHOLDERS - real implementations, not TODO stubs.")
    assert result.severity == "pass"


def test_ssn_redaction_example_is_not_a_marker():
    result = check_prose_quality("Redact SSNs as XXX-XX-XXXX before sharing.")
    assert result.severity == "pass"


def test_real_todo_placeholder_is_flagged():
    assert check_prose_quality("Body. TODO: wire the exporter.").severity == "warn"
    assert check_prose_quality("Body. <!-- FIXME - broken -->").severity == "warn"


def test_todo_inside_a_code_fence_is_ignored():
    result = check_prose_quality("Prose.\n\n```bash\ngrep -rn TODO src/\n```\n")
    assert result.severity == "pass"


# --- F-05: cross-links inside code spans -----------------------------------


def test_crosslink_inside_inline_code_is_ignored(tmp_path):
    config = AuditConfig.from_paths(tmp_path, profile="minimal")
    result = check_crosslinks("Document `@path/to/file.md` as an example.", config)
    assert result.severity == "pass"


def test_crosslink_inside_a_fence_is_ignored(tmp_path):
    config = AuditConfig.from_paths(tmp_path, profile="minimal")
    result = check_crosslinks("Example:\n\n```\n@osint-wiki/sources/foo.md\n```\n", config)
    assert result.severity == "pass"


def test_real_dangling_crosslink_still_vetoes(tmp_path):
    config = AuditConfig.from_paths(tmp_path, profile="minimal")
    result = check_crosslinks("See @missing-page.md for detail.", config)
    assert result.severity == "veto"


# --- F-06: headings inside fences are not sections -------------------------


def test_bash_comment_is_not_a_section_heading():
    from vet.checks.base import parse_document

    assert parse_document("```bash\n# not a heading\n## Phase 1\n```\n") == []
    assert parse_document("## Real Heading\n") == ["Real Heading"]


# --- F-07 / F-15: profile scoring and exit codes ----------------------------


def test_minimal_profile_can_pass(tmp_path):
    p = tmp_path / "doc.md"
    p.write_text("# Overview\n\nSome text.\n\n## Sources\n\n- [x](https://example.com)\n")
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="minimal"))
    assert report.verdict == "PASS", report.summary
    assert report.static_score == 100.0


def test_non_strict_warn_does_not_block_commits(tmp_path):
    p = tmp_path / "weak.md"
    p.write_text("# Overview\n\nText with an emoji here.\n")
    assert cli_main([str(p), "--profile", "minimal"]) == 0


def test_strict_warn_blocks_commits(tmp_path):
    p = tmp_path / "weak.md"
    p.write_text("# Overview\n\nText with an emoji here.\n")
    assert cli_main([str(p), "--profile", "minimal", "--strict"]) == 2


# --- F-11: unreadable input must not abort the run -------------------------


def test_non_utf8_file_does_not_crash_the_run(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe---\nname: x\n---\n")
    good = FIXTURES / "pass_brief.md"
    code = cli_main([str(bad), str(good), "--profile", "brief"])
    assert code == 3


# --- F-03: regime disclosure on ordinary comparative English ----------------


def test_comparative_prose_is_not_a_regime_claim():
    text = "A local Unix socket is better than polling over HTTP and wins on tail latency."
    assert check_regime_disclosure(text).severity == "pass"


def test_comparative_prose_in_a_code_fence_is_ignored():
    text = "Prose.\n\n```\nthis beats the baseline\n```\n"
    assert check_regime_disclosure(text).severity == "pass"


def test_quantitative_comparison_without_disclosure_warns_but_does_not_veto():
    text = "The new sizing method beats the baseline on Sharpe ratio in backtest."
    result = check_regime_disclosure(text)
    assert result.severity == "warn"
    assert not result.veto_reason


def test_quantitative_comparison_with_disclosure_passes():
    text = "It beats the baseline on Sharpe ratio in backtest, broken out per-regime."
    assert check_regime_disclosure(text).severity == "pass"


# --- F-04: claim evidence on ordinary English -------------------------------


def test_proprietary_and_unlicensed_are_not_licence_claims():
    assert not LICENSE_CLAIM_RE.search("Keep proprietary customer keys in the vault.")
    assert not LICENSE_CLAIM_RE.search("The unlicensed scraper must be removed.")
    assert LICENSE_CLAIM_RE.search("Released under MIT.")


def test_frontmatter_version_is_not_a_body_claim(tmp_path):
    p = tmp_path / "note-adoption.md"
    p.write_text(
        "---\n"
        "title: Note\n"
        "metadata:\n"
        '  version: "v9.9"\n'
        "---\n\n"
        "## Target\n\nclaude.ai\n\n"
        "## Summary\n\nAdopt it. [Source: https://example.com/a]\n\n"
        "## Sources\n\n- [Source: https://example.com/a]\n"
    )
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="brief"))
    claim = [c for c in report.checks if c.name == "claim_evidence"][0]
    assert claim.severity == "pass", claim.detail


# --- F-09: the prompt profile ----------------------------------------------


def test_prompt_file_detects_the_prompt_profile(tmp_path):
    p = tmp_path / "research-prompt.md"
    p.write_text("# Research Prompt\n\nYou are an analyst. Investigate and cite sources.\n")
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="prompt"))
    assert report.verdict == "PASS", report.summary


def test_prompt_file_is_not_forced_through_brief_sections(tmp_path):
    p = tmp_path / "prompts" / "research.md"
    p.parent.mkdir()
    p.write_text("# Research Prompt\n\nYou are an analyst. Investigate and cite sources.\n")
    assert cli_main([str(p)]) == 0


def test_prompt_profile_requires_a_real_body(tmp_path):
    p = tmp_path / "prompt.md"
    p.write_text("# x\n")
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="prompt"))
    assert report.verdict == "WARN"


# --- F-10: skillmd body accepts H2 and ignores fenced comments --------------


def test_skillmd_body_accepts_an_h2_opener(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\n"
        "name: h2-skill\n"
        "description: A long enough description for the frontmatter check to be satisfied.\n"
        "---\n\n"
        "## Overview\n\nBody text that is comfortably past the forty character minimum.\n"
    )
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="skillmd"))
    body = [c for c in report.checks if c.name == "skillmd_body"][0]
    assert body.severity == "pass", body.detail


def test_fenced_bash_comment_is_not_a_skill_heading(tmp_path):
    p = tmp_path / "SKILL.md"
    p.write_text(
        "---\n"
        "name: fenced-skill\n"
        "description: A long enough description for the frontmatter check to be satisfied.\n"
        "---\n\n"
        "```bash\n# not a heading\n```\n\nBody text that is past the forty character minimum.\n"
    )
    report = audit_file(p, AuditConfig.from_paths(tmp_path, profile="skillmd"))
    body = [c for c in report.checks if c.name == "skillmd_body"][0]
    assert body.severity == "warn"
    assert "heading" in body.detail


# --- F-08: info severity never blocks ---------------------------------------


def test_info_severity_does_not_affect_the_verdict():
    from vet.engine import assemble_report
    from vet.models import CheckResult

    checks = [
        CheckResult("a", "pass", 0.90, 0.90, "ok"),
        CheckResult("b", "info", 0.10, 0.10, "advisory only"),
    ]
    report = assemble_report("t.md", "prompt", checks, AuditConfig.from_paths(Path(".")))
    assert report.verdict == "PASS"
    assert report.static_score == 100.0


# --- F-12: missing paths are reported, not dropped --------------------------


def test_missing_path_is_reported_and_exits_three(tmp_path, capsys):
    good = FIXTURES / "pass_brief.md"
    code = cli_main([str(good), str(tmp_path / "absent.md"), "--profile", "brief"])
    assert code == 3
    assert "does not exist" in capsys.readouterr().err


# --- F-16: --json is a single valid document --------------------------------


def test_multi_file_json_is_one_valid_document(tmp_path, capsys):
    import json

    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    body = "# Overview\n\nSome text.\n\n## Sources\n\n- [x](https://example.com)\n"
    a.write_text(body)
    b.write_text(body)
    cli_main([str(tmp_path), "--profile", "minimal", "--json"])
    json.loads(capsys.readouterr().out)


# --- F-17: build and dependency directories are skipped ---------------------


def test_venv_contents_are_not_audited(tmp_path, capsys):
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "junk.md").write_text("# Junk\n")
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "ok.md").write_text("# Overview\n\nText.\n")
    cli_main([str(tmp_path), "--profile", "minimal"])
    assert "junk.md" not in capsys.readouterr().out


# --- F-19: declared but unmounted federation aliases ------------------------


def _alias_workspace(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        "# Test\n\n## Related Wikis\n\n"
        "| Alias | Path | Visibility | Description |\n"
        "|-------|------|------------|-------------|\n"
        "| `osint-wiki` | `/nonexistent/sibling/wiki/` | Private | not mounted |\n"
    )


def test_declared_but_unmounted_alias_is_not_dangling(tmp_path):
    _alias_workspace(tmp_path)
    config = AuditConfig.from_paths(tmp_path, profile="minimal")
    result = check_crosslinks("See @osint-wiki/sources/foo.md.", config)
    assert result.severity == "pass"
    assert "not mounted" in result.detail


def test_undeclared_missing_link_still_vetoes(tmp_path):
    config = AuditConfig.from_paths(tmp_path, profile="minimal")
    result = check_crosslinks("See @briefs/missing.md.", config)
    assert result.severity == "veto"


# --- F-10: remaining check corrections --------------------------------------


def test_empty_sources_section_warns():
    text = "## Sources\n\n## Risks\n\nsomething\n"
    assert check_citations(text, ["Sources", "Risks"]).severity == "warn"


def test_populated_sources_section_passes():
    text = "## Sources\n\n- [Source: https://example.com/a]\n"
    assert check_citations(text, ["Sources"]).severity == "pass"


def test_undated_needs_verification_warns():
    result = check_needs_verification("Claim here [NEEDS VERIFICATION].", 30)
    assert result.severity == "warn"
    assert any("undated" in e for e in result.evidence)


def test_dated_fresh_needs_verification_passes():
    from datetime import UTC, datetime

    today = datetime.now(UTC).date().isoformat()
    assert check_needs_verification(f"Claim [{today}]", 30).severity == "pass"


def test_structured_risk_bullets_pass():
    text = (
        "## Risks & mitigations\n\n"
        "- **Drift**: pin the versions\n"
        "- **Cost**: cap the spend\n"
    )
    assert check_risk_discipline(text, "note-adoption.md").severity == "pass"


def test_empty_mitigation_is_caught_when_severity_is_the_last_column():
    text = (
        "## Risks & mitigations\n\n"
        "| Risk | Mitigation | Severity |\n"
        "|------|------------|----------|\n"
        "| Drift |  | High |\n"
        "| Cost | cap the spend | Low |\n"
    )
    result = check_risk_discipline(text, "note-adoption.md")
    assert result.severity == "warn"
    assert any("empty mitigation" in i for i in result.evidence)


def test_single_phase_with_success_criteria_passes():
    text = "## Phase 1\n\nDo the thing.\n\n## Success criteria\n\nIt works.\n"
    result = check_phasing(text, ["Phase 1", "Success criteria"], "note-adoption.md")
    assert result.severity == "pass"


def test_empty_critical_section_warns():
    text = "## Target\n\n## Summary\n\nAdopt this tool.\n\n## Sources\n\n- [Source: x]\n"
    result = check_required_sections(text, ["Target", "Summary", "Sources"], strict_critical=True)
    assert result.severity == "warn"
    assert "empty" in result.detail.lower()


def test_short_but_present_critical_section_is_accepted():
    text = "## Target\n\nclaude.ai\n\n## Summary\n\nAdopt this.\n\n## Sources\n\n- [Source: x]\n"
    result = check_required_sections(text, ["Target", "Summary", "Sources"], strict_critical=True)
    assert result.severity == "pass"


def test_heading_case_is_ignored():
    text = "## TARGET\n\nclaude.ai\n\n## SUMMARY\n\nAdopt this.\n\n## SOURCES\n\n- [Source: x]\n"
    result = check_required_sections(
        text, ["TARGET", "SUMMARY", "SOURCES"], strict_critical=True
    )
    assert result.severity == "pass"
