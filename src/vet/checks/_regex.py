from __future__ import annotations

import re

SECTION_HEAD_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
CROSSLINK_RE = re.compile(r"@([a-zA-Z0-9_\-/]+\.md)\b")
CITATION_RE = re.compile(r"\[Sources?:\s*([^\]]+)\]")
NEEDS_VERIF_RE = re.compile(r"\[NEEDS VERIFICATION\s+(\d{4}-\d{2}-\d{2})\]")
TODO_RE = re.compile(r"\b(TODO|FIXME|XXX)\b")
EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F6FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "]"
)

CRITICAL_SECTIONS = {"Target", "Summary"}
SOURCES_SECTION_ALIASES = {
    "Sources",
    "Source",
    "Primary sources",
    "References",
    "Cross-references",
}

LICENSE_CLAIM_RE = re.compile(
    r"\b(MIT|Apache-?2\.0|AGPL-?3\.0|GPL-?3\.0|GPL-?2\.0|BSD-?2|BSD-?3|MPL-?2\.0|"
    r"LGPL|ISC|Unlicense|proprietary|unlicensed)\b",
    re.IGNORECASE,
)
STAR_COUNT_RE = re.compile(r"\b\d{1,3}(?:,\d{3})*\s*(?:stars?|★|⭐)\b", re.IGNORECASE)
VERSION_RE = re.compile(r"\bv\d+\.\d+(?:\.\d+)?(?:-[a-z0-9]+)?\b")
COMMITS_RE = re.compile(r"\b\d{1,5}\s+commits?\b", re.IGNORECASE)
RELEASE_DATE_RE = re.compile(r"\blast (?:commit|push|release)\s+\d{4}-\d{2}-\d{2}\b", re.IGNORECASE)

VERIFIED_ANCHOR_RE = re.compile(
    r"\bVERIFIED\s+\d{4}-\d{2}-\d{2}|"
    r"\bPhase-?0 audit|"
    r"\baudit (?:complete|cleared|2\d{3}-\d{2}-\d{2})|"
    r"\[Source[s]?:|"
    r"\[NEEDS VERIFICATION|"
    r"\[CONFIRMED\]|\[TENTATIVE\]|\[RETRACTED\]",
    re.IGNORECASE,
)

EFFORT_HINT_RE = re.compile(
    r"\beffort\b|\bestimate\b|\*\*\d+(?:-\d+)?\s*(?:hr|hour|day|week|min)",
    re.IGNORECASE,
)
VERDICT_OPENER_RE = re.compile(
    r"^\s*(?:Adopt|Steal-from|Reject|Reference|Defer|Install|GO|NO-?GO|CONDITIONAL-?GO|"
    r"This brief|Adoption recommendation|Recommendation:?)\b",
    re.IGNORECASE | re.MULTILINE,
)

REGIME_TRIGGER_PATTERNS = [
    r"\bbeats\b",
    r"\boutperforms\b",
    r"\bsurpasses\b",
    r"\bwins on\b",
    r"\bimproves over\b",
    r"\bimproved by \d+% over\b",
    r"\bbetter than\b",
    r"\bsuperior to\b",
    r"\bleading method\b",
    r"\bbest-performing\b",
    r"\b\d+(\.\d+)?%\s*(vs|against)\s*\w+",
]
REGIME_DISCLOSURE_PATTERNS = [
    r"per-regime",
    r"by regime",
    r"regime-conditioned",
    r"regime mix",
    r"\bPRS\b",
    r"B/\|A\|",
    r"\bρ\b",
    r"prior rank correlation",
    r"single-regime",
    r"during \w+ regime",
]
REGIME_SCOPE_NARROWING = [
    r"\bpreliminary\b",
    r"\bexploratory\b",
    r"\bsingle-experiment\b",
    r"\bpilot\b",
    r"\bproof of concept\b",
    r"\bcase study\b",
]

PHASE_SECTION_RE = re.compile(r"^#{2,3}\s+Phase\s*\d", re.MULTILINE | re.IGNORECASE)
RISK_SECTION_TITLES = (
    "Risks",
    "Risks & mitigations",
    "Risks and mitigations",
    "Risk",
    "Risk assessment",
    "Risks and gating conditions",
    "Risks & gating conditions",
)
LICENSE_SECTION_TITLES = ("License", "License posture", "Licensing", "License & IP")
ARCHITECTURE_SECTION_TITLES = (
    "Architecture",
    "Design",
    "System architecture",
    "Integration architecture",
)
VERDICT_LINE_RE = re.compile(r"\*\*(GO|NO-GO|CONDITIONAL-?GO)\*\*", re.IGNORECASE)
SUCCESS_CRITERIA_RE = re.compile(
    r"^#{2,3}\s+(Success criteria|Triggers|GO criteria|Acceptance criteria|"
    r"Promotion criteria|Done when)",
    re.MULTILINE | re.IGNORECASE,
)

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
