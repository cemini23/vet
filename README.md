# vet

Static veto-gate auditor for **agent skills**, **briefs**, and **prompts** before they ship.

Battle-tested patterns from production agent curation workflows (MedSkillAudit-style veto gates, adoption-brief discipline, Anthropic SKILL.md compliance). Stdlib-only. No API keys. No network calls.

## Install

```bash
pip install git+https://github.com/cemini23/vet.git
# or from a clone:
pip install -e .
```

## Quick start

```bash
# Adoption / design brief (default profile)
vet briefs/my-adoption-brief.md

# Anthropic SKILL.md or Cursor skill
vet .cursor/skills/my-skill/SKILL.md
vet path/to/SKILL.md --profile skillmd

# Portable markdown subset
vet docs/agent-runbook.md --profile minimal

# JSON for CI
vet briefs/*.md --json

# Strict: warnings become REJECT
vet briefs/*.md --strict
```

## Profiles

| Profile | Best for | Checks |
|---------|----------|--------|
| `brief` | Tool-adoption / design briefs | 12 static checks: sections, crosslinks, citations, freshness tags, regime disclosure, adoption completeness, risk table, phasing, claim-evidence, abstract quality |
| `skillmd` | `SKILL.md` agent skills | Required frontmatter (`name`, `description`), body structure, recommended metadata, prose hygiene |
| `minimal` | General agent markdown | Crosslinks, citations, freshness, frontmatter, prose |

## Cross-link resolution

`@concepts/foo.md` links resolve against:

1. `--root` (default: cwd or `VET_ROOT`)
2. `{root}/wiki` if present
3. Extra paths via `--link-dir wiki --link-dir docs`

```bash
vet briefs/ship.md --root . --link-dir wiki
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | PASS |
| 1 | WARN |
| 2 | REJECT (veto gate or `--strict`) |
| 3 | ERROR (file not found / unreadable) |

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install git+https://github.com/cemini23/vet.git
- run: vet skills/ --profile skillmd --strict
```

## Veto gates

Two gates can hard-stop a document regardless of score:

- **Operational Stability** — parseable structure, required sections present
- **Scientific Integrity** — dangling cross-links, undisclosed evaluation comparisons

## Lineage

Clean-room patterns adapted from:

- MedSkillAudit veto-gate framework (MIT)
- Academic peer-review checklist ports (MIT)
- Anthropic Agent Skills frontmatter spec

Domain-specific logic (trading, prod execution) is intentionally **not** included — this tool is agent-ecosystem neutral.

## Related

- [phase0](https://github.com/cemini23/phase0) — third-party tool adoption audits (coming next)

## License

MIT — see [LICENSE](LICENSE).
