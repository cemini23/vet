from __future__ import annotations

from pathlib import Path

from vet.cli import main as cli_main
from vet.config import AuditConfig, load_wiki_aliases
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


def _write_alias_root(tmp_path: Path) -> Path:
    """A root with a CLAUDE.md alias table, a wiki page, and a repo-root file."""
    (tmp_path / "wiki" / "concepts").mkdir(parents=True)
    (tmp_path / "wiki" / "concepts" / "real.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "LESSONS.md").write_text("x\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        "| Alias | Path | Visibility | Description |\n"
        "|-------|------|------------|-------------|\n"
        "| `osint-wiki` | `wiki/` | **Private** | test |\n"
        "| `ghost-wiki` | `../does-not-exist/wiki/` | Public | test |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_alias_link_resolves(tmp_path: Path):
    root = _write_alias_root(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\n## Sources\n\n"
        "- [Source: @osint-wiki/concepts/real.md]\n",
        encoding="utf-8",
    )
    report = audit_file(brief, AuditConfig.from_paths(root, profile="brief"))
    assert not [c for c in report.checks if c.name == "crosslinks" and c.severity == "veto"]


def test_alias_resolves_paths_outside_the_wiki_dir(tmp_path: Path):
    root = _write_alias_root(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\n## Sources\n\n"
        "- [Source: @osint-wiki/LESSONS.md]\n",
        encoding="utf-8",
    )
    report = audit_file(brief, AuditConfig.from_paths(root, profile="brief"))
    assert not [c for c in report.checks if c.name == "crosslinks" and c.severity == "veto"]


def test_alias_link_still_dangling_when_target_absent(tmp_path: Path):
    root = _write_alias_root(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\n## Sources\n\n"
        "- [Source: @osint-wiki/concepts/missing.md]\n",
        encoding="utf-8",
    )
    report = audit_file(brief, AuditConfig.from_paths(root, profile="brief"))
    assert report.verdict == "REJECT"
    assert "crosslinks" in {c.name for c in report.checks if c.severity == "veto"}


def test_unknown_alias_is_not_treated_as_a_directory(tmp_path: Path):
    root = _write_alias_root(tmp_path)
    config = AuditConfig.from_paths(root, profile="brief")
    # `ghost-wiki` names a directory that does not exist -> not in the table.
    assert config.resolve_link("ghost-wiki/concepts/real.md") is False
    # A plain wiki-relative path is unaffected by the alias path.
    assert config.resolve_link("concepts/real.md") is True
    assert config.resolve_link("osint-wiki/concepts/real.md") is True
    assert config.resolve_link("osint-wiki/LESSONS.md") is True


def test_cli_passes_a_brief_that_cites_an_alias(tmp_path: Path, capsys):
    """Regression guard: the CLI must carry wiki_aliases into the per-file config.

    It used to rebuild AuditConfig field by field and drop wiki_aliases, which made
    every alias-citing brief REJECT. Unit tests on audit_file did not catch that.
    """
    root = _write_alias_root(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\n## Sources\n\n"
        "- [Source: @osint-wiki/concepts/real.md]\n",
        encoding="utf-8",
    )
    assert cli_main([str(brief), "--root", str(root), "--profile", "brief"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_rejects_a_brief_that_cites_a_missing_alias_target(tmp_path: Path, capsys):
    root = _write_alias_root(tmp_path)
    brief = tmp_path / "brief.md"
    brief.write_text(
        "## Target\n\nx\n\n## Summary\n\ny\n\n## Sources\n\n"
        "- [Source: @osint-wiki/concepts/nope.md]\n",
        encoding="utf-8",
    )
    assert cli_main([str(brief), "--root", str(root), "--profile", "brief"]) == 2


def test_aliases_are_empty_without_a_claude_md(tmp_path: Path):
    assert load_wiki_aliases(tmp_path) == {}


def test_aliases_never_raise_on_an_unreadable_claude_md(tmp_path: Path):
    # A directory named CLAUDE.md must not blow up auditing at import time.
    (tmp_path / "CLAUDE.md").mkdir()
    assert load_wiki_aliases(tmp_path) == {}


def test_blank_alias_path_row_is_skipped(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text(
        "| Alias | Path | Visibility | Description |\n"
        "|-------|------|------------|-------------|\n"
        "| `weird` |    | Public | no path |\n",
        encoding="utf-8",
    )
    assert load_wiki_aliases(tmp_path) == {}
