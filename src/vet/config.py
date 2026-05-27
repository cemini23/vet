from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AuditConfig:
    root: Path
    link_dirs: list[Path] = field(default_factory=list)
    profile: str = "brief"
    nv_age_days: int = 30
    strict: bool = False
    pass_threshold: float = 80.0

    def resolve_link(self, rel_path: str) -> bool:
        for base in self.link_dirs:
            if (base / rel_path).is_file():
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
        return cls(root=root, link_dirs=unique, **kwargs)
