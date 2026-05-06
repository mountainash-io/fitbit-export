# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.1.0]: https://github.com/mountainash-io/fitbit-export/releases/tag/v0.1.0
