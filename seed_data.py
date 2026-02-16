# seed_data.py
"""
Seed the database with default categories.
Run this script whenever you drop/recreate the database.

Usage:
    python seed_data.py
"""

from app import app, db
from models import Category

def seed_categories():
    """Populate the Category table with default budget categories."""
    
    # Define your default categories here
    default_categories = [
        "Groceries",
        "Transport", 
        "Utilities",
        "Mortgage",
        "Entertainment",
        "Dining Out",
        "Healthcare",
        "Shopping",
        "Subscriptions",
        "Income",
        "Transfers",
        "Savings",
        "Other",
    ]
    
    # Need app context to access database
    with app.app_context():
        # Check if categories already exist (idempotency)
        existing = Category.query.count()
        if existing > 0:
            print(f"❌ ABORTED: Category table is not empty ({existing} categories found)")
            print(f"   This script only runs on an empty category table.")
            print(f"   If you want to reseed, first delete all categories manually.")
            return
        
        # Add each category to the database
        print(f"📝 Adding {len(default_categories)} categories...")
        for name in default_categories:
            category = Category(name=name)
            db.session.add(category)
        
        # Commit all at once
        db.session.commit()
        print(f"✅ Successfully seeded {len(default_categories)} categories!")
        
        # Show what was added
        print("\nCategories added:")
        for cat in Category.query.all():
            print(f"  - {cat.name}")

if __name__ == "__main__":
    # This runs when you execute: python seed_data.py
    seed_categories()
