"""Prompt construction for LLM command generation."""

from __future__ import annotations

from cmdo.models import ShellContext

SYSTEM_PROMPT = """\
You are a shell command generator. Given a natural language instruction \
and shell context, produce the exact command(s) to execute.

Rules:
1. Output ONLY valid shell commands for the user's OS and shell.
2. Prefer simple, standard tools over obscure ones.
3. Use tools confirmed available in the context. If the best tool \
is unavailable, use a fallback AND note it.
4. Never generate commands that require interactive input (use flags \
to avoid prompts, e.g., `rm -f` not `rm -i` when deletion is intended).
5. For file operations, use the cwd_listing to resolve ambiguous names.
6. Classify risk level:
   - SAFE: read-only, create files, list, search, compress
   - CAUTION: modify files, install packages, change permissions
   - DANGEROUS: delete files, format disks, overwrite data, sudo operations, \
network-facing services, database drops, recursive force operations
7. If the request is ambiguous, prefer the SAFER interpretation.
8. If you cannot generate a command, say so — never hallucinate.

Respond in JSON:
{
  "command": "...",
  "explanation": "...",
  "risk_level": "SAFE|CAUTION|DANGEROUS",
  "risk_reason": "..." or null,
  "alternatives": [...] or [],
  "is_multi_step": true|false,
  "estimated_duration": "..." or null,
  "confidence": 0.0-1.0
}"""


def _format_context(context: ShellContext) -> str:
    """Format shell context as a concise string for the LLM."""
    lines = [
        f"OS: {context.os}",
        f"Shell: {context.shell}",
        f"CWD: {context.cwd}",
        f"User: {context.user}",
    ]
    if context.cwd_listing:
        listing = ", ".join(context.cwd_listing[:30])
        lines.append(f"Files in CWD: {listing}")
    if context.path_tools:
        lines.append(f"Available tools: {', '.join(context.path_tools)}")
    if context.env_hints:
        hints = ", ".join(f"{k}={v}" for k, v in context.env_hints.items())
        lines.append(f"Environment: {hints}")
    if context.git_branch:
        lines.append(f"Git branch: {context.git_branch}")
    return "\n".join(lines)


def build_prompt(query: str, context: ShellContext) -> list[dict[str, str]]:
    """Build the message list for the OpenAI API call."""
    context_str = _format_context(context)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Shell context:\n{context_str}\n\nInstruction: {query}",
        },
    ]
