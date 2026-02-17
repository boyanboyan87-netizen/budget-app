# seed_data.py
"""
Seed the database with default categories.
Run this script whenever you drop/recreate the database.

Usage:
    python seed_data.py
"""

from app import app, db
from models import Category

# Hierarchical category structure: Parent -> [Children]
hierarchical_categories = {
    "Groceries": ["Supermarket", "Local Shops", "Online Grocery"],
    "Restaurants": ["Fast Food", "Casual Dining", "Fine Dining", "Takeaway"],
    "Transport": ["Public Transport", "Fuel", "Parking", "Taxi/Uber", "Car Maintenance"],
    "Bills & Utilities": ["Electricity", "Gas", "Water", "Internet", "Phone", "Council Tax"],
    "Shopping": ["Clothing", "Electronics", "Home & Garden", "Personal Care"],
    "Entertainment": ["Streaming Services", "Cinema", "Events", "Hobbies"],
    "Health & Fitness": ["Gym Membership", "Medical", "Pharmacy", "Sports Equipment"],
    "Income": ["Salary", "Freelance", "Investment Returns", "Other Income"],
    "Savings & Investments": ["Savings Account", "ISA", "Pension", "Stocks"],
    "Transfer": ["Between Accounts", "To Savings"],
    "Other": []  # No subcategories for "Other"
}



def seed_user_categories(user_id: int):
    """Create hierarchical categories for a specific user"""
    
    for parent_name, children in hierarchical_categories.items():
        # Create parent category
        parent = Category(name=parent_name, user_id=user_id, parent_id=None)
        db.session.add(parent)
        db.session.flush()  # Get parent.id before creating children
        
        # Create child categories
        for child_name in children:
            child = Category(name=child_name, user_id=user_id, parent_id=parent.id)
            db.session.add(child)
    
    db.session.commit()
    
    total = len(hierarchical_categories) + sum(len(c) for c in hierarchical_categories.values())
    print(f"✅ Seeded {total} categories ({len(hierarchical_categories)} parents with subcategories) for user {user_id}")

