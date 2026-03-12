"""Shell context gathering for cmdo."""

from __future__ import annotations

import os
import platform
import subprocess

from cmdo.models import ShellContext

COMMON_TOOLS = [
    "tar", "gzip", "zip", "unzip", "pigz",
    "docker", "docker-compose",
    "git", "gh",
    "python", "python3", "pip", "pip3",
    "node", "npm", "npx",
    "ffmpeg", "convert", "jq",
    "curl", "wget", "httpie",
    "rsync", "scp", "ssh",
    "awk", "sed", "grep",
    "kubectl", "terraform",
]


def _run(cmd: str, timeout: float = 2.0) -> str:
    """Run a shell command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def detect_tools(names: list[str] | None = None) -> list[str]:
    """Check which CLI tools are installed."""
    if names is None:
        names = COMMON_TOOLS
    available = []
    for name in names:
        if _run(f"which {name}"):
            available.append(name)
    return available


def gather_context() -> ShellContext:
    """Collect environmental context for the LLM prompt."""
    # OS info
    system = platform.system()
    if system == "Darwin":
        os_info = f"macOS {platform.mac_ver()[0]}"
    elif system == "Linux":
        os_info = _run("cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2") or f"Linux {platform.release()}"
    else:
        os_info = f"{system} {platform.release()}"

    # Shell
    shell = os.environ.get("SHELL", "")
    shell_name = os.path.basename(shell) if shell else "unknown"
    shell_version = _run(f"{shell} --version 2>&1 | head -1") if shell else ""
    shell_info = f"{shell_name} {shell_version}".strip() if shell_version else shell_name

    # CWD listing (first 50 entries)
    cwd = os.getcwd()
    try:
        entries = sorted(os.listdir(cwd))[:50]
    except OSError:
        entries = []

    # Git branch
    git_branch = _run("git rev-parse --abbrev-ref HEAD 2>/dev/null") or None

    # Environment hints
    env_hints: dict[str, str] = {}
    for key in ("CONDA_DEFAULT_ENV", "VIRTUAL_ENV", "PYENV_VERSION", "NVM_DIR"):
        val = os.environ.get(key)
        if val:
            env_hints[key] = val

    # Available tools
    path_tools = detect_tools()

    return ShellContext(
        os=os_info,
        shell=shell_info,
        cwd=cwd,
        cwd_listing=entries,
        user=os.environ.get("USER", "unknown"),
        path_tools=path_tools,
        env_hints=env_hints,
        git_branch=git_branch,
    )
