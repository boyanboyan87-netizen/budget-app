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
| `parsers.py` | CSV parsing (legacy — to be replaced by single standard parser) |
| `plaid_client.py` | Plaid SDK wrapper (link token, exchange, sync, balances) |
| `blueprints/plaid.py` | Plaid routes (link, exchange, sync, accounts) |
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
- **Plaid**: `PlaidItem` = one bank connection (stores access_token + cursor); `Account` (account_type='automatic') = individual accounts within a bank. Transactions go into `transaction` table with `plaid_transaction_id` for dedup. Cursor-based sync.
- **Unified Account table**: `Account` replaces `PlaidAccount`. Two types: `'automatic'` (Plaid-synced) | `'manual'` (balance-only or with imports). Plaid-specific fields nullable. `status`: `'active'` | `'closed'` (soft-delete).
- **AccountBalance**: historical balance snapshots, references `account.id`. Updated on each Plaid sync. `Account.latest_balance` property returns most recent row.
- **transaction.account** string column kept nullable (legacy) — `transaction.account_id` FK now the primary link. String column to be dropped once import flow is migrated.
- **invert_amounts** on Account (nullable Boolean): `True` = flip signs on import (expenses negative in file), `False` = keep as-is, `None` = unknown. Set when creating a manual account.
- **Amount convention**: positive = expense/debit, negative = income/credit (matches Plaid). Import parser applies `* -1` when `account.invert_amounts is True`.
- **App factory**: `create_app(config_override=None)` in `app.py`. Pass `{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-secret"}` for tests. `login_manager = LoginManager()` lives at module level (like `db`).
- **User model**: `first_name` (nullable=False) + `last_name` (nullable) — populated from Google OAuth `given_name`/`family_name`

## Test Infrastructure
- `tests/conftest.py` — `app`, `client`, `two_users` fixtures (SQLite in-memory)
- `tests/test_models.py` — `UserScopedQuery.for_user()` isolation tests
- `tests/test_claude_client.py` — `clean_json_response()` + `categorise_with_claude()` tests
- **19 tests, all passing**

## Current Focus
**Next session:** Manual Account UI

### Next session task list (in order):
1. **Manual Account UI** — create/view/edit manual accounts
   - Route + form: name, currency, `invert_amounts` question ("expenses shown as negative / positive / not sure")
   - Unified accounts view (automatic + manual together)
2. **Import flow** — upload transactions against a chosen manual account
   - Single standard CSV parser replacing Amex/Barclays/Revolut parsers
   - Template columns: `Date` (YYYY-MM-DD), `Amount`, `Description`, `Reference` (optional)
   - Apply `invert_amounts` sign flip at parse time
3. **Close/Remove Accounts** — soft-delete (`status='closed'`), decide: keep or cascade-delete transactions
4. **Cleanup** — drop `transaction.account` string column from DB once import flow fully migrated

## Completed Milestones
- Multi-user auth (Google OAuth)
- User data isolation (UserScopedQuery pattern)
- DB concurrency (connection pooling)
- Type hints across core files
- **Plaid integration** — connect banks, sync transactions, dedup, removed tx handling, per-item sync, account display
- **App factory refactor** — `create_app()` pattern, enables test config injection
- **User name split** — `name` → `first_name` + `last_name` (migration 004)
- **Test coverage** — 19 tests: isolation, JSON repair, parsers, helpers (all passing)
- **Unified Account table** — `PlaidAccount` replaced by `Account` (automatic/manual types), `AccountBalance` history, `account_id` FK on Transaction, `invert_amounts` field

## Self-Updating Rules
At the end of each session, or whenever the chat is compacted, update this file with:
- New architectural decisions or patterns introduced
- New preferences or workflow requests from me
- Completed milestones (move to "Completed" section)
- New current focus or next milestone
- Any "never do" rules added during the session

Keep this file **concise and current** — it's a living document, not a history log.
