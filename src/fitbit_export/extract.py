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
    on_retry: Callable[[int], None] | None = None,
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
            if on_retry:
                on_retry(int(wait))
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Unreachable: exhausted retries for {path}")


def _fetch_chunked(
    client: httpx.Client, path_template: str,
    start: date, end: date, max_range_days: int, response_key: str,
    dtype: str = "", on_progress: Callable[[ProgressEvent], None] | None = None,
) -> list[dict]:
    results: list[dict] = []
    current = start
    total_days = (end - start).days + 1
    while current <= end:
        chunk_end = min(current + timedelta(days=max_range_days - 1), end)
        if on_progress and dtype:
            done_days = (current - start).days
            on_progress(ProgressEvent(
                data_type=dtype, status="progress",
                current_date=current, pct=done_days / total_days if total_days > 0 else 0,
                message=f"fetching {current} → {chunk_end}",
            ))
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


def _fetch_activities(
    client: httpx.Client, start: date, end: date,
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> list[dict]:
    results: list[dict] = []
    offset = 0
    limit = 100
    for page in range(100):
        if on_progress:
            on_progress(ProgressEvent(
                data_type="activities", status="progress",
                current_date=None, pct=None,
                message=f"page {page + 1} ({len(results)} so far)",
            ))
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
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> list[dict]:
    tcx_dir = output_dir / "raw" / "activity_tcx"
    tcx_dir.mkdir(parents=True, exist_ok=True)

    if on_progress:
        on_progress(ProgressEvent(
            data_type="activity_tcx", status="progress",
            current_date=None, pct=None, message="listing activities...",
        ))
    activities = _fetch_activities(client, start, end, on_progress=None)
    total = len(activities)
    downloaded = []
    for i, activity in enumerate(activities):
        log_id = activity.get("logId")
        if not log_id:
            continue
        if activity.get("logType") == "auto_detected":
            continue

        if on_progress:
            on_progress(ProgressEvent(
                data_type="activity_tcx", status="progress",
                current_date=None,
                pct=(i + 1) / total if total > 0 else 1.0,
                message=f"downloading {i + 1}/{total}",
            ))

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


def _fetch_sleep(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1.2/user/-/sleep/date/{start}/{end}.json", start, end, 100, "sleep", dtype="sleep", on_progress=on_progress)


def _fetch_heart_rate_summary(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/activities/heart/date/{start}/{end}.json", start, end, 365, "activities-heart", dtype="heart_rate_summary", on_progress=on_progress)


def _fetch_heart_rate_intraday(
    client: httpx.Client, start: date, end: date,
    output_dir: Path, checkpoint: Checkpoint, cp_path: Path,
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> list[dict]:
    part_dir = output_dir / "raw" / "heart_rate_intraday"
    results: list[dict] = []
    current = start
    def _on_retry(wait_seconds: int) -> None:
        if on_progress:
            on_progress(ProgressEvent(
                data_type="heart_rate_intraday",
                status="rate_limited",
                current_date=current,
                pct=None,
                message=f"waiting {wait_seconds}s...",
            ))

    while current <= end:
        resp = _request_with_retry(
            client,
            f"/1/user/-/activities/heart/date/{current.isoformat()}/1d/1min.json",
            {},
            on_retry=_on_retry,
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
        if on_progress:
            total_days = (end - start).days + 1
            done_days = (current - start).days + 1
            on_progress(ProgressEvent(
                data_type="heart_rate_intraday",
                status="progress",
                current_date=current,
                pct=done_days / total_days if total_days > 0 else 1.0,
                message=None,
            ))
        current += timedelta(days=1)
    return results


def _fetch_hrv(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/hrv/date/{start}/{end}.json", start, end, 30, "hrv", dtype="hrv", on_progress=on_progress)


def _fetch_spo2(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    if on_progress:
        on_progress(ProgressEvent(data_type="spo2", status="progress", current_date=None, pct=None, message="fetching..."))
    resp = _request_with_retry(client, f"/1/user/-/spo2/date/{start.isoformat()}/{end.isoformat()}.json", {})
    data = resp.json()
    if isinstance(data, list):
        return data
    return [data] if data else []


def _fetch_breathing_rate(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/br/date/{start}/{end}.json", start, end, 30, "br", dtype="breathing_rate", on_progress=on_progress)


def _fetch_skin_temperature(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/temp/skin/date/{start}/{end}.json", start, end, 30, "tempSkin", dtype="skin_temperature", on_progress=on_progress)


def _fetch_weight(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    return _fetch_chunked(client, "/1/user/-/body/log/weight/date/{start}/{end}.json", start, end, 30, "weight", dtype="weight", on_progress=on_progress)


def _fetch_daily_summary(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    resources = ["steps", "calories", "distance", "floors", "minutesSedentary",
                 "minutesLightlyActive", "minutesFairlyActive", "minutesVeryActive"]
    by_date: dict[str, dict] = {}
    total_resources = len(resources) + 1
    for ri, resource in enumerate(resources):
        if on_progress:
            on_progress(ProgressEvent(
                data_type="daily_summary", status="progress",
                current_date=None, pct=ri / total_resources,
                message=f"fetching {resource}...",
            ))
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

    if on_progress:
        on_progress(ProgressEvent(
            data_type="daily_summary", status="progress",
            current_date=None, pct=len(resources) / total_resources,
            message="fetching activeZoneMinutes...",
        ))
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


def _fetch_nutrition(client: httpx.Client, start: date, end: date, on_progress: Callable[[ProgressEvent], None] | None = None) -> list[dict]:
    by_date: dict[str, dict] = {}
    resources = ["caloriesIn", "water"]
    for ri, resource in enumerate(resources):
        if on_progress:
            on_progress(ProgressEvent(
                data_type="nutrition", status="progress",
                current_date=None, pct=ri / len(resources),
                message=f"fetching {resource}...",
            ))
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
                        on_progress=self._on_progress,
                    )
                elif dtype == "activity_tcx":
                    items = _fetch_activity_tcx(
                        self._client, start, self._end,
                        self._output_dir, checkpoint, cp_path,
                        on_progress=self._on_progress,
                    )
                else:
                    fetch_fn = _FETCH_FUNCTIONS[dtype]
                    items = fetch_fn(self._client, start, self._end, on_progress=self._on_progress)
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
