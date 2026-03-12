"""Tests for forbidden command detection."""

import pytest

from cmdo.safety.forbidden import check_forbidden


class TestCheckForbidden:
    @pytest.mark.parametrize(
        "command",
        [
            ":(){ :|:& };:",
            "dd if=/dev/zero of=/dev/sda",
            "dd if=/dev/urandom of=/dev/sdb",
            "rm -rf /",
            "rm -rf /*",
        ],
    )
    def test_forbidden_commands_blocked(self, command: str) -> None:
        result = check_forbidden(command)
        assert result is not None, f"Expected forbidden for: {command}"

    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf /tmp/test",
            "dd if=input.img of=output.img",
            "ls -la",
            "echo 'hello world'",
        ],
    )
    def test_allowed_commands_pass(self, command: str) -> None:
        result = check_forbidden(command)
        assert result is None, f"Expected allowed for: {command}"
