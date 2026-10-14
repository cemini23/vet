from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# Rows of the CLAUDE.md 'Related Wikis' table: | `alias` | `path/to/wiki/` | ...
_ALIAS_ROW_RE = re.compile(
    r"^\|\s*`(?P<alias>[a-z0-9_-]+)`\s*\|\s*`?(?P<path>[^`\n|]+)`?\s*\|",
    re.MULTILINE,
)


def load_wiki_aliases(root: Path) -> dict[str, tuple[Path, ...]]:
    """Map wiki aliases to candidate base directories, from the root CLAUDE.md.

    A brief copied into a sibling federation wiki cites this repo as
    ``@osint-wiki/sources/foo.md``. That alias names this repo's ``wiki/``; the
    sibling may also cite files that live outside ``wiki/`` (``LESSONS.md``,
    ``scripts/...``, ``briefs/...``). Each alias therefore yields two ordered
    bases: the wiki directory itself, then the directory that owns it. Both are
    tried, so either form resolves.

    Returns an empty map when there is no readable CLAUDE.md, or when no table row
    names a directory that exists. Never raises: a malformed table must not break
    auditing.
    """
    claude_md = root / "CLAUDE.md"
    aliases: dict[str, tuple[Path, ...]] = {}
    if not claude_md.is_file():
        return aliases
    try:
        text = claude_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return aliases
    for match in _ALIAS_ROW_RE.finditer(text):
        alias = match.group("alias").strip()
        rel = match.group("path").strip().rstrip("/")
        if not alias or not rel:
            continue
        candidate = (root / rel).resolve()
        if not candidate.is_dir() and (candidate / "wiki").is_dir():
            candidate = candidate / "wiki"
        if candidate.is_dir():
            aliases[alias] = (candidate, candidate.parent)
    return aliases


def load_declared_aliases(root: Path) -> set[str]:
    """Every alias named in CLAUDE.md, whether or not its directory exists here.

    A single-repo CI checkout has no sibling wiki on disk. Those aliases are
    declared and legitimate, so a link that uses one must not read as dangling.
    """
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return set()
    try:
        text = claude_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {
        m.group("alias").strip()
        for m in _ALIAS_ROW_RE.finditer(text)
        if m.group("alias").strip()
    }


@dataclass
class AuditConfig:
    root: Path
    link_dirs: list[Path] = field(default_factory=list)
    profile: str = "brief"
    nv_age_days: int = 30
    strict: bool = False
    pass_threshold: float = 80.0
    # Appended last so external positional callers keep their argument order.
    wiki_aliases: dict[str, tuple[Path, ...]] = field(default_factory=dict)
    unmounted_aliases: set[str] = field(default_factory=set)

    def link_status(self, rel_path: str) -> str:
        """Return "ok", "unmounted", or "missing" for one @path reference.

        "unmounted" means the link names a declared federation alias whose
        sibling repo is not checked out here. That is expected on CI, where only
        one repo exists, so it is not a defect.
        """
        for base in self.link_dirs:
            if (base / rel_path).is_file():
                return "ok"
        alias, sep, rest = rel_path.partition("/")
        if sep and rest:
            for base in self.wiki_aliases.get(alias, ()):
                if (base / rest).is_file():
                    return "ok"
            if alias in self.unmounted_aliases:
                return "unmounted"
        return "missing"

    def resolve_link(self, rel_path: str) -> bool:
        return self.link_status(rel_path) == "ok"

    @classmethod
    def from_paths(
        cls,
        root: Path,
        extra_link_dirs: list[Path] | None = None,
        **kwargs,
    ) -> AuditConfig:
        root = root.resolve()
        dirs: list[Path] = [root]
        wiki = root / "wiki"
        if wiki.is_dir():
            dirs.append(wiki)
        if extra_link_dirs:
            dirs.extend(p.resolve() for p in extra_link_dirs)
        # Preserve order, drop duplicates
        seen: set[Path] = set()
        unique: list[Path] = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                unique.append(d)
        if kwargs.get("wiki_aliases") is None:
            mounted = load_wiki_aliases(root)
            kwargs["wiki_aliases"] = mounted
            if kwargs.get("unmounted_aliases") is None:
                kwargs["unmounted_aliases"] = load_declared_aliases(root) - set(mounted)
        return cls(root=root, link_dirs=unique, **kwargs)
