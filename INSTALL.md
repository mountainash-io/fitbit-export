# Installation

How to install **fitbit-export** on each supported platform.

## Claude Code

### Install from GitHub

Register the plugin's marketplace, then install:

```bash
/plugin marketplace add mountainash-io/fitbit-export
/plugin install fitbit-export@fitbit-export-marketplace
```

### Install from local clone

```bash
claude --plugin-dir /path/to/fitbit-export
```

Or add to `.claude/settings.json` for persistent access:

```json
{
  "extraKnownMarketplaces": {
    "fitbit-export-marketplace": {
      "source": {
        "source": "github",
        "repo": "mountainash-io/fitbit-export"
      }
    }
  }
}
```

### Verify

```bash
claude plugin list
```

Look for `fitbit-export` in the output. Then invoke: `/fitbit-export`

## Cursor

### Install from registry

Search for **fitbit-export** in the Cursor marketplace panel, visit `cursor.com/marketplace`, or run in Agent chat:

```
/add-plugin fitbit-export@https://github.com/mountainash-io/fitbit-export
```

### Install from GitHub

```
/add-plugin fitbit-export@https://github.com/mountainash-io/fitbit-export
```

### Install from local clone

Symlink or copy the plugin directory and restart Cursor (Developer: Reload Window):

```bash
ln -s /path/to/fitbit-export ~/.cursor/plugins/local/fitbit-export
```

### Verify

Open Cursor and check that `fitbit-export` appears when typing `/` in chat.

## Gemini CLI

### Install from registry

Browse the gallery at [geminicli.com/extensions](https://geminicli.com/extensions/) and search for **fitbit-export**, or install directly:

```bash
gemini extensions install mountainash-io/fitbit-export
```

### Install from GitHub

```bash
gemini extensions install mountainash-io/fitbit-export
```

### Install from local clone

```bash
gemini extensions link /path/to/fitbit-export
```

Changes are reflected immediately without reinstalling.

### Verify

```bash
gemini extensions list
```

Look for `fitbit-export` in the output.

## Codex

### Install from registry

Open `/plugins` in Codex, search for **fitbit-export**, and install it.

### Install from GitHub

Register the repo as a marketplace source:

```bash
codex plugin marketplace add mountainash-io/fitbit-export
```

Then open `/plugins` in Codex and install `fitbit-export`.

### Install from local clone

```bash
codex plugin marketplace add /path/to/fitbit-export
```

Then open `/plugins` in Codex and install `fitbit-export`.

### Verify

Start a new Codex session and check one of:

- `/plugins` shows `fitbit-export` as installed
- `~/.codex/config.toml` contains both the marketplace entry and the enabled plugin entry
- the `/fitbit-export` skill resolves in a fresh session

## All Platforms: Python Setup

The skill bootstraps the Python environment automatically, but if you prefer manual setup:

```bash
cd fitbit-export
uv venv && uv pip install -e .
fitbit-export --help
```

Requires Python 3.11+ and `uv` (or `pip`).
