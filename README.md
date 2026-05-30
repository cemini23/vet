# vet

[![CI](https://github.com/cemini23/vet/actions/workflows/ci.yml/badge.svg)](https://github.com/cemini23/vet/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Static veto-gate auditor for **agent skills**, **briefs**, and **prompts** before they ship.

Part of the [agent toolkit](https://github.com/cemini23/agent-toolkit-demo): **vet** (your artifacts) → **phase0** (their repos) → **wikilint** (your wiki).

Stdlib-only · No API keys · No network calls

## Install

```bash
pip install git+https://github.com/cemini23/vet.git
pip install -e .                    # from clone
# PyPI (after configuring trusted publishing):
# pip install agent-vet
```

## Quick start

```bash
vet briefs/my-adoption-brief.md
vet .cursor/skills/my-skill/SKILL.md          # auto profile: skillmd
vet docs/runbook.md --profile minimal
vet skills/ --strict --json
```

## Profiles

| Profile | Best for | Checks |
|---------|----------|--------|
| `brief` | Tool-adoption / design briefs | 12 static checks |
| `skillmd` | `SKILL.md` / Cursor skills | Frontmatter, body, metadata, prose |
| `minimal` | General agent markdown | Crosslinks, citations, freshness, prose |

## GitHub Action (recommended)

```yaml
- uses: actions/checkout@v4
- uses: cemini23/vet@v0.2.0
  with:
    path: .
    profile: skillmd
    strict: "true"
    glob: "**/SKILL.md"
```

The action installs `vet` from the tagged ref — no PyPI required.

See `examples/workflows/vet-skills.yml` and the [demo repo](https://github.com/cemini23/agent-toolkit-demo).

## Veto gates

- **Operational Stability** — required structure missing
- **Scientific Integrity** — dangling cross-links, undisclosed evaluation comparisons

## Exit codes

`0` PASS · `1` WARN · `2` REJECT · `3` ERROR

## Related

- Methodology newsletter: [Outlier Weekly](https://outlierweekly.substack.com)
- YouTube: [@Cemini23](https://www.youtube.com/@Cemini23)
- Agent meta-wiki: [cemini-claude-code-CCC](https://github.com/cemini23/cemini-claude-code-CCC)
- Toolkit: [phase0](https://github.com/cemini23/phase0) · [wikilint](https://github.com/cemini23/wikilint) · [agent-toolkit-demo](https://github.com/cemini23/agent-toolkit-demo) · [ara-schema](https://github.com/cemini23/ara-schema)

## License

MIT
