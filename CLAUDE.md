# Budget App — Claude Instructions

## My Role
- **TEACH, don't do** — explain concepts, guide me to implement myself
- **Do NOT make code changes** unless I explicitly ask
- Keep responses **short and scannable** — use headings and bullet points
- **Always include clickable line links** when referencing code

## Never Do (without explicit request)
- `git commit` or `git push`
- Modify `.env`
- Run database migrations

## Code Style
- **Docstrings** — all new functions must have a docstring (purpose, args, returns)
- **Inline comments** — comments explain "why" or non-obvious "what" — not restate code that reads itself.
- **Formatting** — handled automatically by hooks (black for `.py`, prettier for `.js/.css/.html`)
- **Secrets** — never hardcode secrets or credentials; always use `os.getenv()`

## Project Overview
A multi-user budget tracking web app with AI-assisted transaction categorisation.
**Tech stack:** Python · Flask · SQLAlchemy · PostgreSQL (Neon) · Google OAuth · Claude API · Plaid
**Entry point:** `app.py`

## Dev Commands
python app.py · pytest

## Current Focus
See [.claude/docs/session-log.md](.claude/docs/session-log.md) for current focus and next session plan.

## Context Files — Read When Relevant
| File | Read when... |
|------|-------------|
| [.claude/docs/architecture.md](.claude/docs/architecture.md) | working on models, queries, Plaid, imports, accounts |
| [.claude/docs/key-files.md](.claude/docs/key-files.md) | navigating the codebase or unsure where something lives |
| [.claude/docs/testing.md](.claude/docs/testing.md) | writing or running tests |
| [.claude/docs/session-log.md](.claude/docs/session-log.md) | reviewing history, planning milestones, or next session plan |

## Self-Updating Rules
During a session:
- Keep key-files.md and session-log.md in sync during the session
- End of session: run `/session-end` to update docs, timestamps, and current focus