# vet examples

Copy these into your repo or point CI at this directory.

| Path | Expected |
|------|----------|
| `good-skill/SKILL.md` | PASS |
| `bad-skill/SKILL.md` | REJECT (missing description) |
| `good-brief.md` | PASS |
| `bad-brief.md` | REJECT (missing Target) |

```bash
vet examples/good-skill/SKILL.md --profile skillmd
vet examples/bad-skill/SKILL.md --profile skillmd --strict
```
