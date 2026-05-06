from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from fitbit_export.extract import FitbitExtractor, DATA_TYPES


def _mock_response(data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    resp.headers = {}
    return resp


def test_extractor_creates_raw_dir(tmp_path):
    client = MagicMock()
    client.get.return_value = _mock_response({})
    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 1))
    extractor.run(data_types=["spo2"])
    assert (tmp_path / "raw").is_dir()


def test_extractor_writes_checkpoint(tmp_path):
    client = MagicMock()
    client.get.return_value = _mock_response({})
    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 1))
    extractor.run(data_types=["spo2"])
    cp = json.loads((tmp_path / ".checkpoint.json").read_text())
    assert "spo2" in cp["completed"]


def test_extractor_skips_completed(tmp_path):
    cp = {"version": 1, "started_at": "2026-05-06T14:30:00", "start_date": "2024-01-01", "end_date": "2024-01-01", "completed": ["spo2"], "in_progress": {}}
    (tmp_path / ".checkpoint.json").write_text(json.dumps(cp))
    client = MagicMock()
    events = []
    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 1), on_progress=events.append)
    extractor.run(data_types=["spo2"])
    assert any(e.status == "skipped" for e in events)


def test_extractor_continues_on_failure(tmp_path):
    client = MagicMock()
    client.get.side_effect = Exception("boom")
    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 1))
    result = extractor.run(data_types=["spo2"])
    assert "spo2" in result.failed


def test_data_types_list():
    assert "activities" in DATA_TYPES
    assert "activity_tcx" in DATA_TYPES
    assert "heart_rate_intraday" in DATA_TYPES
    assert len(DATA_TYPES) == 12


def test_activity_tcx_download(tmp_path):
    tcx_content = b"<?xml version='1.0'?>\n" + b"<line>\n" * 20
    activities_resp = _mock_response({
        "pagination": {"next": ""},
        "activities": [
            {"logId": 111, "activityName": "Run", "logType": "tracker",
             "startTime": "2024-01-15T08:00:00.000+00:00"},
            {"logId": 222, "activityName": "Walk", "logType": "auto_detected",
             "startTime": "2024-01-15T12:00:00.000+00:00"},
        ],
    })
    tcx_resp = MagicMock()
    tcx_resp.status_code = 200
    tcx_resp.content = tcx_content
    tcx_resp.raise_for_status = MagicMock()
    tcx_resp.headers = {}

    client = MagicMock()
    client.get.side_effect = [activities_resp, tcx_resp]

    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 31))
    result = extractor.run(data_types=["activity_tcx"])

    assert "activity_tcx" in result.completed
    assert (tmp_path / "raw" / "activity_tcx" / "111.tcx").exists()
    assert not (tmp_path / "raw" / "activity_tcx" / "222.tcx").exists()  # auto_detected skipped


def test_intraday_checkpoint_per_day(tmp_path):
    responses = []
    for d in [date(2024, 1, 1), date(2024, 1, 2)]:
        responses.append(_mock_response({
            "activities-heart": [{"dateTime": d.isoformat(), "value": {}}],
            "activities-heart-intraday": {"dataset": [{"time": "00:00:00", "value": 60}]},
        }))
    client = MagicMock()
    client.get.side_effect = responses
    extractor = FitbitExtractor(client=client, output_dir=tmp_path, start=date(2024, 1, 1), end=date(2024, 1, 2))
    result = extractor.run(data_types=["heart_rate_intraday"])
    assert "heart_rate_intraday" in result.completed
    assert (tmp_path / "raw" / "heart_rate_intraday" / "2024.json").exists()
    data = json.loads((tmp_path / "raw" / "heart_rate_intraday" / "2024.json").read_text())
    assert len(data) == 2
