# Key Files

> Read this file when navigating the codebase or unsure where something lives.

## Core App
> Entry points, data models, and shared business logic.

| File | Purpose |
|------|---------|
| `app.py` | Flask app factory (`create_app()`), routes |
| `models.py` | SQLAlchemy ORM + UserScopedQuery pattern |
| `helpers.py` | Business logic (accepts explicit user_id) |
| `auth.py` | Google OAuth login/logout |
| `parsers.py` | Standard CSV parser (`parse_standard_csv`) — DD/MM/YYYY |
| `claude_client.py` | Claude API integration for categorisation |
| `plaid_client.py` | Plaid SDK wrapper (link token, exchange, sync, balances) |
| `seed_data.py` | Default categories seeder |

## Blueprints
> Flask blueprints — each file owns a feature area's routes.

| File | Purpose |
|------|---------|
| `blueprints/main.py` | Main routes (home, dashboard) |
| `blueprints/transactions.py` | Transaction routes (upload, review, categorise) |
| `blueprints/accounts.py` | Manual account CRUD |
| `blueprints/plaid.py` | Plaid routes (link, exchange, sync, accounts) |

## Templates
> Jinja2 HTML templates. All extend `base.html`.

| File | Purpose |
|------|---------|
| `templates/base.html` | Base layout with navigation |
| `templates/home.html` | Dashboard |
| `templates/transactions.html` | Transaction list |
| `templates/upload.html` | CSV upload |
| `templates/accounts.html` | Account list |
| `templates/account_form.html` | Create/edit account |

## Tests
> pytest test suite. Run with `pytest`. Fixtures in `conftest.py`, sample CSVs in `fixtures/`.

| File | Purpose |
|------|---------|
| `tests/conftest.py` | pytest fixtures (app, client, two_users) |
| `tests/test_models.py` | Model + isolation tests |
| `tests/test_helpers.py` | Helper function tests |
| `tests/test_parsers.py` | CSV parser tests |
| `tests/test_claude_client.py` | Claude API client tests |
| `tests/fixtures/` | Sample CSV files for parser tests |

## Migrations
> Manual SQL migration scripts. Run in numeric order against the Neon DB.

| File | Purpose |
|------|---------|
| `migrations/` | Manual migration scripts (run in order) |

## Config / Claude
> Claude Code configuration, instructions, and project docs. Not part of the app itself.

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude instructions + project overview |
| `.claude/settings.json` | Claude Code hooks (PostToolUse: black + prettier) |
| `.claude/settings.local.json` | Local permissions (not committed) |
| `.claude/docs/architecture.md` | Architectural decisions |
| `.claude/docs/session-log.md` | Session history + current focus |
| `.claude/docs/testing.md` | Testing guidelines |
| `.claude/commands/session-end.md` | `/session-end` skill definition |
