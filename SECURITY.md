# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ObserveCo, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email: security@observeco.app

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work with you to understand and address the issue.

## Security Model

ObserveCo is a **local-first** application:

- **No cloud data transmission** — All data stays on your machine
- **No telemetry by default** — Opt-in only
- **Local database** — SQLite stored in your application support directory
- **Dashboard is localhost-only** — Not exposed to the internet by default
- **API authentication** — Dashboard requires token authentication

## Data Privacy

- ObserveCo does not collect personal data
- Token usage data is stored locally only
- Agent configurations are stored locally only
- No data is sent to external servers without explicit opt-in

## Dependencies

We regularly audit dependencies for known vulnerabilities:

- FastAPI and Uvicorn for web server
- SQLAlchemy for database
- Pydantic for data validation

Run `pip audit` to check for known vulnerabilities in dependencies.

## Authentication

The dashboard uses token-based authentication:

- A secret token is generated on first run
- Stored in `~/.config/observeco/` (platform-dependent)
- Required for all API requests via `X-ObserveCo-Token` header
- Can be reset by deleting the auth config file

## Local Network Exposure

By default, the dashboard binds to `127.0.0.1` (localhost only).

If you bind to `0.0.0.0` for LAN access:
- Ensure your network is trusted
- Use a firewall to restrict access
- Consider using a reverse proxy with HTTPS

## Updates

Security updates will be released as patch versions (e.g., 0.2.1).

Subscribe to security advisories on GitHub.
