"""Command execution with real-time output streaming."""

from __future__ import annotations

import os
import signal
import subprocess
import time

from cmdo.models import ExecutionResult


def execute_command(command: str, stepwise: bool = False) -> ExecutionResult:
    """Execute a shell command with real-time output streaming."""
    if stepwise:
        return _execute_stepwise(command)
    return _execute_single(command)


def _execute_single(command: str) -> ExecutionResult:
    """Execute a single command."""
    shell = os.environ.get("SHELL", "/bin/sh")
    start = time.time()
    was_interrupted = False

    try:
        process = subprocess.Popen(
            [shell, "-c", command],
            stdout=None,  # inherit — stream to terminal
            stderr=None,  # inherit — stream to terminal
        )
        exit_code = process.wait()

    except KeyboardInterrupt:
        # Send SIGINT to child process group
        was_interrupted = True
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        except (ProcessLookupError, OSError):
            pass
        try:
            exit_code = process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            exit_code = -1

    duration = time.time() - start
    return ExecutionResult(
        exit_code=exit_code,
        duration=duration,
        was_interrupted=was_interrupted,
    )


def _execute_stepwise(command: str) -> ExecutionResult:
    """Execute a multi-step command one step at a time."""
    from rich.console import Console
    console = Console()

    # Split on && and ; (simple split — doesn't handle quoted strings perfectly)
    import re
    steps = re.split(r"\s*&&\s*|\s*;\s*", command)
    steps = [s.strip() for s in steps if s.strip()]

    total_duration = 0.0
    for i, step in enumerate(steps, 1):
        console.print(f"\n[bold]Step {i}/{len(steps)}:[/bold] {step}")
        result = _execute_single(step)
        total_duration += result.duration

        if result.was_interrupted:
            return ExecutionResult(
                exit_code=-1,
                duration=total_duration,
                was_interrupted=True,
            )

        if result.exit_code != 0:
            console.print(f"[red]Step {i} failed (exit code {result.exit_code}). Stopping.[/red]")
            return ExecutionResult(
                exit_code=result.exit_code,
                duration=total_duration,
            )

        console.print(f"[green]Step {i} done ({result.duration:.1f}s)[/green]")

        if i < len(steps):
            try:
                answer = input("Continue to next step? [Y/n] ").strip().lower()
                if answer == "n":
                    return ExecutionResult(
                        exit_code=0,
                        duration=total_duration,
                        was_interrupted=True,
                    )
            except (KeyboardInterrupt, EOFError):
                return ExecutionResult(
                    exit_code=0,
                    duration=total_duration,
                    was_interrupted=True,
                )

    return ExecutionResult(exit_code=0, duration=total_duration)
