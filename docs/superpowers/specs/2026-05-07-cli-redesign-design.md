# CLI Redesign: Typer + Rich Dashboard

## Problem

Running `fitbit-export` with no arguments immediately starts exporting all users with no confirmation, no status overview, and plain print() output. Users have no way to see what's been exported, what's remaining, or choose what to do next without memorizing CLI flags.

## Solution

Replace argparse with Typer and plain print with Rich. The bare command shows a dashboard with export status per user, then offers actions. Subcommands allow direct access for scripting and automation.

## Command Structure

```
fitbit-export                        # Dashboard → action menu
fitbit-export export                 # Run extraction (all users, all types)
fitbit-export export --user ID       # Export specific user
fitbit-export export --types sleep,hrv  # Export specific types
fitbit-export export --start DATE    # Start date (default: 2010-01-01)
fitbit-export export --end DATE      # End date (default: today)
fitbit-export export --output DIR    # Output directory (default: ~/fitbit-export-output)
fitbit-export add-user               # OAuth flow for new account
fitbit-export list-users             # Show authenticated accounts
fitbit-export status                 # Dashboard only (no action menu)
fitbit-export status --output DIR    # Dashboard for a specific output directory
```

The bare command is the default entry point for interactive use. Subcommands bypass the dashboard for scripting and CI.

No backwards compatibility with the old `--add-user` / `--list-users` flags. This is v0.2.0 — the old flags are removed. README, SKILL.md, and all docs update in the same commit.

## Default Paths

All persistent state lives under the home directory:

| Data | Location |
|------|----------|
| OAuth tokens | `~/.fitbit-export/tokens-{userId}.json` |
| Export output + checkpoints | `~/fitbit-export-output/{userId}-{name}/` |

In code, both resolve via `Path.home()` (not shell tilde expansion) so they work on Linux, macOS, and Windows:
- `Path.home() / ".fitbit-export"` (tokens — matches existing auth.py)
- `Path.home() / "fitbit-export-output"` (exports)

Default output changed from `./fitbit-export-output` (relative, cwd-dependent) to `~/fitbit-export-output` (fixed, global). This means:

- The dashboard always finds checkpoints regardless of where you run the command.
- Tokens and exports are both home-directory-rooted — consistent and predictable.
- `--output DIR` on `export` and `status` still overrides for custom locations.

### Dashboard discovery logic

1. **Users:** Scan `~/.fitbit-export/tokens-*.json`.
2. **Checkpoints:** Scan `{output_dir}/*/.checkpoint.json`. Output dir is `--output` if provided, otherwise `~/fitbit-export-output`.

If a user has tokens but no checkpoint at the output path, the dashboard shows "no export found" — not "pending". If `--output` points somewhere custom, the dashboard only reports what it can see there.

## Dashboard Layout

Shown on bare `fitbit-export` and `fitbit-export status`:

```
╭─ Fitbit Export ──────────────────────────────────────────╮
│ API shutdown: September 2026                             │
╰──────────────────────────────────────────────────────────╯

 Accounts
 ┌──────────┬─────────────┬──────────┬───────────────────┐
 │ User ID  │ Name        │ Progress │ Last Run          │
 ├──────────┼─────────────┼──────────┼───────────────────┤
 │ 26CBRV   │ Nathaniel   │ 10/12 ✓  │ 2026-05-06 22:30  │
 │ 7XK2QM   │ Sarah       │ 12/12 ✓  │ 2026-05-05 14:15  │
 └──────────┴─────────────┴──────────┴───────────────────┘

 26CBRV — Nathaniel (2 remaining)
 ┌──────────────────────┬──────────┬─────────────────────┐
 │ Data Type            │ Status   │ Detail              │
 ├──────────────────────┼──────────┼─────────────────────┤
 │ activities           │ ✓ done   │ 847 records         │
 │ sleep                │ ✓ done   │ 4,102 records       │
 │ heart_rate_intraday  │ partial  │ through 2024-03-15  │
 │ nutrition            │ pending  │                     │
 └──────────────────────┴──────────┴─────────────────────┘
```

### Dashboard states

- **No authenticated users:** Welcome message, skip tables, prompt to add first account.
- **All users complete:** Congratulations message, no action menu.
- **Partial exports:** Show per-type detail table for users with remaining work, then action menu.
- **Users found but no checkpoints at default path:** Show users with "unknown" status and hint to use `--output`.

### Action menu (bare command only, not `status`)

```
What would you like to do?
[1] Export all users    [2] Export 26CBRV only
[3] Add another user    [4] Quit
```

Dynamic options based on number of users and their completion state.

### Data source

Dashboard reads checkpoint files and token files only — no API calls. Fast and works offline.

## Export Progress Display

During extraction, each data type gets its own Rich progress bar:

```
Exporting Nathaniel (26CBRV)...

 spo2                ━━━━━━━━━━━━━━━━━━━━ 100%  142 records
 weight              ━━━━━━━━━━━━━━━━━━━━ 100%  389 records
 sleep               ━━━━━━━━━━━━━━━━━━━━ 100%  4,102 records
 heart_rate_intraday ━━━━━━━━━━━━━░░░░░░░  62%  2024-03-15 (ETA: ~45min)
```

### Progress states

- **Skipped** (already in checkpoint): shows `✓ done` immediately, no bar.
- **Active**: live progress bar with percentage. For day-by-day types (intraday HR), shows current date and ETA. For single-request types, goes 0→100% instantly.
- **Rate limited**: bar pauses, status shows `waiting 58s...`.
- **Error**: bar turns red with error message.
- **Complete**: bar fills, shows record count.

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = ["httpx>=0.27", "typer[all]>=0.15", "rich>=13"]
```

`typer[all]` pulls in Rich and click. Listing `rich` explicitly for clarity.

## File Changes

| File | Change |
|------|--------|
| `src/fitbit_export/cli.py` | Rewrite: Typer app with `export`, `add-user`, `list-users`, `status` subcommands. Bare invocation calls dashboard then action menu. |
| `src/fitbit_export/display.py` | New: `render_dashboard()`, `render_user_detail()`, `render_action_menu()`, `create_progress_group()`. All Rich rendering lives here. |
| `src/fitbit_export/extract.py` | Minor: emit granular progress events with `current_date` and `pct` for intraday and chunked fetches. Core fetch logic unchanged. |
| `src/fitbit_export/models.py` | Minor: no changes expected — `ProgressEvent` already has `pct` and `current_date` fields. |
| `src/fitbit_export/io.py` | Unchanged. |
| `src/fitbit_export/auth.py` | Unchanged. |
| `pyproject.toml` | Add typer, rich dependencies. Replace any pip references with uv. |
| `skills/fitbit-export/SKILL.md` | Update: new subcommand structure, Phase 4 uses `fitbit-export export` instead of bare command. Bootstrap uses `uv venv && uv pip install -e .` |
| `README.md` | Update: CLI examples use new subcommands, `pip install .` → `uv pip install .` |
| `INSTALL.md` | Update: ensure all install examples use `uv` |

## Architecture

- `cli.py` owns the Typer app and subcommand routing.
- `display.py` owns all Rich rendering. `extract.py` does not import Rich.
- `extract.py` stays a pure data layer. The `FitbitExtractor` class interface is unchanged — the `on_progress` callback bridges extract→display.
- `auth.py` and `io.py` are untouched.

## Doc Fixes (ship with this change)

- `README.md` line 59: `pip install .` → `uv pip install .`
- `README.md`: CLI examples updated to new subcommand structure
- `INSTALL.md`: already uses `uv` — verify no regressions
- `SKILL.md`: update all phases to use new subcommands
- `.gitignore`: add `fitbit-export-output/` to prevent accidental commit of health data

## Out of Scope

- No Textual TUI or interactive widgets.
- No changes to OAuth flow or Fitbit API logic.
- No new data types.
- No config file system — CLI flags are sufficient.
- No backwards compatibility shims for old `--add-user` / `--list-users` flags.
