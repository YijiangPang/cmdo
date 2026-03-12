# cmdo

**Natural language to shell commands.** Just say what you want and cmdo does it.

```
$ cmdo "compress the checkpoints folder"

🤖 Will run:
╭──────────────────────────────────────────────╮
│ tar -czf checkpoints.tar.gz checkpoints/     │
╰──────────────────────────────────────────────╯
📝 Compresses the "checkpoints" directory into a gzipped tarball.

[Y] Execute  [e] Edit  [c] Copy  [n] Cancel
```

## Features

- **Translates natural language** into accurate shell commands using GPT
- **Safety-first**: commands are classified as Safe / Caution / Dangerous with color-coded warnings
- **Hard-blocks** catastrophic commands (fork bombs, `rm -rf /`, disk wipes)
- **Context-aware**: knows your OS, shell, current directory, installed tools, and git branch
- **Works everywhere**: any terminal — iTerm, VSCode, Terminal.app, SSH, tmux

## Install

```bash
pip install cmdo
```

Requires Python 3.10+.

## Quick Start

```bash
# First-time setup — enter your OpenAI API key
cmdo --config

# Use it
cmdo "find all Python files larger than 1MB"
cmdo "start a local HTTP server on port 8080"
cmdo "show disk usage sorted by size"

# Generate without executing
cmdo --dry-run "delete the temp folder"

# Auto-confirm safe commands
cmdo --yes "list all docker containers"
```

## Safety

Every generated command goes through two layers of safety checking:

1. **LLM classification** — the model labels each command as SAFE, CAUTION, or DANGEROUS
2. **Local pattern matching** — a regex-based classifier catches anything the LLM misses

| Risk Level | Confirmation | Auto-confirm (`--yes`) |
|---|---|---|
| **SAFE** (green) | Single keypress `Y` | Allowed |
| **CAUTION** (yellow) | Single keypress `Y` | Allowed |
| **DANGEROUS** (red) | Type full word `yes` | Never |

Certain commands are **hard-blocked** and can never be executed:
- Fork bombs
- Full disk wipes (`dd if=/dev/zero of=/dev/sda`)
- System-wide deletion (`rm -rf /`)

## Configuration

```bash
cmdo --config           # Interactive setup wizard
cmdo --config --show    # View current config (API key masked)
cmdo --config --reset   # Reset to defaults
```

Config is stored in `~/.config/cmdo/config.toml`.

## CLI Reference

```
Usage: cmdo [OPTIONS] [QUERY]...

Options:
  --config          Configure cmdo
  --show            Show current configuration (use with --config)
  --reset           Reset configuration (use with --config)
  -d, --dry-run     Generate command without executing
  -y, --yes         Auto-confirm safe commands
  -m, --model TEXT  Override default model for one query
  -V, --version     Show version
  --help            Show help
```

## License

MIT
