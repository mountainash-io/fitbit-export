from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path

from fitbit_export.display import gather_dashboard_data


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
