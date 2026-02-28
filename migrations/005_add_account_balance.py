"""
Migration 005: Add account_balance table

Creates account_balance to store historical balance snapshots per PlaidAccount.
Each sync appends a new row — balances are never overwritten, enabling history.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db


def upgrade():
    print("🔄 Migration 005: Creating account_balance table...")
    with db.engine.connect() as conn:
        conn.execute(db.text("""
            CREATE TABLE account_balance (
                id SERIAL PRIMARY KEY,
                plaid_account_id INTEGER NOT NULL REFERENCES plaid_account(id) ON DELETE CASCADE,
                current_balance NUMERIC(12,2) NOT NULL,
                available_balance NUMERIC(12,2),
                currency VARCHAR(10) NOT NULL DEFAULT 'GBP',
                recorded_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        print("  ✅ Created account_balance table")

        conn.execute(db.text(
            "CREATE INDEX ix_account_balance_plaid_account_id ON account_balance(plaid_account_id)"
        ))
        conn.execute(db.text(
            "CREATE INDEX ix_account_balance_recorded_at ON account_balance(recorded_at DESC)"
        ))
        print("  ✅ Created indexes")

        conn.commit()
    print("✅ Migration 005 complete.")


def downgrade():
    print("🔄 Downgrade 005: Dropping account_balance table...")
    with db.engine.connect() as conn:
        conn.execute(db.text("DROP TABLE IF EXISTS account_balance"))
        conn.commit()
    print("✅ Downgrade 005 complete.")


def verify():
    print("📊 Verifying migration 005...")
    with db.engine.connect() as conn:
        result = conn.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'account_balance'
        """))
        cols = [row[0] for row in result]
        print(f"  Columns found: {cols}")
        assert 'id' in cols, "❌ id column missing"
        assert 'plaid_account_id' in cols, "❌ plaid_account_id column missing"
        assert 'current_balance' in cols, "❌ current_balance column missing"
        assert 'available_balance' in cols, "❌ available_balance column missing"
        assert 'currency' in cols, "❌ currency column missing"
        assert 'recorded_at' in cols, "❌ recorded_at column missing"
    print("✅ Verification passed.")


if __name__ == '__main__':
    with app.app_context():
        if '--downgrade' in sys.argv:
            downgrade()
        elif '--verify' in sys.argv:
            verify()
        else:
            upgrade()
            verify()
