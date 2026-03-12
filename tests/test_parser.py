"""Tests for LLM response parsing."""

import pytest

from cmdo.llm.parser import parse_response
from cmdo.models import RiskLevel


class TestParseResponse:
    def test_valid_json(self) -> None:
        raw = '{"command": "ls -la", "explanation": "List files", "risk_level": "SAFE", "risk_reason": null, "alternatives": [], "is_multi_step": false, "estimated_duration": "instant", "confidence": 0.95}'
        result = parse_response(raw)
        assert result.command == "ls -la"
        assert result.explanation == "List files"
        assert result.risk_level == RiskLevel.SAFE
        assert result.confidence == 0.95

    def test_json_in_code_block(self) -> None:
        raw = '```json\n{"command": "tar -czf a.tar.gz dir/", "explanation": "Compress", "risk_level": "SAFE", "confidence": 0.9}\n```'
        result = parse_response(raw)
        assert result.command == "tar -czf a.tar.gz dir/"

    def test_dangerous_risk_level(self) -> None:
        raw = '{"command": "rm -rf .", "explanation": "Delete all", "risk_level": "DANGEROUS", "risk_reason": "Deletes everything", "confidence": 0.8}'
        result = parse_response(raw)
        assert result.risk_level == RiskLevel.DANGEROUS
        assert result.risk_reason == "Deletes everything"

    def test_caution_risk_level(self) -> None:
        raw = '{"command": "sudo apt install vim", "explanation": "Install vim", "risk_level": "CAUTION", "confidence": 0.9}'
        result = parse_response(raw)
        assert result.risk_level == RiskLevel.CAUTION

    def test_missing_fields_use_defaults(self) -> None:
        raw = '{"command": "echo hi"}'
        result = parse_response(raw)
        assert result.command == "echo hi"
        assert result.risk_level == RiskLevel.SAFE
        assert result.confidence == 0.8

    def test_invalid_json_fallback(self) -> None:
        raw = "just some text that is not json"
        result = parse_response(raw)
        assert result.command == raw.strip()
        assert result.confidence == 0.3

    def test_multi_step(self) -> None:
        raw = '{"command": "mkdir out && cp *.py out/", "explanation": "Copy", "risk_level": "SAFE", "is_multi_step": true, "confidence": 0.85}'
        result = parse_response(raw)
        assert result.is_multi_step is True

    def test_alternatives(self) -> None:
        raw = '{"command": "rm -rf data/", "explanation": "Delete data", "risk_level": "DANGEROUS", "alternatives": ["mv data/ ~/.Trash/"], "confidence": 0.9}'
        result = parse_response(raw)
        assert result.alternatives == ["mv data/ ~/.Trash/"]
