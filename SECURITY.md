# Security Policy

## Scope

fitbit-export runs locally on your machine. It authenticates with the Fitbit API via OAuth2+PKCE and stores tokens at `~/.fitbit-export/tokens-{userId}.json`. It does not operate remote services or store data externally.

**Token security:** OAuth tokens are stored as plaintext JSON in your home directory. Protect access to `~/.fitbit-export/` accordingly.

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

**Email:** <nathaniel.ramm@discretedatascience.com>

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact

**Response commitment:** We will acknowledge your report within 7 days and work with you to understand and address the issue.

## Preferred Languages

We accept vulnerability reports in English.
