from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class ProgressEvent:
    data_type: str
    status: str
    current_date: date | None
    pct: float | None
    message: str | None


@dataclass(frozen=True)
class ExtractResult:
    output_dir: Path
    completed: list[str]
    failed: dict[str, str]
    record_counts: dict[str, int]
    duration_seconds: float


@dataclass
class RateLimit:
    remaining: int = 150
    limit: int = 150
    reset_seconds: int = 3600


@dataclass
class Checkpoint:
    version: int
    started_at: datetime
    start_date: date
    end_date: date
    completed: list[str] = field(default_factory=list)
    in_progress: dict[str, dict] = field(default_factory=dict)
