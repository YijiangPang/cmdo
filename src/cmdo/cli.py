"""CLI entry point for cmdo."""

from __future__ import annotations

import sys

import click
from rich.console import Console

from cmdo import __version__

console = Console()


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("query", nargs=-1)
@click.option("--config", "do_config", is_flag=True, help="Configure cmdo")
@click.option("--show", is_flag=True, help="Show current configuration (use with --config)")
@click.option("--reset", is_flag=True, help="Reset configuration (use with --config)")
@click.option("--dry-run", "-d", is_flag=True, help="Generate command without executing")
@click.option("--yes", "-y", is_flag=True, help="Auto-confirm safe commands")
@click.option("--model", "-m", default=None, help="Override default model")
@click.option("--version", "-V", is_flag=True, help="Show version")
def main(
    query: tuple[str, ...],
    do_config: bool,
    show: bool,
    reset: bool,
    dry_run: bool,
    yes: bool,
    model: str | None,
    version: bool,
) -> None:
    """cmdo — Natural language to shell commands.

    \b
    Examples:
      cmdo "find all Python files larger than 1MB"
      cmdo "start a local HTTP server on port 8080"
      cmdo --explain "tar -czf archive.tar.gz dir/"
      cmdo --dry-run "delete the temp folder"
    """
    if version:
        click.echo(f"cmdo v{__version__}")
        return

    # Config management
    if do_config:
        if show:
            from cmdo.config import show_config
            show_config()
        elif reset:
            from cmdo.config import reset_config
            reset_config()
        else:
            from cmdo.config import configure
            configure()
        return

    # No query provided
    if not query:
        click.echo(f"cmdo v{__version__} — Natural language to shell commands")
        click.echo('Usage: cmdo "your instruction"')
        click.echo("       cmdo --config        Set up or reconfigure")
        click.echo("       cmdo --help          Show full help")
        return

    # Core flow
    query_str = " ".join(query)
    _run_query(query_str, dry_run=dry_run, auto_yes=yes, model_override=model)


def _run_query(
    query: str,
    *,
    dry_run: bool = False,
    auto_yes: bool = False,
    model_override: str | None = None,
) -> None:
    """Core flow: query → generate → display → confirm → execute."""
    from cmdo.clipboard import copy_to_clipboard
    from cmdo.config import ensure_configured
    from cmdo.context import gather_context
    from cmdo.display import (
        display_command,
        display_error,
        display_execution_result,
        display_forbidden,
        edit_command,
        prompt_user,
    )
    from cmdo.executor import execute_command
    from cmdo.llm.client import generate_command
    from cmdo.models import RiskLevel, UserAction
    from cmdo.safety.classifier import classify_risk, upgrade_risk
    from cmdo.safety.forbidden import check_forbidden

    # 1. Ensure configured
    config = ensure_configured()
    if model_override:
        config.model = model_override

    # 2. Gather context
    with console.status("[dim]Gathering context...[/dim]", spinner="dots"):
        context = gather_context()

    # 3. Generate command via LLM
    try:
        with console.status("[dim]Thinking...[/dim]", spinner="dots"):
            result = generate_command(query, context, config)
    except Exception as e:
        display_error(f"Failed to generate command: {e}")
        sys.exit(2)

    if not result.command:
        display_error("Could not generate a command for that request.")
        sys.exit(1)

    # 4. Safety checks
    forbidden_msg = check_forbidden(result.command)
    if forbidden_msg:
        display_forbidden(forbidden_msg)
        sys.exit(1)

    local_risk, local_reason = classify_risk(result.command)
    result.risk_level = upgrade_risk(result.risk_level, local_risk)
    if local_reason and result.risk_reason is None:
        result.risk_reason = local_reason

    # 5. Display
    display_command(result)

    # 6. Dry run — stop here
    if dry_run:
        return

    # 7. Auto-confirm if --yes flag or config auto_confirm_safe
    if (auto_yes or config.auto_confirm_safe) and result.risk_level != RiskLevel.DANGEROUS:
        action = UserAction.EXECUTE
    else:
        action = prompt_user(result)

    # 8. Handle action
    if action == UserAction.CANCEL:
        console.print("[dim]Cancelled.[/dim]")
        sys.exit(1)

    if action == UserAction.COPY:
        if copy_to_clipboard(result.command):
            console.print("[green]📋 Copied to clipboard![/green]")
        else:
            console.print(f"[yellow]Could not copy. Here's the command:[/yellow]\n{result.command}")
        return

    if action == UserAction.EDIT:
        edited = edit_command(result.command)
        if edited != result.command:
            # Re-check safety on edited command
            forbidden_msg = check_forbidden(edited)
            if forbidden_msg:
                display_forbidden(forbidden_msg)
                sys.exit(1)
            result.command = edited

    # 9. Execute
    stepwise = action == UserAction.EXECUTE_STEPWISE
    exec_result = execute_command(result.command, stepwise=stepwise)
    display_execution_result(exec_result.exit_code, exec_result.duration)

    sys.exit(0 if exec_result.exit_code == 0 else 2)


if __name__ == "__main__":
    main()
