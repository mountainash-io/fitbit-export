# fitbit-export

**Extract all your Fitbit data before the API shuts down.**

Google is phasing out Fitbit accounts and the legacy Fitbit Web API:

| Date | What happens | What you need to do |
|------|-------------|---------------------|
| **May 19, 2026** | Fitbit-only accounts stop working | Migrate to a Google account to keep access |
| **July 15, 2026** | Data for non-migrated accounts deleted from servers | If you haven't migrated, your data is gone |
| **September 2026** | Fitbit Web API shut down permanently | **Run this tool before then — after this date, no one can extract Fitbit data via the API** |

If you've already migrated to a Google account, your data is safe until September. But the API shutdown is the hard deadline for everyone.

This repo is both a **Python CLI tool** you can run directly, and an **AI agent skill** that guides you through the export interactively on Claude Code, Cursor, Gemini CLI, or Codex.

## Install as AI Agent Skill

The skill walks you through authentication, selects data types, handles rate limits, and resumes interrupted exports.

### Claude Code

```bash
/plugin marketplace add mountainash-io/fitbit-export
/plugin install fitbit-export@fitbit-export-marketplace
```

Then invoke: `/fitbit-export`

### Cursor

```
/add-plugin fitbit-export@https://github.com/mountainash-io/fitbit-export
```

### Gemini CLI

```bash
gemini extensions install mountainash-io/fitbit-export
```

### Codex

```bash
codex plugin marketplace add mountainash-io/fitbit-export
```

Then open `/plugins` in Codex and install `fitbit-export`.

See [INSTALL.md](INSTALL.md) for local clone installs and verification steps.

## Install as Python CLI

No AI agent required — run the tool directly from the command line.

```bash
git clone https://github.com/mountainash-io/fitbit-export.git
cd fitbit-export
uv pip install .
fitbit-export
```

A browser window will open for Fitbit authorization. Once authorized, the tool extracts all your data automatically.

## What Gets Exported

| Data Type | Description |
|-----------|-------------|
| activities | All logged exercises and workouts |
| activity_tcx | GPS tracks (TCX files) for manually-logged activities |
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
fitbit-export add-user

# Add another user
fitbit-export add-user

# List all authenticated users
fitbit-export list-users

# Export all users
fitbit-export export

# Export specific user
fitbit-export export --user 26CBRV
```

## Resuming Interrupted Exports

The tool saves progress as it goes. If it gets interrupted (rate limits, crashes, laptop sleep), just run it again -- it picks up where it left off.

Intraday heart rate data is the largest dataset and can take many hours for long-time users. The tool will resume at the exact day it stopped.

## CLI Commands

```
fitbit-export                Show dashboard and choose an action
fitbit-export export         Run the data export
fitbit-export add-user       Add a new Fitbit account
fitbit-export list-users     List authenticated accounts
fitbit-export status         Show export progress
```

## Export Options

```
fitbit-export export [OPTIONS]

--start DATE     Start date (default: 2010-01-01)
--end DATE       End date (default: today)
--output DIR     Output directory (default: ~/fitbit-export-output)
--types TYPES    Comma-separated data types to export
--user ID        Export only this user
```

## Output Structure

```
fitbit-export-output/
+-- 26CBRV-nathaniel/
    +-- raw/
    |   +-- activities.json
    |   +-- activity_tcx/
    |   |   +-- 12345.tcx
    |   |   +-- 67890.tcx
    |   |   +-- ...
    |   +-- activity_tcx.json
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
- A Fitbit account with data (before the API shuts down in September 2026)

## License

MIT
