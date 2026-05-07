from __future__ import annotations

import json
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fitbit_export.models import Checkpoint


def write_json_atomic(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=".tmp_", suffix=".json",
    )
    try:
        with open(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        Path(tmp_path).replace(path)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


CONFIG_PATH = Path.home() / ".fitbit-export" / "config.json"


def load_config(path: Path = CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict, path: Path = CONFIG_PATH) -> None:
    write_json_atomic(data, path)


def load_checkpoint(path: Path) -> Checkpoint | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    raw_completed = data.get("completed", {})
    if isinstance(raw_completed, list):
        completed = {dtype: {} for dtype in raw_completed}
    else:
        completed = raw_completed
    return Checkpoint(
        version=data["version"],
        started_at=datetime.fromisoformat(data["started_at"]),
        start_date=date.fromisoformat(data["start_date"]),
        end_date=date.fromisoformat(data["end_date"]),
        completed=completed,
        in_progress=data.get("in_progress", {}),
    )


def save_checkpoint(cp: Checkpoint, path: Path) -> None:
    data = {
        "version": cp.version,
        "started_at": cp.started_at.isoformat(),
        "start_date": cp.start_date.isoformat(),
        "end_date": cp.end_date.isoformat(),
        "completed": cp.completed,
        "in_progress": cp.in_progress,
    }
    write_json_atomic(data, path)
