"""Terminal display and user interaction."""

from __future__ import annotations

import readline  # noqa: F401 — enables input() line editing
import sys

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cmdo.models import CommandResult, RiskLevel, UserAction

console = Console()

RISK_STYLES = {
    RiskLevel.SAFE: ("green", "🤖"),
    RiskLevel.CAUTION: ("yellow", "🟡"),
    RiskLevel.DANGEROUS: ("red", "🔴"),
}


def display_command(result: CommandResult) -> None:
    """Render the command result with color-coded formatting."""
    color, _ = RISK_STYLES.get(result.risk_level, ("white", "🤖"))

    # Command box
    console.print()
    console.print("🤖 Will run:")
    console.print(Panel(
        Text(result.command, style=f"bold {color}"),
        border_style=color,
        expand=False,
        padding=(0, 1),
    ))

    # Risk warning
    if result.risk_level == RiskLevel.DANGEROUS:
        reason = result.risk_reason or "This command may be destructive."
        console.print(f"[bold red]🔴 WARNING: DESTRUCTIVE — {reason}[/bold red]")
        console.print("[red]   This action may be IRREVERSIBLE.[/red]")
    elif result.risk_level == RiskLevel.CAUTION:
        reason = result.risk_reason or "This command modifies system state."
        console.print(f"[yellow]🟡 CAUTION: {reason}[/yellow]")

    # Explanation
    if result.explanation:
        console.print(f"\n[dim]📝 {result.explanation}[/dim]")

    # Low confidence warning
    if result.confidence < 0.5:
        pct = int(result.confidence * 100)
        console.print(f"\n[yellow]⚠ Low confidence ({pct}%). Please review carefully.[/yellow]")

    console.print()


def prompt_user(result: CommandResult) -> UserAction:
    """Prompt user for action based on risk level."""
    if result.risk_level == RiskLevel.DANGEROUS:
        console.print('[bold red]Type "yes" to confirm, or [n] to cancel:[/bold red]')
        try:
            answer = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return UserAction.CANCEL
        if answer == "yes":
            return UserAction.EXECUTE
        return UserAction.CANCEL
    else:
        # Show action menu
        if result.is_multi_step:
            console.print(r"\[Y] Execute all  \[s] Step-by-step  \[e] Edit  \[c] Copy  \[n] Cancel")
        else:
            console.print(r"\[Y] Execute  \[e] Edit  \[c] Copy  \[n] Cancel")

        try:
            answer = input("> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            console.print()
            return UserAction.CANCEL

        if answer in ("", "y"):
            return UserAction.EXECUTE
        if answer == "s" and result.is_multi_step:
            return UserAction.EXECUTE_STEPWISE
        if answer == "e":
            return UserAction.EDIT
        if answer == "c":
            return UserAction.COPY
        return UserAction.CANCEL


def edit_command(command: str) -> str:
    """Allow user to edit the command inline."""
    console.print("[dim]Edit the command (press Enter when done):[/dim]")

    def prefill_input(text: str) -> str:
        import readline as rl
        def hook():
            rl.insert_text(text)
            rl.redisplay()
        rl.set_pre_input_hook(hook)
        try:
            result = input("> ")
        finally:
            rl.set_pre_input_hook()
        return result

    try:
        edited = prefill_input(command)
        return edited.strip() or command
    except (KeyboardInterrupt, EOFError):
        console.print()
        return command


def display_execution_result(exit_code: int, duration: float) -> None:
    """Show execution result summary."""
    if exit_code == 0:
        console.print(f"[green]✅ Done ({duration:.1f}s)[/green]")
    else:
        console.print(f"[red]❌ Command failed (exit code {exit_code})[/red]")


def display_error(message: str) -> None:
    """Display an error message."""
    console.print(f"[red]❌ {message}[/red]")


def display_forbidden(message: str) -> None:
    """Display a forbidden command message."""
    console.print(f"\n[bold red]🚫 {message}[/bold red]")
    console.print("[red]This command is blocked for safety and cannot be executed.[/red]\n")
