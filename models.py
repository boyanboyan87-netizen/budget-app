# Step 1: Import tools we need
from flask_sqlalchemy import SQLAlchemy   # Our database helper
from datetime import datetime             # For timestamps

# This is like the "bridge" between our app and PostgreSQL
db = SQLAlchemy()


class Transaction(db.Model):
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False) 
    description = db.Column(db.String(200), nullable=False)
    account = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    normalised_description = db.Column(db.String(200), nullable=True)
    
    # BONUS: This helps us see transactions nicely in Python
    def __repr__(self):
        return f"<Transaction {self.description}: £{self.amount}>"

class Category(db.Model):
    __tablename__ = "category"  # singular, matching 'transaction'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Category {self.name}>"