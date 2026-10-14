"""Regression tests for the 2026-10-13 audit findings.

Each test pins a failure that shipped in 0.2.1. Most assert that a BENIGN
input passes — the gate had no false-positive coverage before this file.
"""

from __future__ import annotations

from pathlib import Path

from vet.checks._regex import LICENSE_CLAIM_RE
from vet.checks.base import check_crosslinks, check_prose_quality, check_regime_disclosure
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
