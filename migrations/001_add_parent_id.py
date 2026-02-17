"""
Migration: Add parent_id column to category table
This enables hierarchical categories (parent-child relationships)
"""
import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

def upgrade():
    """Add parent_id column to existing category table"""
    with app.app_context():
        print("🔄 Adding parent_id column to category table...")
        
        # Add parent_id column (nullable, so safe for existing data)
        with db.engine.connect() as conn:
            conn.execute(db.text("""
                ALTER TABLE category 
                ADD COLUMN parent_id INTEGER REFERENCES category(id);
            """))
            
            # Add index for performance
            conn.execute(db.text("""
                CREATE INDEX idx_category_parent ON category(parent_id);
            """))
            
            conn.commit()
        
        print("✅ parent_id column added successfully")

def downgrade():
    """Remove parent_id column (rollback)"""
    with app.app_context():
        with db.engine.connect() as conn:
            conn.execute(db.text("ALTER TABLE category DROP COLUMN parent_id;"))
            conn.commit()
        print("✅ Removed parent_id column")

if __name__ == '__main__':
    upgrade()
