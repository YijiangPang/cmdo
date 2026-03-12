"""Clipboard integration."""

from __future__ import annotations


def copy_to_clipboard(command: str) -> bool:
    """Copy command to system clipboard. Returns True on success."""
    try:
        import pyperclip

        pyperclip.copy(command)
        return True
    except Exception:
        return False
