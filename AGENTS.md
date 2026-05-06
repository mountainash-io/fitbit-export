# fitbit-export

Extract all your Fitbit data before the API shuts down (September 2026).

## Project Context

fitbit-export is a Python CLI tool and cross-platform AI plugin that authenticates with the Fitbit API via OAuth2+PKCE, extracts 12 data types to raw JSON, and handles rate limiting with checkpoint/resume. It supports multiple Fitbit accounts for family exports.

## Skills

This plugin provides the following skills. Read the SKILL.md files listed to understand how to invoke each skill:

- skills/fitbit-export/SKILL.md

## Tool Name Mapping

Skills use Claude Code tool names. Platform equivalents:

- `Bash` → your platform's shell/command tool
- `Read` → your platform's file-read tool
- `AskUserQuestion` → ask the user directly in conversation

## Quick Reference

- **Language:** Python 3.11+
- **Dependencies:** httpx only
- **Entry point:** `fitbit-export` CLI or `python -m fitbit_export`
- **Tokens:** `~/.fitbit-export/tokens-{userId}.json`
- **Output:** `fitbit-export-output/{userId}-{name}/raw/`

## Rate Limits

Fitbit allows 150 requests/hour. Most data types complete quickly. Intraday HR
is 1 request per day of data — a 13-year account takes ~32 hours across multiple
runs. The checkpoint system resumes automatically.
