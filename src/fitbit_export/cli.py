from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from fitbit_export.auth import FitbitAuth
from fitbit_export.extract import FitbitExtractor, DATA_TYPES
from fitbit_export.models import ProgressEvent


def _on_progress(evt: ProgressEvent) -> None:
    if evt.status == "starting":
        print(f"  > {evt.data_type}...")
    elif evt.status == "skipped":
        print(f"  - {evt.data_type} (already done)")
    elif evt.status == "complete":
        print(f"  + {evt.data_type} -- {evt.message}")
    elif evt.status == "error":
        print(f"  ! {evt.data_type} -- {evt.message}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract all your Fitbit data before the API shuts down",
    )
    parser.add_argument("--add-user", action="store_true", help="Add a new Fitbit account")
    parser.add_argument("--list-users", action="store_true", help="List authenticated users")
    parser.add_argument("--user", type=str, help="Export specific user (Fitbit ID)")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2010, 1, 1), help="Start date (default: 2010-01-01)")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(), help="End date (default: today)")
    parser.add_argument("--output", type=Path, default=Path("fitbit-export-output"), help="Output directory")
    parser.add_argument("--types", type=str, default=None, help=f"Comma-separated types: {','.join(DATA_TYPES)}")
    args = parser.parse_args()

    print("Fitbit Export -- https://github.com/mountainash-io/fitbit-export")
    print("Fitbit API shuts down September 2026. Export your data now.")
    print()

    auth = FitbitAuth()

    if args.list_users:
        users = auth.list_users()
        if not users:
            print("No authenticated users. Run: fitbit-export --add-user")
        else:
            print("Authenticated users:")
            for u in users:
                print(f"  * {u['display_name']} ({u['user_id']})")
        return

    if args.add_user:
        auth.add_user()
        return

    if args.user:
        users = [auth.authenticate(args.user)]
    else:
        users = auth.authenticate_all()

    data_types = args.types.split(",") if args.types else None

    for user in users:
        user_dir = args.output / f"{user.user_id}-{user.display_name.split()[0].lower()}"
        print(f"Exporting {user.display_name} ({user.user_id})...")
        print(f"  Date range: {args.start} -> {args.end}")
        print(f"  Output: {user_dir.resolve()}")

        extractor = FitbitExtractor(
            client=user.client,
            output_dir=user_dir,
            start=args.start,
            end=args.end,
            on_progress=_on_progress,
        )
        result = extractor.run(data_types=data_types)

        print()
        print(f"  Done in {result.duration_seconds:.1f}s")
        if result.failed:
            print(f"  Failed: {', '.join(result.failed.keys())}")
            remaining = [k for k in result.failed if "429" in result.failed[k] or "retry" in result.failed[k].lower()]
            if remaining:
                print(f"  Rate limited types -- run again to resume: {', '.join(remaining)}")
        for dtype, count in result.record_counts.items():
            print(f"    {dtype}: {count} records")
        print()
        user.client.close()
