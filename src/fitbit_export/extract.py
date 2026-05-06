from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import httpx

from fitbit_export.models import ProgressEvent, ExtractResult, Checkpoint
from fitbit_export.io import write_json_atomic, load_checkpoint, save_checkpoint


def _request_with_retry(
    client: httpx.Client, path: str, params: dict,
    max_retries: int = 5, backoff_base: float = 30.0, timeout: float = 30.0,
) -> httpx.Response:
    for attempt in range(max_retries + 1):
        resp = client.get(path, params=params, timeout=timeout)
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt >= max_retries:
                raise RuntimeError(
                    f"Failed after {max_retries} retries: {resp.status_code} from {path}"
                )
            retry_after = resp.headers.get("Retry-After")
            if retry_after and resp.status_code == 429:
                wait = float(retry_after)
            else:
                wait = backoff_base * (2 ** attempt)
            print(f"    Rate limited — waiting {int(wait)}s before retry...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Unreachable: exhausted retries for {path}")


def _fetch_chunked(
    client: httpx.Client, path_template: str,
    start: date, end: date, max_range_days: int, response_key: str,
) -> list[dict]:
    results: list[dict] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=max_range_days - 1), end)
        path = path_template.format(start=current.isoformat(), end=chunk_end.isoformat())
        resp = _request_with_retry(client, path, {})
        data = resp.json()
        items = data.get(response_key, [])
        if isinstance(items, list):
            results.extend(items)
        else:
            results.append(data)
        current = chunk_end + timedelta(days=1)
    return results


def _fetch_activities(client: httpx.Client, start: date, end: date) -> list[dict]:
    results: list[dict] = []
    offset = 0
    limit = 100
    for _ in range(100):
        resp = _request_with_retry(
            client, "/1/user/-/activities/list.json",
            {"afterDate": start.isoformat(), "sort": "asc", "limit": limit, "offset": offset},
        )
        data = resp.json()
        items = data.get("activities", [])
        if not items:
            break
        for item in items:
            start_str = item.get("startTime", "")
            if start_str:
                activity_date = datetime.fromisoformat(start_str).date()
                if activity_date > end:
                    return results
            results.append(item)
        next_url = data.get("pagination", {}).get("next", "")
        if not next_url:
            break
        offset += limit
    return results


def _fetch_activity_tcx(
    client: httpx.Client, start: date, end: date,
    output_dir: Path, checkpoint: Checkpoint, cp_path: Path,
) -> list[dict]:
    tcx_dir = output_dir / "raw" / "activity_tcx"
    tcx_dir.mkdir(parents=True, exist_ok=True)

    activities = _fetch_activities(client, start, end)
    downloaded = []
    for activity in activities:
        log_id = activity.get("logId")
        if not log_id:
            continue
        if activity.get("logType") == "auto_detected":
            continue

        tcx_path = tcx_dir / f"{log_id}.tcx"
        if tcx_path.exists():
            downloaded.append({"logId": log_id, "file": str(tcx_path.name)})
            continue

        resp = _request_with_retry(
            client, f"/1/user/-/activities/{log_id}.tcx", {},
        )
        content = resp.content
        if content.count(b"\n") <= 15:
            continue

        tcx_path.write_bytes(content)
        downloaded.append({"logId": log_id, "file": str(tcx_path.name)})

    write_json_atomic(downloaded, output_dir / "raw" / "activity_tcx.json")
    return downloaded


def _fetch_sleep(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1.2/user/-/sleep/date/{start}/{end}.json", start, end, 100, "sleep")


def _fetch_heart_rate_summary(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/activities/heart/date/{start}/{end}.json", start, end, 365, "activities-heart")


def _fetch_heart_rate_intraday(
    client: httpx.Client, start: date, end: date,
    output_dir: Path, checkpoint: Checkpoint, cp_path: Path,
) -> list[dict]:
    part_dir = output_dir / "raw" / "heart_rate_intraday"
    results: list[dict] = []
    current = start
    while current <= end:
        resp = _request_with_retry(
            client,
            f"/1/user/-/activities/heart/date/{current.isoformat()}/1d/1min.json",
            {},
        )
        data = resp.json()
        intraday = data.get("activities-heart-intraday", {})
        dataset = intraday.get("dataset", [])
        if dataset:
            item = {"date": current.isoformat(), "response": data}
            results.append(item)
            year = current.isoformat()[:4]
            year_file = part_dir / f"{year}.json"
            if year_file.exists():
                existing = json.loads(year_file.read_text(encoding="utf-8"))
            else:
                existing = []
            existing.append(item)
            write_json_atomic(existing, year_file)
        checkpoint.in_progress["heart_rate_intraday"] = {"last_completed_date": current.isoformat()}
        save_checkpoint(checkpoint, cp_path)
        current += timedelta(days=1)
    return results


def _fetch_hrv(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/hrv/date/{start}/{end}.json", start, end, 30, "hrv")


def _fetch_spo2(client: httpx.Client, start: date, end: date) -> list[dict]:
    resp = _request_with_retry(client, f"/1/user/-/spo2/date/{start.isoformat()}/{end.isoformat()}.json", {})
    data = resp.json()
    if isinstance(data, list):
        return data
    return [data] if data else []


def _fetch_breathing_rate(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/br/date/{start}/{end}.json", start, end, 30, "br")


def _fetch_skin_temperature(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/temp/skin/date/{start}/{end}.json", start, end, 30, "tempSkin")


def _fetch_weight(client: httpx.Client, start: date, end: date) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/body/log/weight/date/{start}/{end}.json", start, end, 30, "weight")


def _fetch_daily_summary(client: httpx.Client, start: date, end: date) -> list[dict]:
    resources = ["steps", "calories", "distance", "floors", "minutesSedentary",
                 "minutesLightlyActive", "minutesFairlyActive", "minutesVeryActive"]
    by_date: dict[str, dict] = {}
    for resource in resources:
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=1094), end)
            resp = _request_with_retry(
                client,
                f"/1/user/-/activities/{resource}/date/{current.isoformat()}/{chunk_end.isoformat()}.json",
                {},
            )
            data = resp.json()
            series = data.get(f"activities-{resource}", [])
            for entry in series:
                d = entry.get("dateTime", "")
                if d not in by_date:
                    by_date[d] = {"dateTime": d}
                by_date[d][resource] = entry.get("value", "0")
            current = chunk_end + timedelta(days=1)

    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=1094), end)
        resp = _request_with_retry(
            client,
            f"/1/user/-/activities/active-zone-minutes/date/{current.isoformat()}/{chunk_end.isoformat()}.json",
            {},
        )
        data = resp.json()
        for entry in data.get("activities-active-zone-minutes", []):
            d = entry.get("dateTime", "")
            if d not in by_date:
                by_date[d] = {"dateTime": d}
            by_date[d]["activeZoneMinutes"] = entry.get("value", {})
        current = chunk_end + timedelta(days=1)

    return [by_date[d] for d in sorted(by_date.keys())]


def _fetch_nutrition(client: httpx.Client, start: date, end: date) -> list[dict]:
    by_date: dict[str, dict] = {}
    for resource in ["caloriesIn", "water"]:
        current = start
        while current <= end:
            chunk_end = min(current + timedelta(days=1094), end)
            resp = _request_with_retry(
                client,
                f"/1/user/-/foods/log/{resource}/date/{current.isoformat()}/{chunk_end.isoformat()}.json",
                {},
            )
            data = resp.json()
            series = data.get(f"foods-log-{resource}", [])
            for entry in series:
                d = entry.get("dateTime", "")
                if d not in by_date:
                    by_date[d] = {"dateTime": d}
                by_date[d][resource] = entry.get("value", "0")
            current = chunk_end + timedelta(days=1)
    return [by_date[d] for d in sorted(by_date.keys())]


DATA_TYPES = [
    "spo2", "weight", "nutrition", "daily_summary", "activities",
    "activity_tcx", "sleep", "heart_rate_summary", "hrv", "breathing_rate",
    "skin_temperature", "heart_rate_intraday",
]

_FETCH_FUNCTIONS: dict[str, Callable] = {
    "activities": _fetch_activities,
    "sleep": _fetch_sleep,
    "heart_rate_summary": _fetch_heart_rate_summary,
    "hrv": _fetch_hrv,
    "spo2": _fetch_spo2,
    "breathing_rate": _fetch_breathing_rate,
    "skin_temperature": _fetch_skin_temperature,
    "weight": _fetch_weight,
    "daily_summary": _fetch_daily_summary,
    "nutrition": _fetch_nutrition,
}


class FitbitExtractor:
    def __init__(
        self,
        client: httpx.Client,
        output_dir: Path,
        start: date,
        end: date,
        on_progress: Callable[[ProgressEvent], None] | None = None,
    ) -> None:
        self._client = client
        self._output_dir = output_dir
        self._start = start
        self._end = end
        self._on_progress = on_progress

    def _emit(self, data_type: str, status: str, **kwargs: Any) -> None:
        if self._on_progress:
            self._on_progress(ProgressEvent(
                data_type=data_type, status=status,
                current_date=kwargs.get("current_date"),
                pct=kwargs.get("pct"),
                message=kwargs.get("message"),
            ))

    def run(self, data_types: list[str] | None = None) -> ExtractResult:
        t0 = time.monotonic()
        raw_dir = self._output_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        cp_path = self._output_dir / ".checkpoint.json"

        checkpoint = load_checkpoint(cp_path)
        if checkpoint is None:
            checkpoint = Checkpoint(
                version=1, started_at=datetime.now(),
                start_date=self._start, end_date=self._end,
            )

        type_order = data_types or DATA_TYPES
        completed: list[str] = []
        failed: dict[str, str] = {}
        record_counts: dict[str, int] = {}

        for dtype in type_order:
            if dtype in checkpoint.completed:
                self._emit(dtype, "skipped", message="Already completed")
                completed.append(dtype)
                continue

            self._emit(dtype, "starting")

            try:
                start = self._start
                if dtype in checkpoint.in_progress:
                    last = checkpoint.in_progress[dtype].get("last_completed_date")
                    if last:
                        start = date.fromisoformat(last) + timedelta(days=1)
                        if start > self._end:
                            checkpoint.completed.append(dtype)
                            checkpoint.in_progress.pop(dtype, None)
                            save_checkpoint(checkpoint, cp_path)
                            self._emit(dtype, "complete", pct=1.0, message="Resumed — already done")
                            completed.append(dtype)
                            continue

                if dtype == "heart_rate_intraday":
                    items = _fetch_heart_rate_intraday(
                        self._client, start, self._end,
                        self._output_dir, checkpoint, cp_path,
                    )
                elif dtype == "activity_tcx":
                    items = _fetch_activity_tcx(
                        self._client, start, self._end,
                        self._output_dir, checkpoint, cp_path,
                    )
                else:
                    fetch_fn = _FETCH_FUNCTIONS[dtype]
                    items = fetch_fn(self._client, start, self._end)
                    write_json_atomic(items, raw_dir / f"{dtype}.json")

                record_counts[dtype] = len(items)
                checkpoint.completed.append(dtype)
                checkpoint.in_progress.pop(dtype, None)
                save_checkpoint(checkpoint, cp_path)
                self._emit(dtype, "complete", pct=1.0, message=f"{len(items)} records")
                completed.append(dtype)

            except Exception as exc:
                save_checkpoint(checkpoint, cp_path)
                self._emit(dtype, "error", message=str(exc))
                failed[dtype] = str(exc)

        return ExtractResult(
            output_dir=self._output_dir, completed=completed,
            failed=failed, record_counts=record_counts,
            duration_seconds=time.monotonic() - t0,
        )
