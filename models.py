from flask_sqlalchemy import SQLAlchemy   # Our database helper
from datetime import datetime
from flask_login import UserMixin


# This is like the "bridge" between our app and PostgreSQL
db = SQLAlchemy()

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
    name = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='user', lazy=True, cascade='all, delete-orphan')
    social_auths = db.relationship('SocialAuth', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Transaction(db.Model):
    __tablename__ = "transaction"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)  # ADD THIS
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False) 
    description = db.Column(db.String(200), nullable=False)
    account = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    normalised_description = db.Column(db.String(200), nullable=True)
    
    def __repr__(self):
        return f"<Transaction {self.description}: £{self.amount}>"


class Category(db.Model):
    __tablename__ = "category"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f"<Category {self.name}>"