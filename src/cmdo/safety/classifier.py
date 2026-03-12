"""Local risk classification using pattern matching."""

from __future__ import annotations

import re

from cmdo.models import RiskLevel

# Patterns ordered from most to least dangerous
DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-\w*r\w*\s+-\w*f\w*|-\w*f\w*\s+-\w*r\w*|-\w*rf\w*)", "Recursive forced deletion"),
    (r"\brm\s+-\w*r", "Recursive deletion"),
    (r"\bmkfs\b", "Filesystem format"),
    (r"\bdd\s+if=", "Direct disk write"),
    (r">\s*/dev/", "Write to device"),
    (r":\(\)\{\s*:\|:&\s*\};:", "Fork bomb"),
    (r"\bchmod\s+(-\w*R\w*\s+)?777\b", "Open permissions to everyone"),
    (r"\bDROP\s+(TABLE|DATABASE)\b", "Database destruction"),
    (r"\bTRUNCATE\s+", "Database truncation"),
    (r"\b(shutdown|reboot)\b", "System shutdown/reboot"),
    (r"\bsudo\s+rm\b", "Privileged deletion"),
    (r"\bcurl\b.*\|\s*(sudo\s+)?(ba)?sh\b", "Remote code execution"),
    (r"\bwget\b.*\|\s*(sudo\s+)?(ba)?sh\b", "Remote code execution"),
    (r"\bformat\b", "Disk format"),
    (r"\bfdisk\b", "Disk partition"),
    (r":>\s*\S+", "File truncation"),
    (r">\s*/etc/", "Overwrite system config"),
]

CAUTION_PATTERNS: list[tuple[str, str]] = [
    (r"\bsudo\b", "Requires elevated privileges"),
    (r"\bmv\b", "File move/rename (overwrite risk)"),
    (r"\bchmod\b", "Permission change"),
    (r"\bchown\b", "Ownership change"),
    (r"\bpip\s+install\b", "Package installation"),
    (r"\bnpm\s+install\s+-g\b", "Global package installation"),
    (r"\bbrew\s+install\b", "Package installation"),
    (r"\bapt\s+(install|remove)\b", "Package management"),
    (r"\bgit\s+push\s+--force\b", "Force push"),
    (r"\bgit\s+reset\s+--hard\b", "Hard reset"),
    (r"\bsed\s+-i\b", "In-place file edit"),
    (r"\bdocker\s+rm\b", "Container removal"),
    (r"\bkill\b", "Process termination"),
    (r"\bpkill\b", "Process termination"),
    (r"/etc/|/usr/", "System path modification"),
]


def classify_risk(command: str) -> tuple[RiskLevel, str | None]:
    """Classify command risk level using local pattern matching.

    Returns (risk_level, reason) tuple.
    """
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.DANGEROUS, reason

    for pattern, reason in CAUTION_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return RiskLevel.CAUTION, reason

    return RiskLevel.SAFE, None


def upgrade_risk(
    llm_level: RiskLevel, local_level: RiskLevel
) -> RiskLevel:
    """Return the higher of two risk levels."""
    order = {RiskLevel.SAFE: 0, RiskLevel.CAUTION: 1, RiskLevel.DANGEROUS: 2}
    if order[local_level] > order[llm_level]:
        return local_level
    return llm_level
