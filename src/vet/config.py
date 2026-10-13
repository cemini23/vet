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
        text = claude_md.read_text(errors="replace")
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

    def resolve_link(self, rel_path: str) -> bool:
        for base in self.link_dirs:
            if (base / rel_path).is_file():
                return True
        alias, sep, rest = rel_path.partition("/")
        if sep and rest:
            for base in self.wiki_aliases.get(alias, ()):
                if (base / rest).is_file():
                    return True
        return False

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
            kwargs["wiki_aliases"] = load_wiki_aliases(root)
        return cls(root=root, link_dirs=unique, **kwargs)
