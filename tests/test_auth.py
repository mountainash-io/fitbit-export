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
