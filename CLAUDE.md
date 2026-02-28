# Budget App — Claude Instructions

## My Role
- **TEACH, don't do** — explain concepts, guide me to implement myself
- **Do NOT make code changes** unless I explicitly ask
- Keep responses **short and scannable** — use headings and bullet points
- Ensure best practices are followed

## Never Do (without explicit request)
- `git commit` or `git push`
- Modify `.env`
- Run database migrations

## Project Overview
A multi-user budget tracking web app with AI-assisted transaction categorisation.

**Tech stack:** Python · Flask · SQLAlchemy · PostgreSQL (Neon) · Google OAuth · Claude API
**Entry point:** `app.py`

## Key Files
| File | Purpose |
|------|---------|
| `app.py` | Flask routes and app factory |
| `auth.py` | Google OAuth login/logout |
| `models.py` | SQLAlchemy ORM + UserScopedQuery pattern |
| `helpers.py` | Business logic (accepts explicit user_id) |
| `claude_client.py` | Claude API integration for categorisation |
| `parsers.py` | CSV parsing for Amex, Barclays, Revolut |
| `plaid_client.py` | Plaid SDK wrapper (link token, exchange, sync, balances) |
| `seed_data.py` | Default categories seeder |
| `migrations/` | Manual migration scripts |

## Dev Commands
```bash
python app.py   # run dev server
pytest          # run tests
```

## Architecture Decisions
- **UserScopedQuery**: custom query class; use `.for_current_user()` in routes, explicit `user_id` in helpers
- **Category stored as FK** (`category_id` on Transaction) with a `@hybrid_property` string accessor — never filter on `Transaction.category` in SQLAlchemy queries, use `Transaction.category_id` instead
- **SocialAuth table** supports multiple OAuth providers (GitHub, Microsoft planned)
- Connection pool: 20 base + 30 overflow = 50 total (skipped in TESTING mode — SQLite doesn't support it)
- **Plaid**: `PlaidItem` = one bank connection (stores access_token + cursor); `PlaidAccount` = individual accounts within a bank. Transactions go into the existing `transaction` table with `plaid_transaction_id` for dedup. Cursor-based sync via `/transactions/sync`.
- **transaction.account** is currently a string — planned refactor to a unified `Account` FK table supporting both Plaid and manual/CSV imports
- **App factory**: `create_app(config_override=None)` in `app.py`. Pass `{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-secret"}` for tests. `login_manager = LoginManager()` lives at module level (like `db`).
- **User model**: `first_name` (nullable=False) + `last_name` (nullable) — populated from Google OAuth `given_name`/`family_name`

## Test Infrastructure
- `tests/conftest.py` — `app`, `client`, `two_users` fixtures (SQLite in-memory)
- `tests/test_models.py` — `UserScopedQuery.for_user()` isolation tests
- `tests/test_claude_client.py` — `clean_json_response()` + `categorise_with_claude()` tests
- **19 tests, all passing**

## Current Focus
**Next session:** Account balances, unified Account table refactor, Blueprint refactor (split app.py)

## Completed Milestones
- Multi-user auth (Google OAuth)
- User data isolation (UserScopedQuery pattern)
- DB concurrency (connection pooling)
- Type hints across core files
- **Plaid integration** — connect banks, sync transactions, dedup, removed tx handling, per-item sync, account display
- **App factory refactor** — `create_app()` pattern, enables test config injection
- **User name split** — `name` → `first_name` + `last_name` (migration 004)
- **Test coverage** — 19 tests: isolation, JSON repair, parsers, helpers

## Self-Updating Rules
At the end of each session, or whenever the chat is compacted, update this file with:
- New architectural decisions or patterns introduced
- New preferences or workflow requests from me
- Completed milestones (move to "Completed" section)
- New current focus or next milestone
- Any "never do" rules added during the session

Keep this file **concise and current** — it's a living document, not a history log.
