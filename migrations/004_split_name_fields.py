"""
Migration 004: Split name → first_name + last_name

- Renames the existing `name` column to `first_name`
- Fills any NULL first_name with 'User' (safety for old records)
- Adds new nullable `last_name` column
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db


def upgrade():
    print("🔄 Migration 004: Splitting name → first_name + last_name...")
    with db.engine.connect() as conn:
        # Step 1: Rename name → first_name
        conn.execute(db.text('ALTER TABLE "user" RENAME COLUMN name TO first_name'))
        print("  ✅ Renamed 'name' to 'first_name'")

        # Step 2: Fill any NULLs before applying constraints
        conn.execute(db.text("UPDATE \"user\" SET first_name = 'User' WHERE first_name IS NULL"))
        print("  ✅ Filled NULL first_name values with 'User'")

        # Step 3: Add last_name column
        conn.execute(db.text('ALTER TABLE "user" ADD COLUMN last_name VARCHAR(100)'))
        print("  ✅ Added 'last_name' column")

        conn.commit()
    print("✅ Migration 004 complete.")


def downgrade():
    print("🔄 Downgrade 004: Reverting first_name → name, dropping last_name...")
    with db.engine.connect() as conn:
        conn.execute(db.text('ALTER TABLE "user" DROP COLUMN last_name'))
        conn.execute(db.text('ALTER TABLE "user" RENAME COLUMN first_name TO name'))
        conn.commit()
    print("✅ Downgrade 004 complete.")


def verify():
    print("📊 Verifying migration 004...")
    with db.engine.connect() as conn:
        result = conn.execute(db.text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = 'user'
            AND column_name IN ('first_name', 'last_name', 'name')
        """))
        cols = [row[0] for row in result]
        print(f"  Columns found: {cols}")
        assert 'first_name' in cols, "❌ first_name column missing"
        assert 'last_name' in cols, "❌ last_name column missing"
        assert 'name' not in cols, "❌ old 'name' column still exists"
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
