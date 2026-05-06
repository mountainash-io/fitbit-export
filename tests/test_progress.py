from __future__ import annotations

from fitbit_export.display import ProgressTracker
from fitbit_export.models import ProgressEvent


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
