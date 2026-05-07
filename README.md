# fitbit-export

**Python CLI to extract all your Fitbit data before the API shuts down.**

Google is phasing out Fitbit accounts and the legacy Fitbit Web API:

| Date | What happens |
|------|-------------|
| **May 19, 2026** | Fitbit-only accounts stop working — migrate to Google account |
| **July 15, 2026** | Data for non-migrated accounts deleted from servers |
| **September 2026** | Fitbit Web API shut down permanently — no more API access |

## Quick Start

```bash
# Install and run (requires uv)
uvx --from git+https://github.com/mountainash-io/fitbit-export fitbit-export --help

# Or clone and install locally
git clone https://github.com/mountainash-io/fitbit-export.git
cd fitbit-export
uv pip install .
fitbit-export --help
```

## AI Agent Skill

An LLM skill that guides you through the export interactively is available as a separate repo. Install it to Claude Code, Cursor, Codex, and 50+ other agents:

```bash
npx skills add mountainash-io/fitbit-export-skill
```

See [fitbit-export-skill](https://github.com/mountainash-io/fitbit-export-skill) for details.

## What Gets Exported

| Data Type | Description |
|-----------|-------------|
| activities | All logged exercises and workouts |
| activity_tcx | GPS tracks (TCX files) for activities |
| sleep | Sleep sessions with stage data (deep, light, REM, awake) |
| heart_rate_summary | Daily resting heart rate and HR zones |
| heart_rate_intraday | Minute-by-minute heart rate (largest dataset) |
| hrv | Heart rate variability |
| spo2 | Blood oxygen levels |
| breathing_rate | Nightly breathing rate |
| skin_temperature | Nightly skin temperature deviation |
| weight | Weight, BMI, and body fat logs |
| daily_summary | Daily steps, calories, distance, floors, active minutes |
| nutrition | Food and water logs |

## CLI Commands

```
fitbit-export --help         Show all commands and options
fitbit-export export --all   Export all data types
fitbit-export export --types spo2,weight,sleep
fitbit-export add-user       Add a new Fitbit account (opens browser)
fitbit-export list-users     List authenticated accounts with progress
fitbit-export status         Show export progress dashboard
fitbit-export config         View or set configuration
fitbit-export refresh        Refresh OAuth tokens
```

## Export Options

```
fitbit-export export [OPTIONS]

--all            Export all data types (required unless --types given)
--types TYPES    Comma-separated data types to export
--user ID        Export only this user
--start DATE     Start date (default: 2010-01-01)
--end DATE       End date (default: today)
--output DIR     Output directory (default: ~/fitbit-export-output)
```

## Multiple Users (Family Accounts)

```bash
fitbit-export add-user       # First user — opens browser
fitbit-export add-user       # Log out of fitbit.com, then add another
fitbit-export list-users     # List all authenticated users
fitbit-export export --all   # Export all users
fitbit-export export --all --user 26CBRV  # Export specific user
```

## Resuming Interrupted Exports

The tool saves progress incrementally. If interrupted (rate limits, crashes, laptop sleep), run again — it picks up where it left off.

Fitbit allows 150 API requests per hour. Intraday heart rate is the largest dataset (1 request per day of data) and can take many sessions for long-time users.

## Output Structure

```
~/fitbit-export-output/
└── 26CBRV-nathaniel/
    ├── raw/
    │   ├── activities.json
    │   ├── activity_tcx/
    │   │   ├── 12345.tcx
    │   │   └── ...
    │   ├── sleep.json
    │   ├── heart_rate_summary.json
    │   ├── heart_rate_intraday/
    │   │   ├── 2013.json
    │   │   └── ...
    │   ├── hrv.json
    │   ├── spo2.json
    │   ├── breathing_rate.json
    │   ├── skin_temperature.json
    │   ├── weight.json
    │   ├── daily_summary.json
    │   └── nutrition.json
    └── .checkpoint.json
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- A Fitbit account with data

## License

MIT
