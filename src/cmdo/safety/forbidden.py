"""Hard-blocked forbidden commands."""

from __future__ import annotations

import re

FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (
        r":\(\)\{\s*:\|:&\s*\};:",
        "Fork bomb detected. This command would crash your system.",
    ),
    (
        r"\bdd\s+if=/dev/(zero|urandom)\s+of=/dev/[hs]d[a-z]\b",
        "Disk wipe detected. This would destroy all data on the target drive.",
    ),
    (
        r"\brm\s+-\w*rf?\w*\s+/\s*$",
        "Full system deletion detected. This would destroy your entire filesystem.",
    ),
    (
        r"\brm\s+-\w*rf?\w*\s+/\*",
        "Full system deletion detected. This would destroy your entire filesystem.",
    ),
]


def check_forbidden(command: str) -> str | None:
    """Check if a command is forbidden.

    Returns an error message if forbidden, None if allowed.
    """
    for pattern, message in FORBIDDEN_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return message
    return None
