# seed_data.py
"""
Seed the database with default categories.
Run this script whenever you drop/recreate the database.

Usage:
    python seed_data.py
"""

from app import app, db
from models import Category

# Default categories here
default_categories = [
        "Groceries",
        "Restaurants",
        "Transport",
        "Bills & Utilities",
        "Shopping",
        "Entertainment",
        "Health & Fitness",
        "Income",
        "Savings & Investments",
        "Transfer",
        "Other"
    ]


def seed_user_categories(user_id):
    """Create default categories for a specific user"""

    for category_name in default_categories:
        category = Category(name=category_name, user_id=user_id)
        db.session.add(category)
    db.session.commit()
    print(f"Seeded {len(default_categories)} categories for user {user_id}")
