from __future__ import annotations

import json
from pathlib import Path

from fitbit_export.io import write_json_atomic


def test_write_json_atomic(tmp_path):
    target = tmp_path / "output.json"
    write_json_atomic({"key": "value"}, target)
    assert target.exists()
    assert json.loads(target.read_text()) == {"key": "value"}


def test_write_json_atomic_creates_parents(tmp_path):
    target = tmp_path / "a" / "b" / "output.json"
    write_json_atomic([1, 2, 3], target)
    assert json.loads(target.read_text()) == [1, 2, 3]


def test_write_json_atomic_utf8(tmp_path):
    target = tmp_path / "output.json"
    write_json_atomic({"name": "日本語"}, target)
    text = target.read_text(encoding="utf-8")
    assert "日本語" in text
    assert "\\u" not in text
