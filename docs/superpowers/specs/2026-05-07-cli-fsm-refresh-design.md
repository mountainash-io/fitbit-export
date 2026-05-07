# CLI FSM Loop, Token Refresh, List-Users Fix

## Problem

The dashboard runs once and exits after each action. Users must re-run `fitbit-export` to see updated status or take another action. `list-users` duplicates `status` without showing progress. Token refresh has no explicit pathway — stale tokens cause raw HTTP errors.

## Solution

Three changes:

1. Bare `fitbit-export` becomes an FSM loop — dashboard → action → repeat until Quit
2. New `refresh` subcommand for explicit token refresh via browser
3. `list-users` shows export progress alongside each user

## 1. FSM Loop

### State machine

```
DASHBOARD ──► action ──► DASHBOARD (loop)
    │
    └──► QUIT (exit)
```

Every action (export, add-user, refresh, config) returns to the dashboard with freshly loaded data. The user stays in the loop until they pick Quit or press Ctrl-C twice.

### Ctrl-C handling

- **First Ctrl-C** (during an action): catches `KeyboardInterrupt`, prints "Interrupted — returning to dashboard", re-enters loop
- **Second Ctrl-C** (at dashboard/menu level): outer try/except catches it, prints "Goodbye", exits cleanly

### Implementation

The `main` callback in `cli.py` becomes:

```python
try:
    while True:
        data = gather_dashboard_data(token_dir, output_dir)
        render_dashboard(data, output_dir, token_dir)

        # Handle special states
        if not data.users:
            # offer add-user, then continue loop
        if all_complete:
            # offer add-user, then continue loop

        action = render_action_menu(data)
        if action == "quit":
            break

        try:
            execute_action(action, ...)
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted — returning to dashboard[/yellow]")
            continue

except KeyboardInterrupt:
    console.print("\n[dim]Goodbye[/dim]")
```

### Menu options (dynamic)

```
[1] Export all users          (if >1 user with incomplete)
[2] Export Nathaniel (26CBRV) (per incomplete user)
[3] Add another user
[4] Refresh tokens
[5] Change export directory
[6] Quit
```

Plus existing `h`/`help`/`?` for CLI reference and `q`/`quit` shortcut.

### Subcommands stay one-shot

All subcommands (`export`, `add-user`, `refresh`, `config`, `list-users`, `status`) run once and exit. Only bare `fitbit-export` (no subcommand) enters the FSM loop. This preserves scriptability and the escape hatch to the built-in CLI menu.

## 2. Token Refresh Subcommand

### Command

```
fitbit-export refresh              # opens browser, refreshes whichever account is logged in
fitbit-export refresh --user ID    # reminds user to log in as that account, then opens browser
```

### Flow

1. If `--user ID` provided, print: "Make sure you are logged into fitbit.com as [display_name] before continuing."
2. Otherwise, print: "This will refresh tokens for whichever Fitbit account is currently logged into your browser."
3. Open browser for OAuth (same `_run_oauth_flow` as add-user)
4. After auth, fetch profile to get authenticated user_id
5. If `--user ID` was provided and authenticated user_id != requested ID:
   - **Mismatch:** print "Expected [requested_name] ([requested_id]) but browser authenticated as [auth_name] ([auth_id]). Log out of fitbit.com and log in as the correct account." Do NOT save tokens.
6. Check if authenticated user_id matches an existing token file:
   - **Match:** overwrite tokens, print "Tokens refreshed for [name] ([id])"
   - **No match:** print warning "This account ([name]) isn't registered yet. Use `fitbit-export add-user` instead." Do NOT save tokens.

### Implementation

Add `refresh_user()` method to `FitbitAuth` class in `auth.py`. Reuses `_run_oauth_flow` and `_fetch_profile` but checks existing tokens before saving.

## 3. List-Users Progress

### Current output

```
  Nathaniel (26CBRV)
  Sarah (7XK2QM)
```

### New output

```
  Nathaniel (26CBRV)  10/12
  Sarah (7XK2QM)      12/12 ✓
```

Reads checkpoints from the output directory (same as dashboard). If no checkpoint found for a user, shows nothing after the name (no misleading "0/12").

### Implementation

`list-users` in `cli.py` calls `gather_dashboard_data` to get checkpoint info, then formats bare text lines with progress appended.

## File Changes

| File | Change |
|------|--------|
| `cli.py` | FSM loop in `main` callback; add `refresh` subcommand; update `list-users` to show progress; add refresh/config to menu action dispatch |
| `display.py` | Add "Refresh tokens" and "Change export directory" options to `render_action_menu` |
| `auth.py` | Add `refresh_user()` method |

## Out of Scope

- Auto-refresh on 401 during export (separate concern, can be added later)
- Removing `list-users` in favor of `status` (user wants bare list kept)
- Changes to the export or checkpoint logic
