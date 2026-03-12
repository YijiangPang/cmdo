# ai-terminal — Function Design Document

**Version:** 0.1.0 (Design Phase)
**Author:** Yijiang
**Date:** March 2026

---

## 1. Product Overview

`ai-terminal` is a shell-level CLI tool that translates natural language instructions into shell commands, displays them with safety annotations, and optionally executes them — all from any terminal (VSCode, iTerm, Terminal.app, SSH, tmux, etc.).

---

## 2. User Flow Summary

```
┌──────────────────────────────────────────────────────────┐
│  First Run                                               │
│  $ ai "compress checkpoints"                             │
│  ⚠ No API key configured.                                │
│  Run `ai --config` to set up your LLM provider.          │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Normal Run (safe command)                               │
│  $ ai "compress checkpoints folder to checkpoints.tar.gz"│
│                                                          │
│  🤖 Will run:                                            │
│  ┌────────────────────────────────────────────────┐      │
│  │ tar -czf checkpoints.tar.gz checkpoints/       │      │
│  └────────────────────────────────────────────────┘      │
│  📝 Compresses the "checkpoints" directory into a        │
│     gzipped tarball named "checkpoints.tar.gz".          │
│                                                          │
│  [Y] Execute  [e] Edit  [c] Copy  [n] Cancel            │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  Normal Run (dangerous command)                          │
│  $ ai "delete everything in the current directory"       │
│                                                          │
│  🤖 Will run:                                            │
│  ┌────────────────────────────────────────────────┐      │
│  │ rm -rf ./*                                     │      │
│  └────────────────────────────────────────────────┘      │
│  🔴 WARNING: DESTRUCTIVE — permanently deletes all       │
│     files and subdirectories in the current directory.    │
│     This action is IRREVERSIBLE.                         │
│                                                          │
│  Type "yes" to confirm, or [n] to cancel:                │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Function Design

### 3.0 Entry Point

**`main(args: list[str]) → int`**

The top-level entry point. Parses CLI arguments, routes to the correct sub-function, and returns an exit code.

| Input | Behavior |
|-------|----------|
| `ai "compress checkpoints folder"` | → `run_query(query)` |
| `ai --config` | → `configure()` |
| `ai --config --show` | → `show_config()` |
| `ai --config --reset` | → `reset_config()` |
| `ai --history` | → `show_history(n=20)` |
| `ai --history clear` | → `clear_history()` |
| `ai --help` | → `show_help()` |
| `ai --version` | → print version |
| `ai` (no arguments) | → enter interactive/chat mode |
| `ai --dry-run "..."` | → generate + display command, skip execution |
| `ai --yes "..."` | → auto-confirm safe commands (still block dangerous) |
| `ai --model gpt-4o "..."` | → override default model for this query |
| `ai --explain "tar -czf ..."` | → `explain_command(cmd)` (reverse mode) |

**Returns:** `0` on success, `1` on user cancel, `2` on error.

---

### 3.1 Configuration Management

#### 3.1.1 `check_config() → Config | None`

Checks whether a valid configuration exists.

- **Config file location:** `~/.config/ai-terminal/config.toml`
- **Returns:** parsed `Config` object if valid, `None` otherwise
- **Config schema:**
  ```toml
  [llm]
  provider = "openai"          # openai | anthropic | local | custom
  api_key = "sk-..."           # encrypted at rest
  model = "gpt-4o"             # default model
  base_url = ""                # optional, for custom/local endpoints

  [behavior]
  auto_confirm_safe = false    # skip confirmation for safe commands
  danger_confirmation = "type" # "type" (type yes) | "double" (press Y twice)
  history_enabled = true
  max_history = 500

  [display]
  color = true
  explanation = true           # show natural language explanation
  language = "en"              # future: multi-language explanations
  ```

#### 3.1.2 `configure() → Config`

Interactive first-time setup wizard OR reconfiguration.

**Flow:**
```
$ ai --config

🔧 ai-terminal setup

1. Choose your LLM provider:
   [1] OpenAI (GPT-4o, GPT-4o-mini)
   [2] Anthropic (Claude Sonnet, Claude Haiku)
   [3] Local (Ollama, LM Studio)
   [4] Custom endpoint

> 1

2. Enter your OpenAI API key:
   (Get one at https://platform.openai.com/api-keys)
> sk-xxxxxxxxxxxxxxxx

3. Choose default model:
   [1] gpt-4o        (best quality, slower)
   [2] gpt-4o-mini   (fast, cheaper)
> 2

4. Auto-confirm safe commands? (skip [Y/n] for non-destructive commands)
   [y/N]
> n

✅ Configuration saved to ~/.config/ai-terminal/config.toml
   Run `ai "list all python files"` to try it out!
```

- **Validates API key** by making a lightweight test call (e.g., "respond with OK")
- **Encrypts API key** at rest using OS keychain (macOS Keychain, Linux secret-service) with fallback to file-based encryption
- **Creates config directory** if it doesn't exist

#### 3.1.3 `show_config() → None`

Prints current config with the API key masked (`sk-...xxxx`).

#### 3.1.4 `reset_config() → None`

Deletes config file after user confirmation. Next invocation triggers setup.

#### 3.1.5 `ensure_configured() → Config`

Called at the start of every query. If `check_config()` returns `None`:
```
⚠ ai-terminal is not configured yet.
Run `ai --config` to set up your LLM provider and API key.
```
Exits with code `2`.

---

### 3.2 Context Gathering

#### 3.2.1 `gather_context() → ShellContext`

Collects environmental context to help the LLM generate accurate commands.

**Returns `ShellContext`:**
```python
@dataclass
class ShellContext:
    os: str                  # "macOS 15.3" | "Ubuntu 24.04" | ...
    shell: str               # "zsh 5.9" | "bash 5.2" | ...
    cwd: str                 # "/Users/yijiang/projects/ml-exp"
    cwd_listing: list[str]   # top-level files/dirs (first 50, truncated)
    user: str                # "yijiang"
    path_tools: list[str]    # available tools: ["tar", "gzip", "docker", ...]
    env_hints: dict          # CONDA_DEFAULT_ENV, VIRTUAL_ENV, etc.
    git_branch: str | None   # current git branch if in a repo
    recent_commands: list[str]  # last 5 shell history entries (opt-in)
```

**Design notes:**
- `cwd_listing` helps the LLM resolve ambiguous names (e.g., is "checkpoints" a file or folder?)
- `path_tools` is gathered by checking common tool names via `which` — cached for the session
- `env_hints` captures active conda/venv environment so the LLM knows the Python context
- `recent_commands` is opt-in (config flag) for continuity ("do the same but for the other folder")
- Total context is kept under ~800 tokens to minimize latency and cost

#### 3.2.2 `detect_tools(names: list[str]) → list[str]`

Checks which CLI tools are installed. Used by `gather_context()` to tell the LLM what's available (e.g., don't suggest `pigz` if only `gzip` is installed).

---

### 3.3 Command Generation (Core LLM Pipeline)

#### 3.3.1 `generate_command(query: str, context: ShellContext, config: Config) → CommandResult`

The core function. Sends the natural language query + context to the LLM and returns a structured result.

**Returns `CommandResult`:**
```python
@dataclass
class CommandResult:
    command: str             # the shell command(s) to execute
    explanation: str         # plain-English description of what it does
    risk_level: RiskLevel    # SAFE | CAUTION | DANGEROUS
    risk_reason: str | None  # why it's flagged (if CAUTION or DANGEROUS)
    alternatives: list[str]  # optional safer alternatives
    is_multi_step: bool      # True if command uses && or ; or is a script
    estimated_duration: str | None  # "instant" | "~5s" | "~2min" | None
    confidence: float        # 0.0–1.0, LLM's confidence in the command
```

**System prompt structure (sent to LLM):**

```
You are a shell command generator. Given a natural language instruction
and shell context, produce the exact command(s) to execute.

Rules:
1. Output ONLY valid shell commands for the user's OS and shell.
2. Prefer simple, standard tools over obscure ones.
3. Use tools confirmed available in the context. If the best tool
   is unavailable, use a fallback AND note it.
4. Never generate commands that require interactive input (use flags
   to avoid prompts, e.g., `rm -f` not `rm -i` when deletion is intended).
5. For file operations, use the cwd_listing to resolve ambiguous names.
6. Classify risk level:
   - SAFE: read-only, create files, list, search, compress
   - CAUTION: modify files, install packages, change permissions
   - DANGEROUS: delete files, format disks, overwrite data, sudo operations,
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
}
```

**Error handling:**
- Network timeout → retry once, then show error with suggestion to check connection
- Invalid JSON from LLM → retry with stricter prompt, then fallback to raw text parsing
- Low confidence (<0.5) → show warning: "⚠ Low confidence. Please review carefully."
- API rate limit → show wait time, offer to retry

#### 3.3.2 `build_prompt(query: str, context: ShellContext) → list[Message]`

Constructs the message array for the LLM API call. Handles:
- System prompt (rules, output format)
- Context injection (OS, shell, cwd, available tools)
- The user query
- Optional: last N commands from history for continuity

---

### 3.4 Risk Classification & Safety

#### 3.4.1 `classify_risk(command: str) → RiskLevel`

**Local (non-LLM) safety check** that runs as a second pass after the LLM's own classification. This catches cases where the LLM under-classifies risk.

**`RiskLevel` enum:**
```python
class RiskLevel(Enum):
    SAFE = "safe"           # green — read-only, non-destructive
    CAUTION = "caution"     # yellow — modifies state but recoverable
    DANGEROUS = "dangerous" # red — destructive, irreversible, or privileged
```

**Classification rules (local pattern matching):**

| Risk Level | Patterns |
|------------|----------|
| **DANGEROUS** | `rm -rf`, `rm -r`, `mkfs`, `dd if=`, `> /dev/`, `:(){ :\|:& };:`, `chmod -R 777`, `DROP TABLE`, `DROP DATABASE`, `--force` + delete variants, `sudo rm`, `shutdown`, `reboot`, any pipe to `sh`/`bash` from `curl`/`wget`, `format`, `fdisk`, `:> file` (file truncation) |
| **CAUTION** | `sudo *` (not covered above), `mv` (overwrite risk), `chmod`, `chown`, `pip install`, `npm install -g`, `brew install`, `apt install`, `git push --force`, `git reset --hard`, `sed -i` (in-place edit), `docker rm`, `kill`, `pkill`, writing to system paths (`/etc/`, `/usr/`) |
| **SAFE** | `ls`, `cat`, `grep`, `find`, `echo`, `pwd`, `tar` (create), `cp`, `mkdir`, `head`, `tail`, `wc`, `diff`, `git status`, `git log`, `docker ps`, `pip list`, read-only commands |

**Behavior:**
- If local classification is HIGHER risk than LLM's → **upgrade** to local classification
- If local classification is LOWER risk than LLM's → keep LLM's (trust the cautious side)
- This is a safety net, not a replacement for LLM classification

#### 3.4.2 `check_forbidden(command: str) → ForbiddenResult | None`

Hard-blocks commands that should never be executed via a natural language interface, regardless of user confirmation.

**Forbidden patterns:**
- Fork bombs: `:(){ :|:& };:`
- Disk wipe: `dd if=/dev/zero of=/dev/sda`, `dd if=/dev/urandom of=/dev/sda`
- Full system delete: `rm -rf /`, `rm -rf /*`
- Curl-pipe-bash from untrusted: `curl ... | sudo bash` (warn but allow if user insists for known installers)

**Returns:** error message if forbidden, `None` if allowed.

---

### 3.5 Display & User Interaction

#### 3.5.1 `display_command(result: CommandResult) → None`

Renders the command result to the terminal with color-coded formatting.

**Display layout by risk level:**

**SAFE (green):**
```
🤖 Will run:
┌──────────────────────────────────────┐
│ tar -czf checkpoints.tar.gz checkpoints/
└──────────────────────────────────────┘
📝 Compresses the "checkpoints" directory into a gzipped tarball.

[Y] Execute  [e] Edit  [c] Copy  [n] Cancel
```

**CAUTION (yellow):**
```
🤖 Will run:
┌──────────────────────────────────────┐
│ sudo apt install ffmpeg
└──────────────────────────────────────┘
🟡 CAUTION: Installs a system package. Requires sudo privileges.

📝 Installs FFmpeg, a multimedia processing tool, via apt.

[Y] Execute  [e] Edit  [c] Copy  [n] Cancel
```

**DANGEROUS (red):**
```
🤖 Will run:
┌──────────────────────────────────────┐
│ rm -rf ./*
└──────────────────────────────────────┘
🔴 WARNING: DESTRUCTIVE — permanently deletes all files and
   subdirectories in the current directory.
   This action is IRREVERSIBLE.

💡 Safer alternative:
   mv ./* ~/.Trash/   (move to trash instead)

Type "yes" to confirm, or [n] to cancel:
```

**Multi-step commands:**
```
🤖 Will run (3 steps):
┌──────────────────────────────────────┐
│ Step 1: mkdir -p output/
│ Step 2: ffmpeg -i video.mp4 -vn audio.mp3
│ Step 3: echo "Done! Audio saved to output/audio.mp3"
└──────────────────────────────────────┘
📝 Creates an output directory, extracts audio from video.mp4
   as an MP3 file.

[Y] Execute all  [s] Step-by-step  [e] Edit  [c] Copy  [n] Cancel
```

#### 3.5.2 `prompt_user(risk: RiskLevel) → UserAction`

Prompts for confirmation. Behavior varies by risk level.

**`UserAction` enum:**
```python
class UserAction(Enum):
    EXECUTE = "execute"        # run the command
    EXECUTE_STEPWISE = "step"  # run multi-step one at a time
    EDIT = "edit"              # open command in $EDITOR or inline edit
    COPY = "copy"              # copy to clipboard
    CANCEL = "cancel"          # abort
    EXPLAIN_MORE = "explain"   # ask LLM to explain in more detail
```

**Confirmation requirements by risk level:**

| Risk Level | Confirmation Type | Auto-confirm (`--yes` flag) |
|------------|-------------------|-----------------------------|
| SAFE | Single keypress `Y` | ✅ Allowed |
| CAUTION | Single keypress `Y` | ✅ Allowed |
| DANGEROUS | Type full word `"yes"` | ❌ Never auto-confirmed |

#### 3.5.3 `edit_command(command: str) → str`

Opens the generated command for inline editing or in `$EDITOR`.
- Inline mode: pre-fills the command in an editable prompt (using `readline`)
- Editor mode: writes to temp file, opens in `$EDITOR`, reads back

---

### 3.6 Command Execution

#### 3.6.1 `execute_command(command: str, stepwise: bool = False) → ExecutionResult`

Runs the confirmed command in the user's shell.

**Returns `ExecutionResult`:**
```python
@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration: float         # seconds
    was_interrupted: bool   # user pressed Ctrl+C
```

**Execution strategy:**
- Spawns a subprocess using `subprocess.Popen` with the user's default shell
- Inherits the current environment (so conda, venv, PATH all work)
- Streams stdout/stderr in real-time (not buffered)
- Captures exit code
- Handles `Ctrl+C` gracefully: sends SIGINT to child process, reports interrupted state
- Timeout: no default timeout (long-running commands are valid), but Ctrl+C always works

**Stepwise mode (`stepwise=True`):**
- Splits multi-step commands on `&&` / `;` boundaries
- Runs each step, shows output, asks before continuing
- If any step fails, stops and shows error

#### 3.6.2 `handle_execution_error(result: ExecutionResult, original_query: str) → None`

If a command fails (non-zero exit code), offers intelligent recovery:

```
❌ Command failed (exit code 1):
   tar: checkpoints: Cannot stat: No such file or directory

🤖 It looks like there's no "checkpoints" directory here.
   Current directory contains: [model/, data/, train.py, README.md]

   Did you mean?
   [1] tar -czf checkpoints.tar.gz model/   (compress "model/" instead)
   [2] Retry with a different description
   [n] Cancel
```

- Sends the error output back to the LLM with the original query
- LLM suggests a fix or alternative
- User can accept the fix or cancel

---

### 3.7 History & Logging

#### 3.7.1 `log_entry(query: str, result: CommandResult, execution: ExecutionResult | None) → None`

Appends to `~/.config/ai-terminal/history.jsonl`:

```json
{
  "timestamp": "2026-03-12T14:22:05Z",
  "query": "compress checkpoints folder to checkpoints.tar.gz",
  "command": "tar -czf checkpoints.tar.gz checkpoints/",
  "risk_level": "safe",
  "action_taken": "executed",
  "exit_code": 0,
  "duration_ms": 1230,
  "cwd": "/Users/yijiang/projects/ml-exp",
  "model": "gpt-4o-mini"
}
```

#### 3.7.2 `show_history(n: int = 20, filter: str | None = None) → None`

```
$ ai --history
Recent commands:
  [1]  12 Mar 14:22  ✅  tar -czf checkpoints.tar.gz checkpoints/
  [2]  12 Mar 14:18  ✅  find . -name "*.py" -exec wc -l {} +
  [3]  12 Mar 14:05  ❌  docker compose up -d  (exit code 1)
  [4]  12 Mar 13:50  🚫  rm -rf ./data  (cancelled by user)

$ ai --history --filter "docker"
  [3]  12 Mar 14:05  ❌  docker compose up -d  (exit code 1)
```

#### 3.7.3 `rerun_from_history(index: int) → None`

`ai --rerun 1` → re-displays and re-confirms command #1 from history.

#### 3.7.4 `clear_history() → None`

Deletes the history file after confirmation.

---

### 3.8 Reverse Mode (Explain Command)

#### 3.8.1 `explain_command(command: str) → None`

The inverse function: given a command, explain what it does.

```
$ ai --explain "find . -name '*.py' -mtime -7 -exec grep -l 'import torch' {} +"

📖 This command:
  1. Searches the current directory recursively for Python files
  2. Filters to files modified in the last 7 days
  3. Searches those files for the text "import torch"
  4. Prints the filenames of matching files

Components:
  find .              → search from current directory
  -name '*.py'        → only .py files
  -mtime -7           → modified within 7 days
  -exec grep -l ... + → run grep on matches, print filenames
```

---

### 3.9 Interactive Mode

#### 3.9.1 `interactive_mode() → None`

When invoked with no arguments (`$ ai`), enters a REPL-like mode for multi-turn conversation:

```
$ ai

🤖 ai-terminal interactive mode. Type your request or "exit" to quit.

> compress the checkpoints folder
🤖 Will run:
┌────────────────────────────────────────┐
│ tar -czf checkpoints.tar.gz checkpoints/
└────────────────────────────────────────┘
📝 Compresses "checkpoints" into a gzipped tarball.
[Y/e/c/n] > y
✅ Done (1.2s)

> now upload it to s3
🤖 Will run:
┌────────────────────────────────────────┐
│ aws s3 cp checkpoints.tar.gz s3://my-bucket/checkpoints.tar.gz
└────────────────────────────────────────┘
📝 Uploads the tarball to your S3 bucket.
[Y/e/c/n] > n

> exit
```

**Key feature:** The LLM receives the last N turns of conversation, so "now upload **it**" correctly resolves to the file from the previous command.

---

### 3.10 Clipboard Integration

#### 3.10.1 `copy_to_clipboard(command: str) → bool`

Copies the generated command to the system clipboard.
- macOS: `pbcopy`
- Linux: `xclip` or `xsel` (with fallback detection)
- WSL: `clip.exe`

Displays: `📋 Copied to clipboard!`

---

### 3.11 Utility Functions

#### 3.11.1 `show_help() → None`

Prints usage information with examples:
```
ai-terminal v0.1.0 — Natural language to shell commands

Usage:
  ai "your instruction"          Translate and run a command
  ai                             Interactive mode
  ai --explain "command"         Explain an existing command
  ai --config                    Set up or reconfigure
  ai --history                   View command history
  ai --dry-run "instruction"     Generate without executing
  ai --yes "instruction"         Auto-confirm safe commands
  ai --model <name> "..."        Override model for one query

Examples:
  ai "find all Python files larger than 1MB"
  ai "start a local HTTP server on port 8080"
  ai "show GPU memory usage"
  ai --explain "awk '{print $2}' file.txt"

Flags:
  --dry-run, -d     Show command without executing
  --yes, -y         Auto-confirm (safe commands only)
  --model, -m       Override default model
  --verbose, -v     Show full LLM request/response for debugging
  --no-color        Disable colored output
  --version         Show version
  --help, -h        Show this help
```

#### 3.11.2 `check_update() → None`

Periodic background check for new versions (at most once per day). Non-blocking.
```
💡 ai-terminal v0.2.0 is available. Run `pip install --upgrade ai-terminal` to update.
```

---

## 4. Risk Classification Reference

### 4.1 Full Risk Taxonomy

| Category | SAFE Examples | CAUTION Examples | DANGEROUS Examples |
|----------|---------------|-------------------|--------------------|
| **File ops** | `ls`, `cat`, `cp`, `mkdir`, `find`, `head` | `mv` (overwrite), `sed -i`, `chmod` | `rm -rf`, `rm -r`, truncate (`>`) |
| **Archive** | `tar -czf`, `zip`, `unzip -l` | `unzip -o` (overwrite) | `tar -xf` into system dirs |
| **Package** | `pip list`, `npm ls` | `pip install`, `brew install`, `apt install` | `pip install` + `--break-system-packages` with sudo |
| **Git** | `git status/log/diff/branch` | `git push --force`, `git reset --hard` | `git clean -fdx` in home dir |
| **Docker** | `docker ps`, `docker images` | `docker rm`, `docker stop` | `docker system prune -af`, `docker rm -f $(...)` |
| **Network** | `curl` (GET), `ping`, `dig` | `wget` (downloads), `scp` | `curl ... \| bash`, expose ports with `--net=host` |
| **System** | `whoami`, `uname`, `df`, `du` | `sudo ...`, `kill PID` | `shutdown`, `reboot`, `rm -rf /`, `mkfs`, `dd` |
| **Database** | `SELECT`, read queries | `UPDATE`, `INSERT` | `DROP TABLE`, `DROP DATABASE`, `TRUNCATE` |

### 4.2 Warning Message Templates

```python
RISK_MESSAGES = {
    "delete_recursive": "Permanently deletes files/directories. This is IRREVERSIBLE.",
    "sudo_usage": "Requires elevated privileges. Review the command carefully.",
    "force_push": "Overwrites remote git history. Collaborators will be affected.",
    "pipe_to_shell": "Downloads and executes remote code. Only proceed if you trust the source.",
    "disk_write": "Writes directly to disk. Wrong target can destroy data.",
    "system_modify": "Modifies system configuration. May affect system stability.",
    "package_install": "Installs software system-wide. Check the package name is correct.",
    "database_destructive": "Destroys database data. Cannot be undone without backups.",
    "permission_change": "Changes file permissions. May affect access control.",
    "kill_process": "Terminates a running process. Unsaved work may be lost.",
}
```

---

## 5. Error Handling Strategy

| Error | User-Facing Message | Recovery |
|-------|---------------------|----------|
| No API key | "⚠ Not configured. Run `ai --config`" | Exit code 2 |
| Invalid API key | "❌ API key rejected. Run `ai --config` to update" | Exit code 2 |
| Network timeout | "⏱ Request timed out. Check your connection." | Retry once |
| LLM rate limit | "⏳ Rate limited. Retrying in {n}s..." | Auto-retry with backoff |
| LLM returns invalid JSON | (silent retry with stricter prompt) | Retry once, then raw parse |
| Command not found | "❌ `pigz` is not installed. Suggesting alternative..." | LLM re-generates with constraint |
| Execution fails | "❌ Command failed. Want me to diagnose?" | Send error to LLM for fix |
| Ambiguous query | "🤔 Did you mean: [1] ... [2] ...?" | Show options |
| Low confidence | "⚠ Low confidence (45%). Please review carefully." | Still show, flag visually |
| Forbidden command | "🚫 This command is blocked for safety." | Hard block, no override |

---

## 6. Module / File Structure

```
ai-terminal/
├── pyproject.toml               # package config, dependencies, entry point
├── README.md
├── LICENSE
├── src/
│   └── ai_terminal/
│       ├── __init__.py
│       ├── cli.py               # main(), argument parsing (3.0)
│       ├── config.py            # check/configure/show/reset config (3.1)
│       ├── context.py           # gather_context, detect_tools (3.2)
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py        # LLM API client, provider abstraction (3.3)
│       │   ├── prompt.py        # build_prompt, system prompts (3.3.2)
│       │   └── parser.py        # parse LLM JSON response
│       ├── safety/
│       │   ├── __init__.py
│       │   ├── classifier.py    # classify_risk, local pattern matching (3.4.1)
│       │   └── forbidden.py     # check_forbidden, hard blocks (3.4.2)
│       ├── display.py           # display_command, color formatting (3.5)
│       ├── executor.py          # execute_command, error recovery (3.6)
│       ├── history.py           # log, show, rerun, clear (3.7)
│       ├── explain.py           # explain_command reverse mode (3.8)
│       ├── interactive.py       # interactive REPL mode (3.9)
│       ├── clipboard.py         # copy_to_clipboard (3.10)
│       └── utils.py             # show_help, check_update (3.11)
└── tests/
    ├── test_classifier.py       # risk classification unit tests
    ├── test_forbidden.py        # forbidden command tests
    ├── test_context.py          # context gathering tests
    ├── test_display.py          # display formatting tests
    └── test_integration.py      # end-to-end with mock LLM
```

---

## 7. Dependencies

| Package | Purpose |
|---------|---------|
| `click` or `typer` | CLI argument parsing |
| `rich` | Terminal colors, boxes, tables |
| `openai` | OpenAI API client |
| `anthropic` | Anthropic API client |
| `keyring` | OS keychain for API key encryption |
| `prompt_toolkit` | Interactive mode, inline editing, readline |
| `tomli` / `tomllib` | Config file parsing |
| `httpx` | HTTP client (alternative to provider SDKs) |

---

## 8. Future Extensions (Out of Scope for v0.1)

- **Shell integration (v0.2):** Deeper integration via zsh/bash plugin so user can type natural language directly with a prefix key (e.g., `Ctrl+K` to activate)
- **Pipe support (v0.2):** `cat errors.log | ai "summarize these errors"`
- **Multi-command workflows (v0.3):** `ai "set up a new Python project with venv, git, and pre-commit"`
- **Custom aliases (v0.3):** `ai --alias deploy="build, test, push to main, deploy to production"`
- **Team sharing (v1.0):** Shared command library / approved commands for org use
- **Usage analytics dashboard (v1.0):** Track cost, tokens used, most common queries
- **Plugin system (v1.0):** Extend with custom tools (e.g., Kubernetes, Terraform plugins)
