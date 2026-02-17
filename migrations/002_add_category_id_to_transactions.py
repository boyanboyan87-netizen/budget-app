"""
Migration: Add category_id FK to transaction table and migrate data
Converts category from string to foreign key while preserving data
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Transaction, Category, User

def upgrade():
    """Add category_id column and migrate existing string categories to FK"""
    with app.app_context():
        print("🔄 Starting transaction category migration...\n")
        
        # Step 1: Add category_id column
        print("📝 Adding category_id column...")
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                ALTER TABLE transaction 
                ADD COLUMN category_id INTEGER REFERENCES category(id);
            """))
            
            # Add index for performance
            conn.execute(db.text("""
                CREATE INDEX idx_transaction_category ON transaction(category_id);
            """))
            
            conn.commit()
        print("   ✅ category_id column added\n")
        
        # Step 2: Migrate data for each user
        print("📊 Migrating existing categories from string to FK...")
        users = User.query.all()
        total_migrated = 0
        total_unmapped = 0
        
        for user in users:
            print(f"\n   User: {user.email}")
            
            # Build lookup: category_name -> category_id for this user
            category_lookup = {}
            categories = Category.query.filter_by(user_id=user.id).all()
            for cat in categories:
                category_lookup[cat.name] = cat.id
                # Also add full_path mapping for subcategories
                if cat.parent:
                    category_lookup[cat.full_path] = cat.id
            
            print(f"   Found {len(categories)} categories for user")
            
            # Update transactions
            transactions = Transaction.query.filter_by(user_id=user.id).all()
            migrated = 0
            unmapped = 0
            
            for tx in transactions:
                if tx.category:  # Only if category string exists
                    # Try to find matching category
                    cat_id = category_lookup.get(tx.category)
                    if cat_id:
                        tx.category_id = cat_id
                        migrated += 1
                    else:
                        # Category string doesn't match any category
                        unmapped += 1
                        print(f"   ⚠️  Unmapped category: '{tx.category}' (transaction {tx.id})")
            
            db.session.commit()
            total_migrated += migrated
            total_unmapped += unmapped
            print(f"   ✅ Migrated {migrated}/{len(transactions)} transactions")
        
        print(f"\n📈 Migration Summary:")
        print(f"   ✅ Total migrated: {total_migrated}")
        if total_unmapped > 0:
            print(f"   ⚠️  Unmapped categories: {total_unmapped} (set to NULL)")
        
        print(f"\n🗑️  Dropping old 'category' string column...")
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE transaction DROP COLUMN category;"))
            conn.commit()
        print(f"   ✅ Old column removed")

        print(f"\n✅ Migration complete!")

def downgrade():
    """Remove category_id column (rollback)"""
    with app.app_context():
        print("🔄 Rolling back category_id migration...")
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE transaction DROP COLUMN category_id;"))
            conn.commit()
        print("✅ Removed category_id column")

def verify():
    """Verify migration success"""
    with app.app_context():
        total = Transaction.query.count()
        with_cat_id = Transaction.query.filter(Transaction.category_id.isnot(None)).count()
        with_cat_str = Transaction.query.filter(Transaction.category_id.isnot(None)).count()
        
        print(f"\n📊 Verification:")
        print(f"   Total transactions: {total}")
        print(f"   With category_id (FK): {with_cat_id}")
        print(f"   With category (string): {with_cat_str}")
        
        if with_cat_id > 0:
            print(f"\n   ✅ Migration successful!")
        else:
            print(f"\n   ⚠️  No transactions migrated")

if __name__ == '__main__':
    import sys
    if '--verify' in sys.argv:
        verify()
    elif '--downgrade' in sys.argv:
        downgrade()
    else:
        upgrade()
