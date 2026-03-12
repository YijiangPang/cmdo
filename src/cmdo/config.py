"""Configuration management for cmdo."""

from __future__ import annotations

import sys
from pathlib import Path

import tomli_w

from cmdo.models import Config

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

CONFIG_DIR = Path.home() / ".config" / "cmdo"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def _load_toml() -> dict | None:
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, "rb") as f:
        return tomllib.load(f)


def _save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "llm": {
            "provider": config.provider,
            "api_key": config.api_key,
            "model": config.model,
            "base_url": config.base_url,
        },
        "behavior": {
            "auto_confirm_safe": config.auto_confirm_safe,
            "danger_confirmation": config.danger_confirmation,
        },
        "display": {
            "color": config.color,
            "explanation": config.explanation,
        },
    }
    with open(CONFIG_FILE, "wb") as f:
        tomli_w.dump(data, f)


def check_config() -> Config | None:
    """Load and return Config if valid, else None."""
    data = _load_toml()
    if data is None:
        return None
    try:
        llm = data.get("llm", {})
        behavior = data.get("behavior", {})
        display = data.get("display", {})
        config = Config(
            provider=llm.get("provider", "openai"),
            api_key=llm.get("api_key", ""),
            model=llm.get("model", "gpt-5-mini"),
            base_url=llm.get("base_url", ""),
            auto_confirm_safe=behavior.get("auto_confirm_safe", False),
            danger_confirmation=behavior.get("danger_confirmation", "type"),
            color=display.get("color", True),
            explanation=display.get("explanation", True),
        )
        if not config.api_key:
            return None
        return config
    except (KeyError, TypeError):
        return None


def configure() -> Config:
    """Interactive setup wizard."""
    from rich.console import Console

    console = Console()
    console.print("\n[bold]🔧 cmdo setup[/bold]\n")

    # Provider (OpenAI only for MVP)
    console.print("1. Choose your LLM provider:")
    console.print("   [1] OpenAI (GPT-5.4, GPT-5-mini)")
    console.print()
    choice = input("   > ").strip()
    if choice not in ("", "1"):
        console.print("[yellow]Only OpenAI is supported in this version.[/yellow]")
    provider = "openai"

    # API key
    console.print("\n2. Enter your OpenAI API key:")
    console.print("   [dim](Get one at https://platform.openai.com/api-keys)[/dim]")
    api_key = input("   > ").strip()
    if not api_key:
        console.print("[red]API key is required.[/red]")
        sys.exit(2)

    # Validate API key
    console.print("\n   [dim]Validating API key...[/dim]", end="")
    if _validate_api_key(api_key):
        console.print(" [green]✓[/green]")
    else:
        console.print(" [red]✗[/red]")
        console.print("[red]   API key validation failed. Please check your key.[/red]")
        sys.exit(2)

    # Model
    console.print("\n3. Choose default model:")
    console.print("   [1] gpt-5.4       (best quality, slower)")
    console.print("   [2] gpt-5-mini    (fast, cheaper)")
    console.print("   [3] Custom        (enter model name)")
    model_choice = input("   > ").strip()
    if model_choice == "1":
        model = "gpt-5.4"
    elif model_choice == "3":
        model = input("   Enter model name: ").strip()
        if not model:
            console.print("[yellow]No model entered, defaulting to gpt-5-mini.[/yellow]")
            model = "gpt-5-mini"
    else:
        model = "gpt-5-mini"

    # Auto-confirm
    console.print("\n4. Auto-confirm safe commands? (skip [Y/n] for non-destructive)")
    auto_confirm = input("   [y/N] > ").strip().lower() == "y"

    config = Config(
        provider=provider,
        api_key=api_key,
        model=model,
        auto_confirm_safe=auto_confirm,
    )
    _save_config(config)
    console.print(f"\n[green]✅ Configuration saved to {CONFIG_FILE}[/green]")
    console.print('   Run [bold]cmdo "list all python files"[/bold] to try it out!\n')
    return config


def _validate_api_key(api_key: str) -> bool:
    """Validate API key by listing available models."""
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        client.models.list()
        return True
    except Exception:
        return False


def show_config() -> None:
    """Print current config with masked API key."""
    from rich.console import Console

    console = Console()
    config = check_config()
    if config is None:
        console.print("[yellow]No configuration found. Run `cmdo --config` to set up.[/yellow]")
        return

    masked_key = config.api_key[:7] + "..." + config.api_key[-4:] if len(config.api_key) > 11 else "****"
    console.print("\n[bold]cmdo configuration[/bold]\n")
    console.print(f"  Provider:           {config.provider}")
    console.print(f"  API Key:            {masked_key}")
    console.print(f"  Model:              {config.model}")
    console.print(f"  Auto-confirm safe:  {config.auto_confirm_safe}")
    console.print(f"  Color:              {config.color}")
    console.print(f"  Explanations:       {config.explanation}")
    console.print()


def reset_config() -> None:
    """Delete config after confirmation."""
    from rich.console import Console

    console = Console()
    if not CONFIG_FILE.exists():
        console.print("[yellow]No configuration file to reset.[/yellow]")
        return

    confirm = input("Are you sure you want to reset the configuration? [y/N] ").strip().lower()
    if confirm == "y":
        CONFIG_FILE.unlink()
        console.print("[green]Configuration reset. Run `cmdo --config` to reconfigure.[/green]")
    else:
        console.print("Cancelled.")


def ensure_configured() -> Config:
    """Return config or exit with error if not configured."""
    config = check_config()
    if config is None:
        from rich.console import Console

        console = Console()
        console.print("[yellow]⚠ cmdo is not configured yet.[/yellow]")
        console.print("Run [bold]cmdo --config[/bold] to set up your LLM provider and API key.")
        sys.exit(2)
    return config
