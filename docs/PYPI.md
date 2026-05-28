# PyPI trusted publishing

Package name: **`agent-vet`** (import: `vet`)

## One-time setup (PyPI)

1. Create project: https://pypi.org/manage/projects/ → **agent-vet**
2. **Publishing** → **Add a new publisher**
   - PyPI project: `agent-vet`
   - Owner: `cemini23`
   - Repository: `vet`
   - Workflow: `publish.yml`
   - Environment: *(leave blank unless using GitHub Environment)*

Repeat for `phase0` and `wikilint` on their repos.

## Release

```bash
git tag v0.2.1
git push origin v0.2.1
gh release create v0.2.1 --title "v0.2.1" --notes "..."
```

The `publish.yml` workflow runs on **Release published** and uploads via OIDC (no API token in repo).

## Install after publish

```bash
pip install agent-vet
pip install phase0
pip install wikilint
```
