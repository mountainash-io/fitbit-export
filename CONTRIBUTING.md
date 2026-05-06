# Contributing to fitbit-export

Thank you for your interest in contributing! This guide covers the basics.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Please read it before participating.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Follow [INSTALL.md](INSTALL.md) for development setup
4. Create a feature branch (`git checkout -b feature/your-feature`)
5. Make your changes
6. Open a pull request targeting `develop`

## Development Setup

```bash
uv venv && uv pip install -e ".[dev]"
```

## Pull Request Process

1. PRs target `develop`, not `main`
2. Update `CHANGELOG.md` if your change is user-facing
3. Update `INSTALL.md` if install steps changed
4. Ensure tests pass: `uv run pytest`
