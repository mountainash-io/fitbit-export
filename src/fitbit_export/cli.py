from __future__ import annotations

import os
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
