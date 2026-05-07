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
