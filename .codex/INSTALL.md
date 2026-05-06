# fitbit-export — Codex Installation

## Install from registry

Open `/plugins` in Codex, search for **fitbit-export**, and install it.

## Install from GitHub

Register the repo as a marketplace source:

```bash
codex plugin marketplace add mountainash-io/fitbit-export
```

Then open `/plugins` in Codex and install `fitbit-export`.

## Install from local clone

```bash
codex plugin marketplace add /path/to/fitbit-export
```

Then open `/plugins` in Codex and install `fitbit-export`.

## Verify

Start a new Codex session and check one of:

- `/plugins` shows `fitbit-export` as installed
- `~/.codex/config.toml` contains both the marketplace entry and the enabled plugin entry
- the `/fitbit-export` skill resolves in a fresh session
