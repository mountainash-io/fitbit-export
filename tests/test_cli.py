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
    assert "refresh" in result.output


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
