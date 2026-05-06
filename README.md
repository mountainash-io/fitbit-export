# fitbit-export

**Extract all your Fitbit data before the API shuts down in September 2026.**

Fitbit accounts stop working on May 19, 2026. Data is permanently deleted after July 15, 2026. This tool extracts everything from your account via the Fitbit API and saves it as raw JSON files.

## Quick Start

```bash
git clone https://github.com/mountainash-io/fitbit-export.git
cd fitbit-export
pip install .
fitbit-export
```

A browser window will open for you to log into Fitbit and authorize the export. Once authorized, the tool extracts all your data automatically.

## What Gets Exported

| Data Type | Description |
|-----------|-------------|
| activities | All logged exercises and workouts |
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

## Multiple Users (Family Accounts)

```bash
# First user -- opens browser
fitbit-export

# Add another user
fitbit-export --add-user

# List all authenticated users
fitbit-export --list-users

# Export all users (default)
fitbit-export

# Export specific user
fitbit-export --user 26CBRV
```

## Resuming Interrupted Exports

The tool saves progress as it goes. If it gets interrupted (rate limits, crashes, laptop sleep), just run it again -- it picks up where it left off.

Intraday heart rate data is the largest dataset and can take many hours for long-time users. The tool will resume at the exact day it stopped.

## Options

```
--start DATE     Start date (default: 2010-01-01)
--end DATE       End date (default: today)
--output DIR     Output directory (default: ./fitbit-export-output)
--types TYPES    Comma-separated data types to export
--add-user       Add a new Fitbit account
--list-users     List authenticated accounts
--user ID        Export only this user
```

## Using Your Own Fitbit App

By default, this tool uses a shared Fitbit developer app. If you prefer to use your own:

1. Go to https://dev.fitbit.com/apps/new
2. Register an app (OAuth 2.0 Application Type: **Personal**)
3. Set Redirect URL to `http://localhost:8080/callback`
4. Set environment variables:

```bash
export FITBIT_CLIENT_ID=your_client_id
export FITBIT_CLIENT_SECRET=your_client_secret
fitbit-export
```

## Output Structure

```
fitbit-export-output/
+-- 26CBRV-nathaniel/
    +-- raw/
    |   +-- activities.json
    |   +-- sleep.json
    |   +-- heart_rate_summary.json
    |   +-- heart_rate_intraday/
    |   |   +-- 2013.json
    |   |   +-- 2014.json
    |   |   +-- ...
    |   +-- hrv.json
    |   +-- spo2.json
    |   +-- breathing_rate.json
    |   +-- skin_temperature.json
    |   +-- weight.json
    |   +-- daily_summary.json
    |   +-- nutrition.json
    +-- .checkpoint.json
```

## Requirements

- Python 3.11+
- A Fitbit account (before May 19, 2026)

## License

MIT
