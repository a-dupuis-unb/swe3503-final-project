from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from decimal import Decimal
from sqlalchemy.orm import validates

# Add predefined categories
EXPENSE_CATEGORIES = [
    'Housing',
    'Transportation',
    'Food',
    'Utilities',
    'Insurance',
    'Healthcare',
    'Savings',
    'Entertainment',
    'Shopping',
    'Other'
]

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    expenses = db.relationship('Expense', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f"<User {self.username}>"

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    _amount = db.Column('amount', db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    @validates('category')
    def validate_category(self, key, category):
        assert category in EXPENSE_CATEGORIES, f"Category must be one of: {', '.join(EXPENSE_CATEGORIES)}"
        return category
    
    @property
    def amount(self):
        return float(self._amount)

    @amount.setter
    def amount(self, value):
        self._amount = round(Decimal(str(value)), 2)
    
    def __repr__(self):
        return f"<Expense {self.category}: ${self.amount:.2f}>"

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    _amount = db.Column('amount', db.Numeric(10, 2), nullable=False)
    period = db.Column(db.String(20), default="monthly")  # "monthly" or "weekly"
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    @validates('category')
    def validate_category(self, key, category):
        assert category in EXPENSE_CATEGORIES, f"Category must be one of: {', '.join(EXPENSE_CATEGORIES)}"
        return category
    
    @property
    def amount(self):
        return float(self._amount)

    @amount.setter
    def amount(self, value):
        self._amount = round(Decimal(str(value)), 2)
    
    def __repr__(self):
        return f"<Budget {self.category}: ${self.amount:.2f} per {self.period}>"
