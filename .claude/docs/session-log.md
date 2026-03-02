# Session Log

> Read this file when reviewing project history or planning the next session and milestone.

---

## Current Focus
> What we're working on next.

**Close/Remove Accounts + Cleanup**
1. Close/Remove Accounts — soft-delete (`status='closed'`), decide: keep or cascade-delete transactions
2. Cleanup — drop `transaction.account` string column from DB + model + `account=account_name` line in `helpers.py`
3. Remove any traces of Amex, Barclay & Revolut (old import functions)

---

## Road Map
> Discussed but not yet started.

_(nothing queued yet)_

---

## Completed
> Daily log of what has been done

(02/03/2026 00:12)
- **PostToolUse hook**  — auto-formats `.py` with black, `.js`/`.css` with prettier on every Claude file edit; configured in `.claude/settings.json`
- **CLAUDE.md restructure** — lean core file with on-demand context docs in `.claude/docs/`

28/02/2026
- **Unified Account table** — `PlaidAccount` replaced by `Account` (automatic/manual types), `AccountBalance` history, `account_id` FK on Transaction, `invert_amounts` field
- **Manual Account UI** — create/view/edit at `/accounts`, unified with Plaid accounts
- **DB cleanups** — `AccountBalance.currency` dropped; `Account.item_id` → `plaid_item_id`

26/02/2026
- **Import flow** — standard CSV parser (DD/MM/YYYY), account selection, `invert_amounts` sign flip
- **Test coverage** — 20 tests: isolation, JSON repair, parsers, helpers (all passing)
- **Test fix** — rewrote `test_parsers.py` for `parse_standard_csv`; 4 meaningful tests replacing 3 broken ones (16 → 20 total)

25/02/2026
- **Plaid integration** — connect banks, sync transactions, dedup, removed tx handling, per-item sync, account display

21/02/2026
- **App factory refactor** — `create_app()` pattern, enables test config injection
- **User name split** — `name` → `first_name` + `last_name` (migration 004)
- Multi-user auth (Google OAuth)
- User data isolation (UserScopedQuery pattern)
- DB concurrency (connection pooling)
- Type hints across core files


