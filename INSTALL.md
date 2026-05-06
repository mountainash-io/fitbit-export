# fitbit-export — Platform Installation Guide

## Claude Code (reference platform)

```bash
# Install as a Claude Code plugin
claude plugin add /path/to/fitbit-export
# Or from GitHub:
claude plugin add https://github.com/mountainash-io/fitbit-export
```

Then invoke: `/fitbit-export`

**Plugin manifest:** `plugin.json` (root) + `.claude-plugin/plugin.json` (metadata)

## Cursor

1. Clone the repo:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git
   ```

2. Open the cloned directory as a Cursor workspace (or add it to your existing workspace).

3. Cursor discovers the plugin via `.cursor-plugin/plugin.json` and loads context from `.github/copilot-instructions.md`.

4. Ask the agent: *"Run the fitbit-export skill to export my Fitbit data"*

**Plugin manifest:** `.cursor-plugin/plugin.json` + `.cursor-plugin/marketplace.json`

## Gemini CLI

1. Clone the repo:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git
   ```

2. From within the cloned directory, Gemini CLI discovers the extension via `gemini-extension.json` and reads `GEMINI.md` for context and tool mapping.

3. Reference the skill:
   ```
   > @skills/fitbit-export/SKILL.md Export my Fitbit data
   ```

4. Or ask directly: *"Follow the fitbit-export skill to export my data"*

**Extension manifest:** `gemini-extension.json`

## Codex

1. Clone the repo:
   ```bash
   git clone https://github.com/mountainash-io/fitbit-export.git ~/fitbit-export
   ```

2. Register as a Codex plugin:
   ```bash
   mkdir -p ~/.agents/plugins
   ln -s ~/fitbit-export ~/.agents/plugins/fitbit-export
   ```

   Or for skill-only discovery:
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/fitbit-export/skills/fitbit-export ~/.agents/skills/fitbit-export
   ```

3. Restart Codex, then ask: *"Use the fitbit-export skill"*

**Plugin manifest:** `.codex-plugin/plugin.json`

## All Platforms: Python Setup

The skill bootstraps the Python environment automatically, but if you prefer manual setup:

```bash
cd fitbit-export
uv venv && uv pip install -e .
fitbit-export --help
```

Requires Python 3.11+ and `uv` (or `pip`).
