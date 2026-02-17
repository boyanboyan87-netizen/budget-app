"""Database migration script - drops and recreates all tables with new schema"""
from app import app, db
from models import User, SocialAuth, Transaction, Category

def reset_database():
    """Drop all tables and recreate them with new multi-user schema"""
    with app.app_context():
        print("🗑️  Dropping all tables...")
        db.drop_all()

        print("📝 Creating all tables with new schema...")
        db.create_all()

        print("\n✅ Database reset complete!")
        print("\nNew tables created:")
        print("  - user (authentication)")
        print("  - social_auth (Google/Facebook/etc. logins)")
        print("  - transaction (user-specific transactions)")
        print("  - category (user-specific categories)")
        print("\n🎯 Ready for Phase 1 testing!")

if __name__ == '__main__':
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("   All existing transactions and categories will be lost.")
    confirm = input("\nAre you sure you want to continue? (yes/no): ")
    
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("❌ Migration cancelled")
