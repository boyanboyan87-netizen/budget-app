"""
Migration: Add Plaid integration tables
Creates plaid_item and plaid_account tables, and adds plaid_transaction_id
to the transaction table for deduplication.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db


def upgrade():
    """Create plaid_item, plaid_account tables and add plaid_transaction_id to transaction"""
    with app.app_context():
        print("🔄 Starting Plaid tables migration...\n")

        with db.engine.connect() as conn:

            # Step 1: plaid_item — one row per linked bank per user
            print("📝 Creating plaid_item table...")
            conn.execute(db.text("""
                CREATE TABLE plaid_item (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    access_token VARCHAR(200) NOT NULL,
                    item_id VARCHAR(100) NOT NULL,
                    institution_name VARCHAR(100),
                    cursor VARCHAR(200),
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_synced_at TIMESTAMP
                );
            """))
            print("   ✅ plaid_item table created\n")

            # Step 2: plaid_account — one row per account within a linked bank
            print("📝 Creating plaid_account table...")
            conn.execute(db.text("""
                CREATE TABLE plaid_account (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    item_id INTEGER NOT NULL REFERENCES plaid_item(id),
                    plaid_account_id VARCHAR(100) NOT NULL,
                    name VARCHAR(100),
                    mask VARCHAR(10),
                    account_type VARCHAR(50)
                );
            """))
            print("   ✅ plaid_account table created\n")

            # Step 3: Add plaid_transaction_id to transaction for deduplication
            print("📝 Adding plaid_transaction_id column to transaction...")
            conn.execute(db.text("""
                ALTER TABLE transaction
                ADD COLUMN plaid_transaction_id VARCHAR(100);
            """))
            print("   ✅ plaid_transaction_id column added\n")

            # Step 4: Unique partial index — prevents duplicate imports
            print("📝 Creating deduplication index...")
            conn.execute(db.text("""
                CREATE UNIQUE INDEX idx_plaid_tx_user
                ON transaction(user_id, plaid_transaction_id)
                WHERE plaid_transaction_id IS NOT NULL;
            """))
            print("   ✅ Index created\n")

            conn.commit()

        print("✅ Migration complete!")


def downgrade():
    """Remove Plaid tables and column (rollback)"""
    with app.app_context():
        print("🔄 Rolling back Plaid tables migration...")
        with db.engine.connect() as conn:
            conn.execute(db.text("DROP INDEX IF EXISTS idx_plaid_tx_user;"))
            conn.execute(db.text("ALTER TABLE transaction DROP COLUMN IF EXISTS plaid_transaction_id;"))
            conn.execute(db.text("DROP TABLE IF EXISTS plaid_account;"))
            conn.execute(db.text("DROP TABLE IF EXISTS plaid_item;"))
            conn.commit()
        print("✅ Rollback complete")


def verify():
    """Verify migration success"""
    with app.app_context():
        with db.engine.connect() as conn:
            # Check tables exist
            result = conn.execute(db.text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('plaid_item', 'plaid_account');
            """))
            tables = [row[0] for row in result]

            # Check column exists
            result = conn.execute(db.text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'transaction'
                AND column_name = 'plaid_transaction_id';
            """))
            column = result.fetchone()

        print("\n📊 Verification:")
        print(f"   plaid_item table:    {'✅' if 'plaid_item' in tables else '❌'}")
        print(f"   plaid_account table: {'✅' if 'plaid_account' in tables else '❌'}")
        print(f"   plaid_transaction_id column: {'✅' if column else '❌'}")


if __name__ == '__main__':
    if '--verify' in sys.argv:
        verify()
    elif '--downgrade' in sys.argv:
        downgrade()
    else:
        upgrade()
