---
name: example-skill
description: >-
  Example agent skill for unit tests. Use when demonstrating vet skillmd profile
  validation on Anthropic-style SKILL.md files.
license: MIT
metadata.author: vet-tests
metadata.version: "1.0.0"
---

# Example skill

## When to use

Run vet on skills before publishing them.

## Workflow

1. Write SKILL.md
2. Run `vet --profile skillmd path/to/SKILL.md`
