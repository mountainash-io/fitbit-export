# CLI FSM Loop, Token Refresh, List-Users Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make bare `fitbit-export` an FSM loop (dashboard → action → repeat), add `refresh` subcommand for token refresh, and show progress in `list-users`.

**Architecture:** The `main` callback becomes a `while True` loop with Ctrl-C handling. `render_action_menu` gains refresh/config options. `FitbitAuth` gains a `refresh_user()` method. `list-users` reads checkpoint data via `gather_dashboard_data`.

**Tech Stack:** Python 3.11+, Typer, Rich (existing deps)

---

### Task 1: Add refresh_user() to auth.py

**Files:**
- Modify: `src/fitbit_export/auth.py`
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write test for refresh_user matching existing user**

Create `tests/test_auth.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from fitbit_export.auth import FitbitAuth


def _write_token(token_dir: Path, user_id: str, display_name: str) -> None:
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / f"tokens-{user_id}.json").write_text(json.dumps({
        "user_id": user_id,
        "display_name": display_name,
        "access_token": "old-token",
        "refresh_token": "old-refresh",
        "token_expires_at": 0,
    }))


def test_refresh_user_updates_existing(tmp_path: Path) -> None:
    token_dir = tmp_path / ".fitbit-export"
    _write_token(token_dir, "ABC123", "Alice")
    auth = FitbitAuth(token_dir=token_dir)

    fake_tokens = {"access_token": "new-token", "refresh_token": "new-refresh", "token_expires_at": 9999999999}
    with patch("fitbit_export.auth._run_oauth_flow", return_value=fake_tokens), \
         patch("fitbit_export.auth._fetch_profile", return_value=("ABC123", "Alice")), \
         patch("fitbit_export.auth._make_client", return_value=MagicMock()):
        result = auth.refresh_user()

    assert result.user_id == "ABC123"
    saved = json.loads((token_dir / "tokens-ABC123.json").read_text())
    assert saved["access_token"] == "new-token"


def test_refresh_user_rejects_unregistered(tmp_path: Path) -> None:
    token_dir = tmp_path / ".fitbit-export"
    _write_token(token_dir, "ABC123", "Alice")
    auth = FitbitAuth(token_dir=token_dir)

    fake_tokens = {"access_token": "new-token", "refresh_token": "new-refresh", "token_expires_at": 9999999999}
    with patch("fitbit_export.auth._run_oauth_flow", return_value=fake_tokens), \
         patch("fitbit_export.auth._fetch_profile", return_value=("XYZ789", "Stranger")), \
         patch("fitbit_export.auth._make_client", return_value=MagicMock()):
        result = auth.refresh_user()

    assert result is None
    saved = json.loads((token_dir / "tokens-ABC123.json").read_text())
    assert saved["access_token"] == "old-token"


def test_refresh_user_rejects_user_id_mismatch(tmp_path: Path) -> None:
    token_dir = tmp_path / ".fitbit-export"
    _write_token(token_dir, "ABC123", "Alice")
    _write_token(token_dir, "DEF456", "Bob")
    auth = FitbitAuth(token_dir=token_dir)

    fake_tokens = {"access_token": "new-token", "refresh_token": "new-refresh", "token_expires_at": 9999999999}
    with patch("fitbit_export.auth._run_oauth_flow", return_value=fake_tokens), \
         patch("fitbit_export.auth._fetch_profile", return_value=("DEF456", "Bob")), \
         patch("fitbit_export.auth._make_client", return_value=MagicMock()):
        result = auth.refresh_user(expected_user_id="ABC123")

    assert result is None
    saved_alice = json.loads((token_dir / "tokens-ABC123.json").read_text())
    assert saved_alice["access_token"] == "old-token"
    saved_bob = json.loads((token_dir / "tokens-DEF456.json").read_text())
    assert saved_bob["access_token"] == "old-token"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_auth.py -v`
Expected: FAIL — `AttributeError: 'FitbitAuth' object has no attribute 'refresh_user'`

- [ ] **Step 3: Implement refresh_user()**

In `src/fitbit_export/auth.py`, add this method to the `FitbitAuth` class after `add_user()` (after line 208):

```python
    def refresh_user(self, expected_user_id: str | None = None) -> AuthenticatedUser | None:
        existing = self.list_users()
        existing_ids = {u["user_id"] for u in existing}

        if expected_user_id:
            match = next((u for u in existing if u["user_id"] == expected_user_id), None)
            if match:
                print(f"Make sure you are logged into fitbit.com as {match['display_name']} before continuing.")
            else:
                print(f"No account with ID {expected_user_id} found.")
                return None
        else:
            print("This will refresh tokens for whichever Fitbit account is logged into your browser.")
        print()

        tokens = _run_oauth_flow(self._client_id)
        client = _make_client(tokens["access_token"])
        user_id, display_name = _fetch_profile(client)

        if expected_user_id and user_id != expected_user_id:
            expected_name = next((u["display_name"] for u in existing if u["user_id"] == expected_user_id), expected_user_id)
            print(f"Expected {expected_name} ({expected_user_id}) but browser authenticated as {display_name} ({user_id}).")
            print("Log out of fitbit.com and log in as the correct account.")
            client.close()
            return None

        if user_id not in existing_ids:
            print(f"This account ({display_name}) isn't registered yet. Use `fitbit-export add-user` instead.")
            client.close()
            return None

        _save_tokens(self._token_dir, user_id, display_name, tokens)
        print(f"Tokens refreshed for {display_name} ({user_id})")
        return AuthenticatedUser(user_id=user_id, display_name=display_name, client=client)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_auth.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: all 13 tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/fitbit_export/auth.py tests/test_auth.py
git commit -m "feat: add refresh_user() with user ID mismatch guard"
```

---

### Task 2: Add refresh and config to action menu

**Files:**
- Modify: `src/fitbit_export/display.py`
- Modify: `tests/test_display.py`

- [ ] **Step 1: Update render_action_menu to include refresh and config options**

In `src/fitbit_export/display.py`, in the `render_action_menu` function, change the options list building. Currently (lines 140-151):

```python
def render_action_menu(data: DashboardData) -> str:
    options: list[tuple[str, str]] = []

    incomplete = [u for u in data.users if len(u.completed) < len(DATA_TYPES)]
    if incomplete:
        if len(data.users) > 1:
            options.append(("export-all", "Export all users"))
        for user in incomplete:
            options.append((f"export-{user.user_id}", f"Export {user.display_name} ({user.user_id})"))

    options.append(("add-user", "Add another user"))
    options.append(("quit", "Quit"))
```

Replace with:

```python
def render_action_menu(data: DashboardData) -> str:
    options: list[tuple[str, str]] = []

    incomplete = [u for u in data.users if len(u.completed) < len(DATA_TYPES)]
    if incomplete:
        if len(data.users) > 1:
            options.append(("export-all", "Export all users"))
        for user in incomplete:
            options.append((f"export-{user.user_id}", f"Export {user.display_name} ({user.user_id})"))

    options.append(("add-user", "Add another user"))
    options.append(("refresh", "Refresh tokens"))
    options.append(("config", "Change export directory"))
    options.append(("quit", "Quit"))
```

- [ ] **Step 2: Update the help text in the menu to include refresh**

In the same function, in the help block (the `if choice.lower() in ("h", "help", "?"):` branch), add after the `fitbit-export config` line:

```python
            console.print("    fitbit-export refresh        Refresh account tokens")
```

- [ ] **Step 3: Run tests to verify no regressions**

Run: `uv run pytest tests/test_display.py tests/test_cli.py -v`
Expected: all 8 tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/fitbit_export/display.py
git commit -m "feat: add refresh and config options to dashboard action menu"
```

---

### Task 3: Add refresh subcommand to cli.py

**Files:**
- Modify: `src/fitbit_export/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write test for refresh subcommand in help**

Add to `tests/test_cli.py`:

```python
def test_help_includes_refresh() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "refresh" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli.py::test_help_includes_refresh -v`
Expected: FAIL — "refresh" not in output

- [ ] **Step 3: Add refresh subcommand**

In `src/fitbit_export/cli.py`, add after the `config` command (after line 214):

```python
@app.command()
def refresh(
    user: Optional[str] = typer.Option(None, help="Refresh specific user (Fitbit ID)"),
) -> None:
    """Refresh OAuth tokens via browser re-authentication."""
    token_dir = _get_token_dir()
    auth = FitbitAuth(token_dir=token_dir)
    result = auth.refresh_user(expected_user_id=user)
    if result:
        result.client.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/cli.py tests/test_cli.py
git commit -m "feat: add refresh subcommand for token re-authentication"
```

---

### Task 4: Update list-users to show progress

**Files:**
- Modify: `src/fitbit_export/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write test for list-users with progress**

Add to `tests/test_cli.py`:

```python
import json


def _setup_user_with_checkpoint(tmp_path, monkeypatch, completed: list[str]) -> None:
    token_dir = tmp_path / ".fitbit-export"
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / "tokens-ABC123.json").write_text(json.dumps({
        "user_id": "ABC123",
        "display_name": "Alice",
        "access_token": "fake",
        "refresh_token": "fake",
    }))
    monkeypatch.setenv("FITBIT_TOKEN_DIR", str(token_dir))

    output_dir = tmp_path / "fitbit-export-output"
    user_dir = output_dir / "ABC123-alice"
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / ".checkpoint.json").write_text(json.dumps({
        "version": 1,
        "started_at": "2026-05-07T00:00:00",
        "start_date": "2010-01-01",
        "end_date": "2026-05-07",
        "completed": completed,
        "in_progress": {},
    }))
    monkeypatch.setenv("FITBIT_OUTPUT_DIR", str(output_dir))


def test_list_users_shows_progress(tmp_path, monkeypatch) -> None:
    _setup_user_with_checkpoint(tmp_path, monkeypatch, ["spo2", "weight"])
    result = runner.invoke(app, ["list-users"])
    assert result.exit_code == 0
    assert "Alice" in result.output
    assert "ABC123" in result.output
    assert "2/12" in result.output


def test_list_users_shows_complete(tmp_path, monkeypatch) -> None:
    all_types = [
        "spo2", "weight", "nutrition", "daily_summary", "activities",
        "activity_tcx", "sleep", "heart_rate_summary", "hrv",
        "breathing_rate", "skin_temperature", "heart_rate_intraday",
    ]
    _setup_user_with_checkpoint(tmp_path, monkeypatch, all_types)
    result = runner.invoke(app, ["list-users"])
    assert result.exit_code == 0
    assert "12/12" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_list_users_shows_progress -v`
Expected: FAIL — "2/12" not in output

- [ ] **Step 3: Update list_users command**

In `src/fitbit_export/cli.py`, replace the `list_users` function (lines 170-181):

```python
@app.command()
def list_users() -> None:
    """List authenticated Fitbit accounts."""
    token_dir = _get_token_dir()
    output_dir = _get_output_dir(None)
    auth = FitbitAuth(token_dir=token_dir)
    users = auth.list_users()
    if not users:
        console.print("[yellow]No authenticated users.[/yellow]")
        console.print("Run [bold]fitbit-export add-user[/bold] to connect an account.")
        return

    data = gather_dashboard_data(token_dir=token_dir, output_dir=output_dir)
    status_map = {u.user_id: u for u in data.users}
    total = len(DATA_TYPES)

    for u in users:
        user_id = u["user_id"]
        name = u["display_name"]
        st = status_map.get(user_id)
        if st and st.has_checkpoint:
            done = len(st.completed)
            check = " ✓" if done == total else ""
            console.print(f"  {name} ({user_id})  {done}/{total}{check}")
        else:
            console.print(f"  {name} ({user_id})")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/cli.py tests/test_cli.py
git commit -m "feat: show export progress in list-users output"
```

---

### Task 5: Convert main callback to FSM loop

**Files:**
- Modify: `src/fitbit_export/cli.py`

- [ ] **Step 1: Rewrite the main callback**

Replace the `main` function (lines 98-139) with:

```python
@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return

    token_dir = _get_token_dir()
    output_dir = _get_output_dir(None)

    try:
        while True:
            data = gather_dashboard_data(token_dir=token_dir, output_dir=output_dir)
            render_dashboard(data, output_dir, token_dir=token_dir)

            if not data.users:
                if typer.confirm("Add your first Fitbit account now?", default=True):
                    auth = FitbitAuth(token_dir=token_dir)
                    try:
                        auth.add_user()
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Interrupted — returning to dashboard[/yellow]")
                    continue
                else:
                    break

            all_complete = all(len(u.completed) >= len(DATA_TYPES) for u in data.users)
            if all_complete:
                console.print("[green bold]All exports complete![/green bold]")

            action = render_action_menu(data)

            if action == "quit":
                break

            try:
                _execute_action(action, token_dir, output_dir)
            except KeyboardInterrupt:
                console.print("\n[yellow]Interrupted — returning to dashboard[/yellow]")
                continue

    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye[/dim]")
```

- [ ] **Step 2: Add the _execute_action helper**

Add this function before the `main` callback (after `_run_export`, around line 96):

```python
def _execute_action(action: str, token_dir: Path, output_dir: Path) -> None:
    auth = FitbitAuth(token_dir=token_dir)
    if action == "add-user":
        auth.add_user()
    elif action == "refresh":
        auth.refresh_user()
    elif action == "config":
        new_dir = console.input("  New export directory: ").strip()
        if new_dir:
            cfg = load_config()
            cfg["output_dir"] = str(Path(new_dir).expanduser().resolve())
            save_config(cfg)
            console.print(f"[green]Output directory set to:[/green] {cfg['output_dir']}")
    elif action == "export-all":
        _run_export(auth, output_dir, None, date(2010, 1, 1), date.today(), None)
    elif action.startswith("export-"):
        user_id = action.removeprefix("export-")
        _run_export(auth, output_dir, user_id, date(2010, 1, 1), date.today(), None)
```

- [ ] **Step 3: Run all tests**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 4: Smoke test the FSM loop**

Run: `uv run fitbit-export 2>&1`

Expected: dashboard displays, menu shows with all options including "Refresh tokens" and "Change export directory", pressing `q` exits cleanly.

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/cli.py
git commit -m "feat: convert dashboard to FSM loop with Ctrl-C handling"
```

---

### Task 6: Final verification

**Files:** None — verification only.

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 2: Smoke test all subcommands**

```bash
uv run fitbit-export --help          # shows export, add-user, list-users, status, config, refresh
uv run fitbit-export list-users      # shows users with progress (N/12)
uv run fitbit-export status          # shows dashboard, exits (one-shot)
uv run fitbit-export config          # shows paths, exits (one-shot)
uv run fitbit-export refresh --help  # shows --user option
```

- [ ] **Step 3: Smoke test FSM loop**

Run `uv run fitbit-export`, verify:
- Dashboard displays with status tables
- Menu shows all options including Refresh tokens and Change export directory
- Selecting an action and completing it returns to the dashboard
- Pressing `q` exits
- Pressing Ctrl-C during menu exits with "Goodbye"

- [ ] **Step 4: Commit any remaining changes**

```bash
git status
```
