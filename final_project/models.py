from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, current_user
from decimal import Decimal
from sqlalchemy.orm import validates
import os
from final_project.encryption_utils import generate_key, encrypt_key_with_master_key, decrypt_key_with_master_key, encrypt_to_string, decrypt_to_string, decrypt_to_numeric
from final_project import db

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

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    encrypted_key = db.Column(db.String(255), nullable=True)
    
    expenses = db.relationship('Expense', backref='user', lazy=True)
    budgets = db.relationship('Budget', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_encryption_key(self):
        """Generate a new encryption key for the user and store it encrypted"""
        # Generate a new encryption key
        key = generate_key()
        # Get the master key from environment variable
        master_key = os.environ.get('MASTER_KEY')
        if not master_key:
            raise ValueError("MASTER_KEY environment variable is not set")
        # Encrypt the user's key with the master key
        self.encrypted_key = encrypt_key_with_master_key(key, master_key)
        return key
    
    def get_encryption_key(self):
        """Decrypt and return the user's encryption key"""
        if not self.encrypted_key:
            return self.generate_encryption_key()
        
        master_key = os.environ.get('MASTER_KEY')
        if not master_key:
            raise ValueError("MASTER_KEY environment variable is not set")
        
        return decrypt_key_with_master_key(self.encrypted_key, master_key)
    
    def __repr__(self):
        return f"<User {self.username}>"

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow)
    category = db.Column(db.String(50), nullable=False)
    _encrypted_amount = db.Column('amount', db.Text, nullable=False)
    _encrypted_description = db.Column('description', db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    @validates('category')
    def validate_category(self, key, category):
        assert category in EXPENSE_CATEGORIES, f"Category must be one of: {', '.join(EXPENSE_CATEGORIES)}"
        return category
    
    @property
    def amount(self):
        """Decrypt and return the amount as a float."""
        if not self._encrypted_amount:
            return 0.0
        user = current_user
        encryption_key = user.get_encryption_key()
        try:
            return decrypt_to_numeric(self._encrypted_amount, encryption_key)
        except Exception as e:
            # Log the error but return a default value to prevent application from crashing
            print(f"Error decrypting amount: {e}")
            return 0.0

    @amount.setter
    def amount(self, value):
        """Encrypt and store the amount."""
        # First round to 2 decimal places
        numeric_value = round(Decimal(str(value)), 2)
        # Convert to string for encryption
        str_value = str(numeric_value)
        
        user = current_user
        encryption_key = user.get_encryption_key()
        self._encrypted_amount = encrypt_to_string(str_value, encryption_key)

    @property
    def description(self):
        """Decrypt and return the description."""
        if not self._encrypted_description:
            return ""
        user = current_user
        encryption_key = user.get_encryption_key()
        try:
            return decrypt_to_string(self._encrypted_description, encryption_key)
        except Exception as e:
            # Log the error but return a default value
            print(f"Error decrypting description: {e}")
            return "[Encrypted]"

    @description.setter
    def description(self, value):
        """Encrypt and store the description."""
        if value is None:
            self._encrypted_description = None
            return
        
        user = current_user
        encryption_key = user.get_encryption_key()
        self._encrypted_description = encrypt_to_string(value, encryption_key)
    
    def __repr__(self):
        """Return a string representation of the expense with safely decrypted data."""
        try:
            amount_display = f"${self.amount:.2f}"
        except:
            amount_display = "[Encrypted Amount]"
        
        return f"<Expense {self.category}: {amount_display}>"

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
