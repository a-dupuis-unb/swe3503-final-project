# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from models import db, User, Expense, Budget, EXPENSE_CATEGORIES
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'supersecretkey'

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

LOCKOUT_THRESHOLD = 5      # Number of failed attempts allowed
LOCKOUT_TIME = 3           # Lockout duration in minutes
FAILED_ATTEMPTS = {}       # Tracks number of failed attempts per user identifier
LOCKOUT_UNTIL = {}         # Tracks lockout expiration time per user identifier

# ---------------------------
# User Authentication Routes
# ---------------------------

import re
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic password policy: at least 8 chars, includes a digit, an uppercase, etc.
        pattern = r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+\-=\[\]{};":\\|,.<>\/?]{8,}$'

        if not re.match(pattern, password):
            flash("Password must be at least 8 characters long, contain an uppercase letter, and a digit.", "danger")
            return redirect(url_for('register'))
        
        # Simple validation
        if not username or not email or not password:
            flash("Please fill out all fields.", "danger")
            return redirect(url_for('register'))
        if User.query.filter((User.username==username) | (User.email==email)).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for('register'))
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier')  # username or email
        password = request.form.get('password')

        # 1. Check if user is currently locked out
        lockout_expires = LOCKOUT_UNTIL.get(identifier)
        if lockout_expires and datetime.utcnow() < lockout_expires:
            remaining = int((lockout_expires - datetime.utcnow()).total_seconds())
            flash(f"You are locked out. Please wait {remaining} seconds before trying again.", "danger")
            return redirect(url_for('login'))

        # 2. Attempt to find and authenticate user
        user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
        
        if user and user.check_password(password):
            # SUCCESS: Log them in
            login_user(user)
            # Reset attempt count and lockout
            FAILED_ATTEMPTS[identifier] = 0
            LOCKOUT_UNTIL.pop(identifier, None)  # remove from lockout if present
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
        else:
            # FAIL: Increment attempt count
            FAILED_ATTEMPTS[identifier] = FAILED_ATTEMPTS.get(identifier, 0) + 1
            attempts = FAILED_ATTEMPTS[identifier]
            remaining_attempts = LOCKOUT_THRESHOLD - attempts

            if attempts >= LOCKOUT_THRESHOLD:
                # Lock them out for 3 minutes
                LOCKOUT_UNTIL[identifier] = datetime.utcnow() + timedelta(minutes=LOCKOUT_TIME)
                flash(f"You have reached {LOCKOUT_THRESHOLD} failed attempts. "
                      f"Locked out for {LOCKOUT_TIME} minutes.", "danger")
            else:
                flash(f"Invalid credentials. You have {remaining_attempts} attempts left.", "danger")

            return redirect(url_for('login'))

    # GET request: Just render the login page
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

# ---------------------------
# Expense Tracking Routes
# ---------------------------

@app.route('/')
@login_required
def index():
    # Always get the 5 most recent expenses (unfiltered)
    recent_expenses = (Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .limit(5)
        .all()
    )

    # Get filters from query parameters (sent via ?category_filter=Food&start_date=... etc.)
    category_filter = request.args.get('category_filter', '')
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search_text = request.args.get('search_text', '')

    # Base query for expenses belonging to current user
    query = Expense.query.filter_by(user_id=current_user.id)

    # Filter by category if provided
    if category_filter:
        query = query.filter(Expense.category == category_filter)

    # Filter by amount range if provided
    if min_amount:
        try:
            query = query.filter(Expense._amount >= float(min_amount))
        except ValueError:
            pass  # ignore if user typed something invalid
    if max_amount:
        try:
            query = query.filter(Expense._amount <= float(max_amount))
        except ValueError:
            pass

    # Filter by date range if provided
    from datetime import datetime
    date_format = '%Y-%m-%d'
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, date_format)
            query = query.filter(Expense.date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, date_format)
            query = query.filter(Expense.date <= end_dt)
        except ValueError:
            pass

    # Search by description (case-insensitive)
    if search_text:
        # Using ilike for case-insensitive matching
        query = query.filter(Expense.description.ilike(f'%{search_text}%'))

    # Sort results (optional). Let’s default to newest first.
    filtered_expenses = query.order_by(Expense.date.desc()).all()

    # For the category dropdown
    categories = EXPENSE_CATEGORIES  # or dynamically gather from the DB if you prefer

    return render_template(
        'index.html', 
        recent_expenses=recent_expenses,
        filtered_expenses=filtered_expenses,
        categories=categories
    )

@app.route('/add-expense', methods=['POST'])
@login_required
def add_expense():
    date_str = request.form.get('date')
    category = request.form.get('category')
    amount = request.form.get('amount')
    description = request.form.get('description')
    try:
        expense_date = datetime.strptime(date_str, '%Y-%m-%d')
        expense = Expense(
            date=expense_date,
            category=category,
            amount=float(amount),
            description=description,
            user_id=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense added successfully!", "success")
    except Exception as e:
        flash(f"Error adding expense: {e}", "danger")
    return redirect(url_for('index'))

@app.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    
    # Merge categories similarly as in the index route
    categories_query = db.session.query(Expense.category).filter_by(user_id=current_user.id).distinct().all()
    expense_categories = [cat[0] for cat in categories_query] if categories_query else []
    default_categories = EXPENSE_CATEGORIES
    categories = list(set(default_categories) | set(expense_categories))
    
    if request.method == 'POST':
        try:
            expense.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d')
            expense.category = request.form.get('category')
            expense.amount = float(request.form.get('amount'))
            expense.description = request.form.get('description')
            db.session.commit()
            flash("Expense updated successfully!", "success")
            return redirect(url_for('index'))
        except Exception as e:
            flash(f"Error updating expense: {e}", "danger")
    
    return render_template('edit_expense.html', expense=expense, categories=categories)


@app.route('/delete-expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting expense: {e}", "danger")
    return redirect(url_for('index'))

# ---------------------------
# Budget & Reporting Routes
# ---------------------------

@app.route('/set-budget', methods=['POST'])
@login_required
def set_budget():
    category = request.form.get('category')
    amount = request.form.get('amount')
    period = request.form.get('period', 'monthly')
    try:
        budget = Budget.query.filter_by(user_id=current_user.id, category=category, period=period).first()
        if budget:
            budget.amount = float(amount)
        else:
            budget = Budget(category=category, amount=float(amount), period=period, user_id=current_user.id)
            db.session.add(budget)
        db.session.commit()
        flash("Budget set successfully!", "success")
    except Exception as e:
        flash(f"Error setting budget: {e}", "danger")
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get current month's start and end dates
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1)
    
    # Get monthly expenses per category
    expenses_by_category = db.session.query(
        Expense.category,
        db.func.sum(Expense._amount).label('total')
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date < end_of_month
    ).group_by(Expense.category).all()
    
    # Convert to dictionary for easier lookup
    expense_totals = {cat: float(total) for cat, total in expenses_by_category}
    
    # Get all budgets
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    # Calculate budget status for each category
    budget_status = []
    for category in EXPENSE_CATEGORIES:
        budget = next((b for b in budgets if b.category == category), None)
        status = {
            'category': category,
            'budget_amount': budget.amount if budget else 0,
            'spent': expense_totals.get(category, 0),
            'remaining': (budget.amount - expense_totals.get(category, 0)) if budget else 0,
            'has_budget': budget is not None
        }
        budget_status.append(status)

    # Example data for the pie chart (category distribution)
    # If it were live data, it would be queried from the database and summed
    category_labels = ["Food", "Transportation", "Housing", "Entertainment"]
    category_values = [300, 150, 800, 100]

    # Example data for the line chart (monthly spending over 6 months)
    # If it were live data, it would be queried from the database and summed
    line_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun"]
    line_data = [200, 250, 180, 300, 220, 400]
    
    return render_template(
        'dashboard.html',
        line_labels=line_labels,
        line_data=line_data,
        category_labels=category_labels,
        category_values=category_values,
        budget_status=budget_status,
        categories=EXPENSE_CATEGORIES,
        summary=expenses_by_category,
        budgets=budgets
    )

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',  # or 127.0.0.1 for localhost only
        port=5000,
        debug=True
    )
