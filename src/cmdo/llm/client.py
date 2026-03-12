"""LLM API client for command generation."""

from __future__ import annotations

import time

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError

from cmdo.llm.parser import parse_response
from cmdo.llm.prompt import build_prompt
from cmdo.models import CommandResult, Config, ShellContext


def generate_command(
    query: str, context: ShellContext, config: Config
) -> CommandResult:
    """Send query + context to LLM and return a structured CommandResult."""
    client = OpenAI(
        api_key=config.api_key,
        base_url=config.base_url or None,
    )
    messages = build_prompt(query, context)

    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=messages,
                max_completion_tokens=1024,
            )
            raw = response.choices[0].message.content or ""
            result = parse_response(raw)
            if result.command:
                return result
            # Empty command on first attempt — retry
            if attempt == 0:
                continue
            return result

        except RateLimitError:
            if attempt == 0:
                wait = 5
                from rich.console import Console

                Console().print(f"[yellow]⏳ Rate limited. Retrying in {wait}s...[/yellow]")
                time.sleep(wait)
                continue
            raise

        except (APITimeoutError, APIConnectionError):
            if attempt == 0:
                continue
            raise

    # Should not reach here, but just in case
    return CommandResult(command="", explanation="Failed to generate command.", confidence=0.0)
