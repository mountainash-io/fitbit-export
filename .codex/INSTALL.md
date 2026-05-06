# fitbit-export — Codex Installation

## Skill-based install (recommended)

Symlink the skill into your Codex skills directory:

```bash
# Clone the repo
git clone https://github.com/mountainash-io/fitbit-export.git ~/fitbit-export

# Expose to Codex skill discovery
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

After symlinking, restart Codex and confirm the skill is discoverable:

```
> What skills do you have for Fitbit?
```

The agent should recognize `fitbit-export` and be able to walk you through the export.

## Quick Reference

- **Language:** Python 3.11+
- **Dependencies:** httpx only (install with `uv pip install -e ~/fitbit-export`)
- **Auth:** OAuth2 + PKCE, opens browser for Fitbit login
- **Output:** `fitbit-export-output/{userId}-{name}/raw/`
