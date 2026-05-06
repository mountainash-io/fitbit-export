# fitbit-export — Platform Installation Guide

## Claude Code (reference platform)

```bash
# Install as a Claude Code plugin
claude plugin add /path/to/fitbit-export
# Or from GitHub:
claude plugin add https://github.com/mountainash-io/fitbit-export
```

Then invoke: `/fitbit-export`

## Cursor

1. Clone the repo into your workspace or a shared location:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git
   ```

2. Open the cloned directory as a Cursor workspace (or add it to your existing workspace).

3. Cursor will automatically pick up `.github/copilot-instructions.md` for context and `skills/fitbit-export/SKILL.md` for the export workflow.

4. Ask the agent: *"Run the fitbit-export skill to export my Fitbit data"*

## Gemini CLI

1. Clone the repo:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git
   ```

2. From within the cloned directory, Gemini CLI will read `GEMINI.md` for context and tool mapping.

3. Reference the skill:
   ```
   > @skills/fitbit-export/SKILL.md Export my Fitbit data
   ```

4. Or ask directly: *"Follow the fitbit-export skill to export my data"*

## Codex

1. Clone and symlink to skill discovery:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git ~/fitbit-export
   mkdir -p ~/.agents/skills
   ln -s ~/fitbit-export/skills/fitbit-export ~/.agents/skills/fitbit-export
   ```

2. Restart Codex, then ask: *"Use the fitbit-export skill"*

See `.codex/INSTALL.md` for detailed Codex instructions.

## All Platforms: Python Setup

The skill bootstraps the Python environment automatically, but if you prefer manual setup:

```bash
cd fitbit-export
uv venv && uv pip install -e .
fitbit-export --help
```

Requires Python 3.11+ and `uv` (or `pip`).
