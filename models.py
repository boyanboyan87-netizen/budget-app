from flask_sqlalchemy import SQLAlchemy   # Our database helper
from datetime import datetime
from flask_login import UserMixin, current_user
from sqlalchemy.orm import Query
from sqlalchemy.ext.hybrid import hybrid_property


# This is like the "bridge" between our app and PostgreSQL
db = SQLAlchemy()

class UserScopedQuery(Query):
    """Custom query class that provides user-scoped filtering."""

    def for_user(self, user_id: int):
        """Filter results to a specific user."""
        return self.filter_by(user_id=user_id)

    def for_current_user(self):
        """Filter results to the currently logged-in user."""
        if not current_user.is_authenticated:
            # Return empty query if no user logged in
            return self.filter_by(user_id=None)
        return self.filter_by(user_id=current_user.id)

class SocialAuth(db.Model):
    """Store social authentication provider connections"""
    __tablename__ = "social_auth"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    provider = db.Column(db.String(50), nullable=False)  # 'google', 'facebook', 'github', etc.
    provider_user_id = db.Column(db.String(200), nullable=False)  # Their ID from that provider
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure one provider account can't link to multiple users
    __table_args__ = (db.UniqueConstraint('provider', 'provider_user_id', name='unique_provider_user'),)
    
    def __repr__(self):
        return f'<SocialAuth {self.provider}:{self.provider_user_id}>'


class User(UserMixin, db.Model):
    """User model for authentication and data ownership"""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy=True, cascade='all, delete-orphan')
    social_auths = db.relationship('SocialAuth', backref='user', lazy=True, cascade='all, delete-orphan')
    plaid_items = db.relationship('PlaidItem', backref='user', lazy=True, cascade='all, delete-orphan')
    accounts = db.relationship('Account', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Transaction(db.Model):
    __tablename__ = "transaction"
    query_class = UserScopedQuery

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True, index=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False) 
    description = db.Column(db.String(200), nullable=False)
    account = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    normalised_description = db.Column(db.String(200), nullable=True)
    plaid_transaction_id = db.Column(db.String(100), nullable=True)
    
    # Relationships
    category_obj = db.relationship('Category', backref='transactions')
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=True, index=True)

    @hybrid_property
    def category(self):
        """Return full category path string (e.g., 'Groceries > Supermarket')"""
        if self.category_obj:
            return self.category_obj.full_path
        return None

    @category.setter  
    def category(self, value):
        """Allow setting category by string - finds matching category by name or path"""
        if value is None:
            self.category_id = None
            return
        
        # Import here to avoid circular import
        from models import Category
        
        # Try to find category by full path or name
        cat = Category.query.for_current_user().filter(
            (Category.name == value)
        ).first()
        
        if cat:
            self.category_id = cat.id
        else:
            # If not found, leave as None (will handle in migration)
            self.category_id = None

    def __repr__(self):
        return f"<Transaction {self.description}: £{self.amount}>"


class Category(db.Model):
    __tablename__ = "category"
    query_class = UserScopedQuery

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True, index=True)

    # Relationships
    parent = db.relationship('Category', remote_side=[id], backref='children')

    @property
    def full_path(self) -> str:
        """Return 'Groceries > Supermarket' or just 'Groceries'"""
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    @property
    def is_parent(self) -> bool:
        """Check if this category has children"""
        return len(self.children) > 0

    def __repr__(self):
        return f"<Category {self.name}>"
    

class PlaidItem(db.Model):
    __tablename__ = "plaid_item"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    access_token = db.Column(db.String(200), nullable=False)
    item_id = db.Column(db.String(100), nullable=False)
    institution_name = db.Column(db.String(100))
    cursor = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_synced_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    accounts = db.relationship('Account', backref='item', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<PlaidItem {self.institution_name} (user {self.user_id})>'


class Account(db.Model):
    __tablename__ = "account"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # 'automatic' | 'manual'
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active' | 'closed'
    currency = db.Column(db.String(10), nullable=False, default='GBP')

    # Plaid-specific (null for manual accounts)
    plaid_account_id = db.Column(db.String(100), nullable=True)  # Plaid's string ID
    item_id = db.Column(db.Integer, db.ForeignKey('plaid_item.id'), nullable=True)
    mask = db.Column(db.String(10), nullable=True)
    subtype = db.Column(db.String(50), nullable=True)  # e.g. 'depository', 'credit'
    invert_amounts = db.Column(db.Boolean, nullable=True)  # True=flip amount signs on import, None=unknown


    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    balance_history = db.relationship(
        'AccountBalance',
        backref='account',
        order_by='AccountBalance.recorded_at.desc()',
        cascade='all, delete-orphan',
    )
    transactions = db.relationship('Transaction', backref='account_obj', lazy=True)

    @property
    def latest_balance(self):
        return self.balance_history[0] if self.balance_history else None

    def __repr__(self):
        return f'<Account {self.name} ({self.account_type})>'



class AccountBalance(db.Model):
    """Historical balance snapshot for a Accounts. Appended on each sync."""
    __tablename__ = "account_balance"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(
        db.Integer,
        db.ForeignKey('account.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    current_balance = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default='GBP')
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
