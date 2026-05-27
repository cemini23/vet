from __future__ import annotations

from collections.abc import Callable

from vet.checks import base, skillmd
from vet.config import AuditConfig

CheckFn = Callable[..., object]

PROFILES: dict[str, list[str]] = {
    "brief": [
        "required_sections",
        "crosslinks",
        "citations",
        "needs_verification_freshness",
        "prose_quality",
        "frontmatter",
        "regime_disclosure",
        "brief_completeness",
        "risk_discipline",
        "phasing",
        "claim_evidence",
        "abstract_synthesis",
    ],
    "minimal": [
        "required_sections_soft",
        "crosslinks",
        "citations",
        "needs_verification_freshness",
        "prose_quality",
        "frontmatter",
    ],
    "skillmd": [
        "skillmd_frontmatter",
        "skillmd_body",
        "skillmd_metadata",
        "skillmd_prose",
    ],
}


def available_profiles() -> list[str]:
    return sorted(PROFILES)


def run_profile_checks(
    profile: str,
    *,
    text: str,
    sections: list[str],
    target: str,
    config: AuditConfig,
):
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile {profile!r}. Choose from: {available_profiles()}")

    checks = []
    for name in PROFILES[profile]:
        fn = _CHECK_DISPATCH[name]
        checks.append(fn(text=text, sections=sections, target=target, config=config))
    return checks


def _required_sections(text, sections, target, config):
    del target
    strict = config.profile != "minimal"
    return base.check_required_sections(text, sections, strict_critical=strict)


def _required_sections_soft(text, sections, target, config):
    del target
    return base.check_required_sections(text, sections, strict_critical=False)


def _crosslinks(text, sections, target, config):
    del sections, target
    return base.check_crosslinks(text, config)


def _citations(text, sections, target, config):
    del target, config
    return base.check_citations(text, sections)


def _needs_verification_freshness(text, sections, target, config):
    del sections, target
    return base.check_needs_verification(text, config.nv_age_days)


def _prose_quality(text, sections, target, config):
    del sections, target, config
    return base.check_prose_quality(text)


def _frontmatter(text, sections, target, config):
    del sections, target, config
    return base.check_frontmatter(text)


def _regime_disclosure(text, sections, target, config):
    del sections, target, config
    return base.check_regime_disclosure(text)


def _brief_completeness(text, sections, target, config):
    del config
    return base.check_brief_completeness(text, sections, target)


def _risk_discipline(text, sections, target, config):
    del sections, config
    return base.check_risk_discipline(text, target)


def _phasing(text, sections, target, config):
    del config
    return base.check_phasing(text, sections, target)


def _claim_evidence(text, sections, target, config):
    del sections, config
    return base.check_claim_evidence(text, target)


def _abstract_synthesis(text, sections, target, config):
    del sections, config
    return base.check_abstract_synthesis(text, target)


def _skillmd_frontmatter(text, sections, target, config):
    del sections, target, config
    return skillmd.check_skillmd_frontmatter(text)


def _skillmd_body(text, sections, target, config):
    del sections, target, config
    return skillmd.check_skillmd_body(text)


def _skillmd_metadata(text, sections, target, config):
    del sections, target, config
    return skillmd.check_skillmd_metadata(text)


def _skillmd_prose(text, sections, target, config):
    del sections, target, config
    return skillmd.check_skillmd_prose(text)


_CHECK_DISPATCH = {
    "required_sections": _required_sections,
    "required_sections_soft": _required_sections_soft,
    "crosslinks": _crosslinks,
    "citations": _citations,
    "needs_verification_freshness": _needs_verification_freshness,
    "prose_quality": _prose_quality,
    "frontmatter": _frontmatter,
    "regime_disclosure": _regime_disclosure,
    "brief_completeness": _brief_completeness,
    "risk_discipline": _risk_discipline,
    "phasing": _phasing,
    "claim_evidence": _claim_evidence,
    "abstract_synthesis": _abstract_synthesis,
    "skillmd_frontmatter": _skillmd_frontmatter,
    "skillmd_body": _skillmd_body,
    "skillmd_metadata": _skillmd_metadata,
    "skillmd_prose": _skillmd_prose,
}
