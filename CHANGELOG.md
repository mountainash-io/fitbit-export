# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-07

### Changed

- CLI rewritten with Typer subcommands: `export`, `add-user`, `list-users`, `status`
- Running `fitbit-export` with no arguments now shows a dashboard and action menu instead of immediately exporting
- Default output directory changed from `./fitbit-export-output` to `~/fitbit-export-output`
- Progress display uses Rich progress bars per data type instead of plain text
- All documentation updated to use `uv` instead of `pip`

### Added

- Dashboard showing per-user export progress and per-type status
- Rich progress bars with ETA for long-running extractions (heart_rate_intraday)
- `fitbit-export status` command for read-only dashboard view
- `.gitignore` entry for `fitbit-export-output/`

### Removed

- Old `--add-user`, `--list-users` top-level flags (replaced by subcommands)

## [0.1.0] - 2026-05-06

### Added

- OAuth2 + PKCE authentication with built-in client_id (no developer app registration needed)
- 12 data type extractors: activities, activity_tcx, sleep, heart_rate_summary, heart_rate_intraday, hrv, spo2, breathing_rate, skin_temperature, weight, daily_summary, nutrition
- GPS/TCX activity file download for manually-logged activities
- Checkpoint/resume system for interrupted exports
- Rate limit handling (150 requests/hour) with automatic retry
- Multi-user support for family account exports
- Claude Code plugin with interactive `/fitbit-export` skill
- Cross-platform plugin packaging: Cursor, Gemini CLI, Codex
- Platform install docs (INSTALL.md) with marketplace/registry commands

[0.2.0]: https://github.com/mountainash-io/fitbit-export/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mountainash-io/fitbit-export/releases/tag/v0.1.0
