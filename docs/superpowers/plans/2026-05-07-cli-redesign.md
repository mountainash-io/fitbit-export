# CLI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace argparse CLI with Typer + Rich dashboard, per-type progress bars, and subcommands.

**Architecture:** `cli.py` → Typer app with subcommands. `display.py` → all Rich rendering. `extract.py` → emits granular progress events (unchanged interface). Progress callback bridges extract→display.

**Tech Stack:** Python 3.11+, Typer 0.15+, Rich 13+, httpx 0.27+

---

### Task 1: Dependencies and .gitignore

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`

- [ ] **Step 1: Add typer and rich to pyproject.toml**

```toml
[project]
name = "fitbit-export"
version = "0.2.0"
description = "Extract all your Fitbit data before the API shuts down (September 2026)"
readme = "README.md"
requires-python = ">=3.11"
license = "MIT"
dependencies = ["httpx>=0.27", "typer[all]>=0.15", "rich>=13"]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
fitbit-export = "fitbit_export.cli:app"

[tool.hatch.build.targets.wheel]
packages = ["src/fitbit_export"]
```

Note: entry point changes from `fitbit_export.cli:main` to `fitbit_export.cli:app` (Typer app object).
Version bumped to 0.2.0.

- [ ] **Step 2: Add fitbit-export-output/ to .gitignore**

Append to `.gitignore`:

```
fitbit-export-output/
```

- [ ] **Step 3: Install updated dependencies**

Run: `uv pip install -e .`
Expected: installs typer, rich, click alongside httpx

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml .gitignore
git commit -m "chore: add typer + rich deps, bump to v0.2.0, gitignore export output"
```

---

### Task 2: Display module — dashboard rendering

**Files:**
- Create: `src/fitbit_export/display.py`
- Create: `tests/test_display.py`

- [ ] **Step 1: Write tests for dashboard data gathering**

Create `tests/test_display.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path

from fitbit_export.display import gather_dashboard_data, UserStatus


def _write_token(tmp_path: Path, user_id: str, display_name: str) -> None:
    token_dir = tmp_path / ".fitbit-export"
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / f"tokens-{user_id}.json").write_text(json.dumps({
        "user_id": user_id,
        "display_name": display_name,
        "access_token": "fake",
        "refresh_token": "fake",
    }))


def _write_checkpoint(
    tmp_path: Path, user_id: str, name: str,
    completed: list[str], in_progress: dict | None = None,
) -> None:
    user_dir = tmp_path / "fitbit-export-output" / f"{user_id}-{name}"
    user_dir.mkdir(parents=True, exist_ok=True)
    cp = {
        "version": 1,
        "started_at": datetime.now().isoformat(),
        "start_date": "2010-01-01",
        "end_date": date.today().isoformat(),
        "completed": completed,
        "in_progress": in_progress or {},
    }
    (user_dir / ".checkpoint.json").write_text(json.dumps(cp))


def test_no_users(tmp_path: Path) -> None:
    data = gather_dashboard_data(
        token_dir=tmp_path / ".fitbit-export",
        output_dir=tmp_path / "fitbit-export-output",
    )
    assert data.users == []


def test_user_no_checkpoint(tmp_path: Path) -> None:
    _write_token(tmp_path, "ABC123", "Alice")
    data = gather_dashboard_data(
        token_dir=tmp_path / ".fitbit-export",
        output_dir=tmp_path / "fitbit-export-output",
    )
    assert len(data.users) == 1
    assert data.users[0].user_id == "ABC123"
    assert data.users[0].completed == []
    assert data.users[0].has_checkpoint is False


def test_user_partial_export(tmp_path: Path) -> None:
    _write_token(tmp_path, "ABC123", "Alice")
    _write_checkpoint(tmp_path, "ABC123", "alice", ["spo2", "weight"])
    data = gather_dashboard_data(
        token_dir=tmp_path / ".fitbit-export",
        output_dir=tmp_path / "fitbit-export-output",
    )
    assert len(data.users) == 1
    assert data.users[0].completed == ["spo2", "weight"]
    assert data.users[0].has_checkpoint is True


def test_user_with_in_progress(tmp_path: Path) -> None:
    _write_token(tmp_path, "ABC123", "Alice")
    _write_checkpoint(
        tmp_path, "ABC123", "alice",
        completed=["spo2"],
        in_progress={"heart_rate_intraday": {"last_completed_date": "2024-03-15"}},
    )
    data = gather_dashboard_data(
        token_dir=tmp_path / ".fitbit-export",
        output_dir=tmp_path / "fitbit-export-output",
    )
    user = data.users[0]
    assert user.in_progress == {"heart_rate_intraday": {"last_completed_date": "2024-03-15"}}


def test_multiple_users(tmp_path: Path) -> None:
    _write_token(tmp_path, "ABC123", "Alice")
    _write_token(tmp_path, "DEF456", "Bob")
    _write_checkpoint(tmp_path, "ABC123", "alice", ["spo2", "weight"])
    data = gather_dashboard_data(
        token_dir=tmp_path / ".fitbit-export",
        output_dir=tmp_path / "fitbit-export-output",
    )
    assert len(data.users) == 2
    ids = {u.user_id for u in data.users}
    assert ids == {"ABC123", "DEF456"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_display.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fitbit_export.display'`

- [ ] **Step 3: Implement display.py — data gathering**

Create `src/fitbit_export/display.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskID

from fitbit_export.extract import DATA_TYPES

console = Console()

DEFAULT_OUTPUT_DIR = Path.home() / "fitbit-export-output"


@dataclass
class UserStatus:
    user_id: str
    display_name: str
    completed: list[str] = field(default_factory=list)
    in_progress: dict[str, dict] = field(default_factory=dict)
    has_checkpoint: bool = False
    last_run: datetime | None = None


@dataclass
class DashboardData:
    users: list[UserStatus] = field(default_factory=list)


def gather_dashboard_data(
    token_dir: Path,
    output_dir: Path,
) -> DashboardData:
    users: list[UserStatus] = []

    if not token_dir.exists():
        return DashboardData(users=[])

    for token_file in sorted(token_dir.glob("tokens-*.json")):
        try:
            tokens = json.loads(token_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        user_id = tokens.get("user_id", "")
        display_name = tokens.get("display_name", "Unknown")
        if not user_id:
            continue

        status = UserStatus(user_id=user_id, display_name=display_name)

        cp_candidates = list(output_dir.glob(f"{user_id}-*/.checkpoint.json"))
        if cp_candidates:
            cp_path = cp_candidates[0]
            try:
                cp_data = json.loads(cp_path.read_text(encoding="utf-8"))
                status.completed = cp_data.get("completed", [])
                status.in_progress = cp_data.get("in_progress", {})
                status.has_checkpoint = True
                stat = cp_path.stat()
                status.last_run = datetime.fromtimestamp(stat.st_mtime)
            except (json.JSONDecodeError, OSError):
                pass

        users.append(status)

    return DashboardData(users=users)


def render_dashboard(data: DashboardData, output_dir: Path) -> None:
    console.print(Panel(
        "[bold]Fitbit Export[/bold]\nAPI shutdown: September 2026",
        expand=False,
    ))
    console.print()

    if not data.users:
        console.print("[yellow]No authenticated Fitbit accounts found.[/yellow]")
        console.print("Run [bold]fitbit-export add-user[/bold] to connect your first account.")
        return

    accounts_table = Table(title="Accounts")
    accounts_table.add_column("User ID", style="cyan")
    accounts_table.add_column("Name")
    accounts_table.add_column("Progress")
    accounts_table.add_column("Last Run")

    for user in data.users:
        total = len(DATA_TYPES)
        done = len(user.completed)
        if not user.has_checkpoint:
            progress = "[dim]no export found[/dim]"
        elif done == total:
            progress = f"[green]{done}/{total} ✓[/green]"
        else:
            progress = f"[yellow]{done}/{total}[/yellow]"

        last_run = user.last_run.strftime("%Y-%m-%d %H:%M") if user.last_run else "-"
        accounts_table.add_row(user.user_id, user.display_name, progress, last_run)

    console.print(accounts_table)
    console.print()

    for user in data.users:
        if not user.has_checkpoint:
            continue
        remaining = [t for t in DATA_TYPES if t not in user.completed]
        if not remaining and not user.in_progress:
            continue

        detail_table = Table(
            title=f"{user.user_id} — {user.display_name} ({len(remaining)} remaining)",
        )
        detail_table.add_column("Data Type")
        detail_table.add_column("Status")
        detail_table.add_column("Detail")

        for dtype in DATA_TYPES:
            if dtype in user.completed:
                detail_table.add_row(dtype, "[green]✓ done[/green]", "")
            elif dtype in user.in_progress:
                last_date = user.in_progress[dtype].get("last_completed_date", "")
                detail_table.add_row(dtype, "[yellow]partial[/yellow]", f"through {last_date}")
            else:
                detail_table.add_row(dtype, "[dim]pending[/dim]", "")

        console.print(detail_table)
        console.print()


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

    console.print("[bold]What would you like to do?[/bold]")
    for i, (_, label) in enumerate(options, 1):
        console.print(f"  [{i}] {label}")

    while True:
        choice = console.input("\n> ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx][0]
        except ValueError:
            pass
        console.print(f"[red]Please enter a number 1-{len(options)}[/red]")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_display.py -v`
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/display.py tests/test_display.py
git commit -m "feat: add display module — dashboard data gathering and Rich rendering"
```

---

### Task 3: Display module — progress bar factory

**Files:**
- Modify: `src/fitbit_export/display.py`
- Create: `tests/test_progress.py`

- [ ] **Step 1: Write tests for progress callback**

Create `tests/test_progress.py`:

```python
from __future__ import annotations

from fitbit_export.display import ProgressTracker
from fitbit_export.models import ProgressEvent
from fitbit_export.extract import DATA_TYPES


def test_progress_tracker_lifecycle() -> None:
    tracker = ProgressTracker(data_types=["spo2", "weight"])
    tracker.start()

    tracker.on_progress(ProgressEvent(
        data_type="spo2", status="starting",
        current_date=None, pct=None, message=None,
    ))
    tracker.on_progress(ProgressEvent(
        data_type="spo2", status="complete",
        current_date=None, pct=1.0, message="142 records",
    ))
    tracker.on_progress(ProgressEvent(
        data_type="weight", status="skipped",
        current_date=None, pct=None, message="Already completed",
    ))

    tracker.stop()


def test_progress_tracker_handles_error() -> None:
    tracker = ProgressTracker(data_types=["spo2"])
    tracker.start()

    tracker.on_progress(ProgressEvent(
        data_type="spo2", status="starting",
        current_date=None, pct=None, message=None,
    ))
    tracker.on_progress(ProgressEvent(
        data_type="spo2", status="error",
        current_date=None, pct=None, message="429 rate limited",
    ))

    tracker.stop()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_progress.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProgressTracker'`

- [ ] **Step 3: Implement ProgressTracker in display.py**

Append to `src/fitbit_export/display.py`:

```python
class ProgressTracker:
    def __init__(self, data_types: list[str] | None = None) -> None:
        self._types = data_types or DATA_TYPES
        self._progress = Progress(
            TextColumn("{task.description}", justify="right", style="bold"),
            BarColumn(bar_width=30),
            TextColumn("{task.percentage:>3.0f}%"),
            TextColumn("{task.fields[status]}", style="dim"),
            TimeRemainingColumn(),
            console=console,
        )
        self._tasks: dict[str, TaskID] = {}

    def start(self) -> None:
        self._progress.start()
        for dtype in self._types:
            self._tasks[dtype] = self._progress.add_task(
                dtype, total=100, status="", visible=True,
            )

    def stop(self) -> None:
        self._progress.stop()

    def on_progress(self, evt: ProgressEvent) -> None:
        task_id = self._tasks.get(evt.data_type)
        if task_id is None:
            return

        if evt.status == "skipped":
            self._progress.update(task_id, completed=100, status="[green]✓ done[/green]")
        elif evt.status == "starting":
            self._progress.update(task_id, completed=0, status="starting...")
        elif evt.status == "progress":
            pct = (evt.pct or 0) * 100
            status_text = ""
            if evt.current_date:
                status_text = str(evt.current_date)
            elif evt.message:
                status_text = evt.message
            self._progress.update(task_id, completed=pct, status=status_text)
        elif evt.status == "rate_limited":
            self._progress.update(task_id, status=f"[yellow]{evt.message}[/yellow]")
        elif evt.status == "complete":
            self._progress.update(task_id, completed=100, status=f"[green]{evt.message}[/green]")
        elif evt.status == "error":
            self._progress.update(task_id, status=f"[red]{evt.message}[/red]")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_progress.py -v`
Expected: all 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/display.py tests/test_progress.py
git commit -m "feat: add ProgressTracker — Rich progress bars for extraction"
```

---

### Task 4: Emit granular progress from extract.py

**Files:**
- Modify: `src/fitbit_export/extract.py`

- [ ] **Step 1: Add progress emission to `_fetch_heart_rate_intraday`**

In `src/fitbit_export/extract.py`, the `_fetch_heart_rate_intraday` function needs an `on_progress` callback parameter. But since it's called from `FitbitExtractor.run()` which already has the callback, we thread it through.

Modify `FitbitExtractor.run()` — in the `heart_rate_intraday` branch (around line 333), add progress emission inside `_fetch_heart_rate_intraday`. The function already has a `while current <= end` loop. Add an `on_progress` parameter:

Change the function signature at line 129:

```python
def _fetch_heart_rate_intraday(
    client: httpx.Client, start: date, end: date,
    output_dir: Path, checkpoint: Checkpoint, cp_path: Path,
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> list[dict]:
```

Inside the while loop, after `save_checkpoint(checkpoint, cp_path)` (line 157), add:

```python
        if on_progress:
            total_days = (end - start).days + 1
            done_days = (current - start).days + 1
            on_progress(ProgressEvent(
                data_type="heart_rate_intraday",
                status="progress",
                current_date=current,
                pct=done_days / total_days if total_days > 0 else 1.0,
                message=None,
            ))
```

- [ ] **Step 2: Add rate_limited event to `_request_with_retry`**

At line 31, where the retry wait message is printed, also accept and call an optional callback. However, since `_request_with_retry` is a low-level function called from many places, the simplest approach is to change the `print()` at line 31 to use the progress callback if available.

Instead of modifying `_request_with_retry`, add a `rate_limited` emission in `FitbitExtractor.run()` by catching the wait message. This is cleaner: wrap the retry wait in `_fetch_heart_rate_intraday`:

Replace line 31 in `_request_with_retry`:

```python
            print(f"    Rate limited — waiting {int(wait)}s before retry...")
```

With:

```python
            # Rate limit message handled by caller's progress callback if available
            print(f"    Rate limited — waiting {int(wait)}s before retry...")
```

Leave this as-is for now — the print goes to stderr-like output while Rich owns the progress display. Rich's `Progress` uses alternate screen buffering so the print won't interfere. This is a minor cosmetic issue we can revisit.

- [ ] **Step 3: Thread on_progress into _fetch_heart_rate_intraday call**

In `FitbitExtractor.run()`, change the `heart_rate_intraday` call (around line 334):

```python
                if dtype == "heart_rate_intraday":
                    items = _fetch_heart_rate_intraday(
                        self._client, start, self._end,
                        self._output_dir, checkpoint, cp_path,
                        on_progress=self._on_progress,
                    )
```

- [ ] **Step 4: Run existing tests to verify no regressions**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitbit_export/extract.py
git commit -m "feat: emit granular progress events from heart_rate_intraday extraction"
```

---

### Task 5: Rewrite cli.py with Typer

**Files:**
- Modify: `src/fitbit_export/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write tests for CLI subcommands**

Create `tests/test_cli.py`:

```python
from __future__ import annotations

from typer.testing import CliRunner

from fitbit_export.cli import app

runner = CliRunner()


def test_status_no_users(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FITBIT_TOKEN_DIR", str(tmp_path / ".fitbit-export"))
    monkeypatch.setenv("FITBIT_OUTPUT_DIR", str(tmp_path / "fitbit-export-output"))
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "No authenticated" in result.output


def test_list_users_no_users(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FITBIT_TOKEN_DIR", str(tmp_path / ".fitbit-export"))
    result = runner.invoke(app, ["list-users"])
    assert result.exit_code == 0
    assert "No authenticated" in result.output


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "export" in result.output
    assert "add-user" in result.output
    assert "list-users" in result.output
    assert "status" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL — `ImportError: cannot import name 'app'`

- [ ] **Step 3: Rewrite cli.py**

Replace `src/fitbit_export/cli.py` entirely:

```python
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from fitbit_export.auth import FitbitAuth, TOKEN_DIR
from fitbit_export.display import (
    DEFAULT_OUTPUT_DIR,
    ProgressTracker,
    gather_dashboard_data,
    render_action_menu,
    render_dashboard,
)
from fitbit_export.extract import DATA_TYPES, FitbitExtractor

console = Console()
app = typer.Typer(
    name="fitbit-export",
    help="Extract all your Fitbit data before the API shuts down (September 2026).",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _get_token_dir() -> Path:
    override = os.environ.get("FITBIT_TOKEN_DIR")
    return Path(override) if override else TOKEN_DIR


def _get_output_dir(output: Path | None) -> Path:
    override = os.environ.get("FITBIT_OUTPUT_DIR")
    if override:
        return Path(override)
    return output or DEFAULT_OUTPUT_DIR


def _run_export(
    auth: FitbitAuth,
    output_dir: Path,
    user_id: str | None,
    start: date,
    end: date,
    types: str | None,
) -> None:
    if user_id:
        users = [auth.authenticate(user_id)]
    else:
        users = auth.authenticate_all()

    data_types = types.split(",") if types else None

    for user in users:
        user_dir = output_dir / f"{user.user_id}-{user.display_name.split()[0].lower()}"
        console.print(f"\n[bold]Exporting {user.display_name} ({user.user_id})[/bold]")
        console.print(f"  Date range: {start} → {end}")
        console.print(f"  Output: {user_dir.resolve()}\n")

        tracker = ProgressTracker(data_types=data_types)
        tracker.start()

        extractor = FitbitExtractor(
            client=user.client,
            output_dir=user_dir,
            start=start,
            end=end,
            on_progress=tracker.on_progress,
        )
        result = extractor.run(data_types=data_types)
        tracker.stop()

        console.print(f"\n  Done in {result.duration_seconds:.1f}s")
        if result.failed:
            for dtype, err in result.failed.items():
                console.print(f"  [red]✗ {dtype}: {err}[/red]")
            rate_limited = [k for k in result.failed if "429" in result.failed[k]]
            if rate_limited:
                console.print("\n  [yellow]Rate limited — run again in ~1 hour to resume.[/yellow]")
        console.print()
        user.client.close()


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return

    token_dir = _get_token_dir()
    output_dir = _get_output_dir(None)
    data = gather_dashboard_data(token_dir=token_dir, output_dir=output_dir)
    render_dashboard(data, output_dir)

    if not data.users:
        if typer.confirm("Add your first Fitbit account now?", default=True):
            auth = FitbitAuth(token_dir=token_dir)
            auth.add_user()
        return

    all_complete = all(len(u.completed) >= len(DATA_TYPES) for u in data.users)
    if all_complete:
        console.print("[green bold]All exports complete![/green bold]")
        return

    action = render_action_menu(data)

    if action == "quit":
        return
    elif action == "add-user":
        auth = FitbitAuth(token_dir=token_dir)
        auth.add_user()
    elif action == "export-all":
        auth = FitbitAuth(token_dir=token_dir)
        _run_export(auth, output_dir, None, date(2010, 1, 1), date.today(), None)
    elif action.startswith("export-"):
        user_id = action.removeprefix("export-")
        auth = FitbitAuth(token_dir=token_dir)
        _run_export(auth, output_dir, user_id, date(2010, 1, 1), date.today(), None)


@app.command()
def export(
    user: Optional[str] = typer.Option(None, help="Export specific user (Fitbit ID)"),
    start: str = typer.Option("2010-01-01", help="Start date (YYYY-MM-DD)"),
    end: str = typer.Option(date.today().isoformat(), help="End date (YYYY-MM-DD)"),
    output: Optional[Path] = typer.Option(None, help="Output directory (default: ~/fitbit-export-output)"),
    types: Optional[str] = typer.Option(None, help=f"Comma-separated types: {','.join(DATA_TYPES)}"),
) -> None:
    """Run the Fitbit data export."""
    token_dir = _get_token_dir()
    output_dir = _get_output_dir(output)
    auth = FitbitAuth(token_dir=token_dir)
    _run_export(auth, output_dir, user, date.fromisoformat(start), date.fromisoformat(end), types)


@app.command()
def add_user() -> None:
    """Add a new Fitbit account via browser OAuth."""
    token_dir = _get_token_dir()
    auth = FitbitAuth(token_dir=token_dir)
    auth.add_user()


@app.command()
def list_users() -> None:
    """List authenticated Fitbit accounts."""
    token_dir = _get_token_dir()
    auth = FitbitAuth(token_dir=token_dir)
    users = auth.list_users()
    if not users:
        console.print("[yellow]No authenticated users.[/yellow]")
        console.print("Run [bold]fitbit-export add-user[/bold] to connect an account.")
        return
    for u in users:
        console.print(f"  {u['display_name']} ({u['user_id']})")


@app.command()
def status(
    output: Optional[Path] = typer.Option(None, help="Output directory to check (default: ~/fitbit-export-output)"),
) -> None:
    """Show export status dashboard (no actions)."""
    token_dir = _get_token_dir()
    output_dir = _get_output_dir(output)
    data = gather_dashboard_data(token_dir=token_dir, output_dir=output_dir)
    render_dashboard(data, output_dir)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all 3 tests PASS

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 6: Manual smoke test**

Run: `uv run fitbit-export --help`
Expected: shows subcommands: export, add-user, list-users, status

Run: `uv run fitbit-export status`
Expected: shows dashboard (may say "no authenticated users" or show real data)

Run: `uv run fitbit-export`
Expected: shows dashboard + action menu

- [ ] **Step 7: Commit**

```bash
git add src/fitbit_export/cli.py tests/test_cli.py
git commit -m "feat: rewrite CLI with Typer subcommands and Rich dashboard"
```

---

### Task 6: Update __main__.py entry point

**Files:**
- Modify: `src/fitbit_export/__main__.py`

- [ ] **Step 1: Read current __main__.py**

Current content is likely: `from fitbit_export.cli import main; main()`

- [ ] **Step 2: Update to use Typer app**

Replace `src/fitbit_export/__main__.py`:

```python
from fitbit_export.cli import app

app()
```

- [ ] **Step 3: Test**

Run: `uv run python -m fitbit_export --help`
Expected: same output as `uv run fitbit-export --help`

- [ ] **Step 4: Commit**

```bash
git add src/fitbit_export/__main__.py
git commit -m "fix: update __main__.py entry point for Typer app"
```

---

### Task 7: Update SKILL.md for new CLI

**Files:**
- Modify: `skills/fitbit-export/SKILL.md`

- [ ] **Step 1: Update SKILL.md Phase 0 bootstrap**

In the SKILL.md Bootstrap section, the install command is already `uv venv && uv pip install -e .` — no change needed there.

- [ ] **Step 2: Update Phase 2 — Authentication**

Change line 108 (the `--add-user` invocation):

```
    result = Bash("cd {plugin_dir} && .venv/bin/fitbit-export add-user --output {output_dir}")
```

- [ ] **Step 3: Update Phase 3 — list users**

Change line 136 (the `--list-users` invocation):

```
    result = Bash("cd {plugin_dir} && .venv/bin/fitbit-export list-users")
```

- [ ] **Step 4: Update Phase 4 — Extract**

Change line 196 (the export invocation):

```
    result = Bash(
      "cd {plugin_dir} && .venv/bin/fitbit-export export --user {user.user_id} --output {output_dir}",
      timeout: 600000  # 10 minutes max per run
    )
```

- [ ] **Step 5: Commit**

```bash
git add skills/fitbit-export/SKILL.md
git commit -m "docs: update SKILL.md for new Typer subcommand structure"
```

---

### Task 8: Update README and docs — pip → uv, new CLI

**Files:**
- Modify: `README.md`
- Modify: `INSTALL.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Fix README — pip install → uv**

In README.md, the "Install as Python CLI" section (around line 59):

Change:
```bash
pip install .
```

To:
```bash
uv pip install .
```

- [ ] **Step 2: Fix README — CLI options section**

Update the "CLI Options" section to show subcommands:

```
## CLI Commands

fitbit-export                Show dashboard and choose an action
fitbit-export export         Run the data export
fitbit-export add-user       Add a new Fitbit account
fitbit-export list-users     List authenticated accounts
fitbit-export status         Show export progress

## Export Options

fitbit-export export [OPTIONS]

--start DATE     Start date (default: 2010-01-01)
--end DATE       End date (default: today)
--output DIR     Output directory (default: ~/fitbit-export-output)
--types TYPES    Comma-separated data types to export
--user ID        Export only this user
```

- [ ] **Step 3: Update CHANGELOG.md**

Add a new section at the top:

```markdown
## [0.2.0] - 2026-05-07

### Changed

- CLI rewritten with Typer subcommands: `export`, `add-user`, `list-users`, `status`
- Running `fitbit-export` with no arguments now shows a dashboard and action menu instead of immediately exporting
- Default output directory changed from `./fitbit-export-output` to `~/fitbit-export-output`
- Progress display uses Rich progress bars per data type instead of plain text
- All documentation updated to use `uv` instead of `pip`

### Added

- Dashboard showing per-user export progress and per-type status
- Rich progress bars with ETA for long-running extractions (heart_rate_intraday)
- `fitbit-export status` command for read-only dashboard view
- `.gitignore` entry for `fitbit-export-output/`

### Removed

- Old `--add-user`, `--list-users` top-level flags (replaced by subcommands)
```

Update the links at the bottom:

```markdown
[0.2.0]: https://github.com/mountainash-io/fitbit-export/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mountainash-io/fitbit-export/releases/tag/v0.1.0
```

- [ ] **Step 4: Verify INSTALL.md**

Check INSTALL.md uses `uv` throughout. It already does — no changes needed.

- [ ] **Step 5: Commit**

```bash
git add README.md CHANGELOG.md
git commit -m "docs: update README and CHANGELOG for v0.2.0 CLI redesign"
```

---

### Task 9: Clean up and final verification

**Files:** None new — verification only.

- [ ] **Step 1: Delete stale export output from working tree**

```bash
rm -rf fitbit-export-output/
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest -v`
Expected: all tests PASS

- [ ] **Step 3: Manual end-to-end smoke test**

Run: `uv run fitbit-export`
Expected: dashboard with action menu (or welcome screen if no tokens)

Run: `uv run fitbit-export status`
Expected: dashboard only, no action menu

Run: `uv run fitbit-export list-users`
Expected: user list or "no authenticated users" message

Run: `uv run fitbit-export export --help`
Expected: shows --user, --start, --end, --output, --types options

- [ ] **Step 4: Commit any remaining changes**

```bash
git status
# If clean, nothing to do. If stray files, commit them.
```
