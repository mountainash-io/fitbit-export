# fitbit-export — Codex Installation

## Plugin install (recommended)

```bash
git clone https://github.com/mountainash-io/fitbit-export.git ~/fitbit-export
mkdir -p ~/.agents/plugins
ln -s ~/fitbit-export ~/.agents/plugins/fitbit-export
```

Codex discovers the plugin via `.codex-plugin/plugin.json` and exposes the `fitbit-export` skill.

## Skill-only install (alternative)

If you only want the skill without plugin metadata:

```bash
git clone https://github.com/mountainash-io/fitbit-export.git ~/fitbit-export
mkdir -p ~/.agents/skills
ln -s ~/fitbit-export/skills/fitbit-export ~/.agents/skills/fitbit-export
```

## Tool mapping

The skill references Claude Code tool names. Codex equivalents:

| Skill references | Codex equivalent |
|-----------------|------------------|
| `Bash(command)` | `shell(command)` |
| `Read(path)` | `read_file(path)` |
| `AskUserQuestion(...)` | Ask the user directly in conversation |

## Verify

After installation, restart Codex and confirm:

```
> What skills do you have for Fitbit?
```

## Quick Reference

- **Language:** Python 3.11+
- **Dependencies:** httpx only (install with `uv pip install -e ~/fitbit-export`)
- **Auth:** OAuth2 + PKCE, opens browser for Fitbit login
- **Output:** `fitbit-export-output/{userId}-{name}/raw/`
