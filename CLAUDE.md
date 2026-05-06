# fitbit-export

Standalone tool to extract all Fitbit data before the API shuts down in September 2026.

## Quick Reference

- **Language:** Python 3.11+
- **Dependencies:** httpx only
- **Auth:** OAuth2 + PKCE with built-in client_id (no secret needed)
- **Entry point:** `fitbit-export` CLI or `python -m fitbit_export`
- **Tokens:** `~/.fitbit-export/tokens-{userId}.json`
- **Output:** `fitbit-export-output/{userId}-{name}/raw/`

## Running

```bash
uv venv && uv pip install -e .
fitbit-export              # auth + extract all users
fitbit-export --add-user   # add another Fitbit account
fitbit-export --list-users # show authenticated users
```

## Data Types (12)

activities, activity_tcx, sleep, heart_rate_summary, heart_rate_intraday,
hrv, spo2, breathing_rate, skin_temperature, weight, daily_summary, nutrition

## Rate Limits

Fitbit allows 150 requests/hour. Most data types complete quickly. Intraday HR
is 1 request per day of data — a 13-year account takes ~32 hours across multiple
runs. The checkpoint system resumes automatically.
