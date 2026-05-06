from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TaskID  # noqa: F401 — used by ProgressTracker in Task 3

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
