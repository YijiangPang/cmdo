"""Parse LLM responses into CommandResult."""

from __future__ import annotations

import json
import re

from cmdo.models import CommandResult, RiskLevel


def _extract_json(text: str) -> str:
    """Extract JSON from text that may contain markdown fences."""
    # Try to find JSON in code block
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try to find raw JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def _parse_risk_level(value: str) -> RiskLevel:
    """Parse risk level string to enum."""
    value = value.upper().strip()
    if value == "DANGEROUS":
        return RiskLevel.DANGEROUS
    if value == "CAUTION":
        return RiskLevel.CAUTION
    return RiskLevel.SAFE


def parse_response(raw: str) -> CommandResult:
    """Parse LLM JSON response into a CommandResult."""
    json_str = _extract_json(raw)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Fallback: treat the whole response as a command
        return CommandResult(
            command=raw.strip(),
            explanation="(Could not parse LLM response)",
            confidence=0.3,
        )

    return CommandResult(
        command=data.get("command", ""),
        explanation=data.get("explanation", ""),
        risk_level=_parse_risk_level(data.get("risk_level", "SAFE")),
        risk_reason=data.get("risk_reason"),
        alternatives=data.get("alternatives", []),
        is_multi_step=data.get("is_multi_step", False),
        estimated_duration=data.get("estimated_duration"),
        confidence=float(data.get("confidence", 0.8)),
    )
