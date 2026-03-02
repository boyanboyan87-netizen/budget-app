# Test Infrastructure

> Read this file when writing or running tests.

## Test Suite
- **20 tests, all passing**
- Run with: `pytest`

## Fixtures (`tests/conftest.py`)
- `app` — Flask test app with SQLite in-memory DB
- `client` — Flask test client
- `two_users` — two isolated users for data isolation tests

## Test Files
| File | Covers |
|------|--------|
| `tests/test_models.py` | `UserScopedQuery.for_user()` isolation |
| `tests/test_claude_client.py` | `clean_json_response()` + `categorise_with_claude()` |
| `tests/test_helpers.py` | Business logic helpers |
| `tests/test_parsers.py` | CSV parsing |

## Test Config
Pass this to `create_app()` for tests:
```python
{"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "test-secret"}
```
Connection pool is skipped in TESTING mode (SQLite doesn't support it).

## Test Fixtures Data
Sample CSVs in `tests/fixtures/`: amex (used by `test_parsers.py`), barclays, revolut (present but not currently used by any test).
