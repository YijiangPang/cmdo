"""Tests for context gathering."""

from unittest.mock import patch

from cmdo.context import detect_tools, gather_context


class TestDetectTools:
    def test_detects_available_tools(self) -> None:
        with patch("cmdo.context._run") as mock_run:
            mock_run.side_effect = lambda cmd, **kw: "/usr/bin/tar" if "tar" in cmd else ""
            result = detect_tools(["tar", "nonexistent"])
            assert "tar" in result
            assert "nonexistent" not in result


class TestGatherContext:
    def test_returns_shell_context(self) -> None:
        ctx = gather_context()
        assert ctx.cwd != ""
        assert ctx.user != ""
        assert ctx.os != ""
