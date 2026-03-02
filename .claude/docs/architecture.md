# Architecture Decisions

> Read this file when working on: models, queries, Plaid integration, imports, accounts, auth, or testing config.

- **UserScopedQuery**: custom query class; use `.for_current_user()` in routes, explicit `user_id` in helpers
- **Category stored as FK** (`category_id` on Transaction) with a `@hybrid_property` string accessor — never filter on `Transaction.category` in SQLAlchemy queries, use `Transaction.category_id` instead
- **SocialAuth table** supports multiple OAuth providers (GitHub, Microsoft planned)
- Connection pool: 20 base + 30 overflow = 50 total (skipped in TESTING mode — SQLite doesn't support it)
- **Plaid**: `PlaidItem` = one bank connection (stores access_token + cursor); `Account` (account_type='automatic') = individual accounts within a bank. Transactions go into `transaction` table with `plaid_transaction_id` for dedup. Cursor-based sync.
- **Unified Account table**: `Account` replaces `PlaidAccount`. Two types: `'automatic'` (Plaid-synced) | `'manual'` (balance-only or with imports). Plaid-specific fields nullable. `status`: `'active'` | `'closed'` (soft-delete).
- **AccountBalance**: historical balance snapshots, references `account.id`. Updated on each Plaid sync. `Account.latest_balance` property returns most recent row.
- **transaction.account** string column still NOT NULL (legacy) — must be populated until cleanup step drops it. Set to `account.name` on import. `transaction.account_id` FK is the primary link.
- **invert_amounts** on Account (nullable Boolean): `True` = flip signs on import (expenses negative in file), `False` = keep as-is, `None` = unknown. Set when creating a manual account.
- **Amount convention**: positive = expense/debit, negative = income/credit (matches Plaid). Import parser applies `* -1` when `account.invert_amounts is True`.
- **Standard CSV format**: `Date` (DD/MM/YYYY), `Amount`, `Description`, `Reference` (optional). Parsed by `parse_standard_csv()` in `parsers.py`.
- **AccountBalance.currency removed** — currency lives only on `Account`. No longer on balance snapshots.
- **Account.plaid_item_id** — renamed from `item_id` for clarity.
- **Category dropdown selected check**: use `tx.category_obj.name == name` (not `tx.category == name`) — `tx.category` returns full_path which doesn't match short names.
- **App factory**: `create_app(config_override=None)` in `app.py`. Pass `{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-secret"}` for tests. `login_manager = LoginManager()` lives at module level (like `db`).
- **User model**: `first_name` (nullable=False) + `last_name` (nullable) — populated from Google OAuth `given_name`/`family_name`
