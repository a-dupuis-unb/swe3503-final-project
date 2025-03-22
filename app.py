# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from models import db, User, Expense, Budget, EXPENSE_CATEGORIES
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
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
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.date.desc()).all()
    
    # Use the default list of categories
    categories = EXPENSE_CATEGORIES

    return render_template('index.html', expenses=expenses, categories=categories)

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
    
    return render_template(
        'dashboard.html',
        budget_status=budget_status,
        categories=EXPENSE_CATEGORIES,
        summary=expenses_by_category,
        budgets=budgets
    )

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

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',  # or 127.0.0.1 for localhost only
        port=5000,
        debug=False
    )
