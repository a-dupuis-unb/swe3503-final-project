import random
import re
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from final_project.encryption_utils import decrypt_to_numeric
from .models import User, Expense, Budget, db, EXPENSE_CATEGORIES
import functools

bp = Blueprint('main', __name__)

# Authentication settings
LOCKOUT_THRESHOLD = 3  # Number of failed attempts before lockout
LOCKOUT_TIME = 3       # Lockout duration in minutes
FAILED_ATTEMPTS = {}   # Track failed login attempts
LOCKOUT_UNTIL = {}     # Track lockout expiration times

class Pagination:
    def __init__(self, query, page, per_page, total, items):
        self.query = query
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items

    @property
    def pages(self):
        if self.per_page == 0 or self.total == 0:
            return 0
        return int((self.total + self.per_page - 1) / self.per_page)

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        if not self.has_prev:
            return None
        return self.page - 1

    @property
    def next_num(self):
        if not self.has_next:
            return None
        return self.page + 1
# ---------------------------
# User Authentication Routes
# ---------------------------

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Basic password policy: at least 8 chars, includes a digit, an uppercase, etc.
        pattern = r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+\-=\[\]{};\":\\|,.<>\/?]{8,}$'

        if not re.match(pattern, password):
            flash("Password must be at least 8 characters long, contain an uppercase letter, and a digit.", "danger")
            return redirect(url_for('main.register'))
        
        # Simple validation
        if not username or not email or not password:
            flash("Please fill out all fields.", "danger")
            return redirect(url_for('main.register'))
        if User.query.filter((User.username==username) | (User.email==email)).first():
            flash("Username or email already exists.", "danger")
            return redirect(url_for('main.register'))
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        new_user.generate_encryption_key()
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for('main.login'))
    return render_template('register.html')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # Check if user is currently locked out
        lockout_expires = LOCKOUT_UNTIL.get(email)
        if lockout_expires and datetime.utcnow() < lockout_expires:
            remaining = int((lockout_expires - datetime.utcnow()).total_seconds())
            flash(f"You are locked out. Please wait {remaining} seconds before trying again.", "danger")
            return redirect(url_for('main.login'))

        # Attempt to find and authenticate user
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            # SUCCESS: Log them in
            login_user(user)
            # Reset attempt count and lockout
            FAILED_ATTEMPTS[email] = 0
            LOCKOUT_UNTIL.pop(email, None)  # remove from lockout if present
            
            # Check if user has a temporary password and needs to change it
            if user.requires_password_change():
                flash("Your password has been reset. Please set a new password to continue.", "warning")
                return redirect(url_for('main.force_password_change'))
            
            flash("Logged in successfully!", "success")
            return redirect(url_for('main.home'))
        else:
            # FAIL: Increment attempt count
            FAILED_ATTEMPTS[email] = FAILED_ATTEMPTS.get(email, 0) + 1
            attempts = FAILED_ATTEMPTS[email]
            remaining_attempts = LOCKOUT_THRESHOLD - attempts

            if attempts >= LOCKOUT_THRESHOLD:
                # Lock them out for 3 minutes
                LOCKOUT_UNTIL[email] = datetime.utcnow() + timedelta(minutes=LOCKOUT_TIME)
                flash(f"You have reached {LOCKOUT_THRESHOLD} failed attempts. "
                     f"Locked out for {LOCKOUT_TIME} minutes.", "danger")
            else:
                flash(f"Invalid credentials. You have {remaining_attempts} attempts left.", "danger")

            return redirect(url_for('main.login'))

    # GET request: Just render the login page
    return render_template('login.html')

@bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # Store email in session for the reset flow
            session['reset_email'] = email
            
            # Mark account as requiring password reset
            user.invalidate_password()
            db.session.commit()
            
            # Redirect directly to reset page
            flash('Please create a new password for your account.', 'info')
            return redirect(url_for('main.reset_password'))
        flash('Email address not found.', 'danger')
    return render_template('reset_password.html')

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Check if we have a reset email in session
    if 'reset_email' not in session:
        flash('Please submit a password reset request first.', 'warning')
        return redirect(url_for('main.reset_password_request'))
        
    # Get user from session email
    email = session['reset_email']
    user = User.query.filter_by(email=email).first()
    
    if not user:
        # Clear invalid session and redirect
        session.pop('reset_email', None)
        flash('Invalid reset session. Please try again.', 'danger')
        return redirect(url_for('main.reset_password_request'))
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.reset_password'))
        
        # Check password strength
        pattern = r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+\-=\[\]{};\":\\|,.<>\/?]{8,}$'
        if not re.match(pattern, new_password):
            return redirect(url_for('main.reset_password'))
        # Set the new password
        user.set_password(new_password)
        db.session.commit()
        db.session.commit()
        
        # Clear reset session
        session.pop('reset_email', None)
        
        flash('Your password has been updated successfully. Please log in with your new password.', 'success')
        return redirect(url_for('main.login'))
        
    return render_template('change_password.html', reset_mode=True)

@bp.route('/force-password-change', methods=['GET', 'POST'])
@login_required
def force_password_change():
    if not current_user.requires_password_change():
        # If user doesn't need to change password, redirect to home
        return redirect(url_for('main.home'))
        
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Check if passwords match
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.force_password_change'))
        
        # Check password strength (same as registration)
        pattern = r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d!@#$%^&*()_+\-=\[\]{};\":\\|,.<>\/?]{8,}$'
        if not re.match(pattern, new_password):
            flash("Password must be at least 8 characters long, contain an uppercase letter, and a digit.", "danger")
            return redirect(url_for('main.force_password_change'))
        
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Your password has been updated successfully.', 'success')
        return redirect(url_for('main.home'))
        
    return render_template('change_password.html')

# Middleware to check if password reset is required and redirect
def check_password_change_required(view_func):
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if current_user.is_authenticated and current_user.requires_password_change():
            # Exclude the force_password_change route and logout route to prevent redirect loops
            if request.endpoint != 'main.force_password_change' and request.endpoint != 'main.logout':
                flash('You must set a new password before continuing.', 'warning')
                return redirect(url_for('main.force_password_change'))
        return view_func(*args, **kwargs)
    return wrapped_view
@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for('main.login'))

# ---------------------------
# Expense Tracking Routes
# ---------------------------
# Expense Tracking Routes
# ---------------------------

@bp.route('/')
@login_required
@check_password_change_required
def home():
    return render_template('home.html')

@bp.route('/add-expense-page')
@login_required
@check_password_change_required
def add_expense_page():
    # Get the last 15 days of expenses
    recent_expenses = (Expense.query
        .filter_by(user_id=current_user.id)
        .order_by(Expense.date.desc())
        .limit(15)
        .all())
    return render_template('add_expense.html', 
                        categories=EXPENSE_CATEGORIES,
                        recent_expenses=recent_expenses)

@bp.route('/search-expenses')
@login_required
@check_password_change_required
def search_expenses():
    category_filter = request.args.get('category_filter', '')
    min_amount = request.args.get('min_amount', '')
    max_amount = request.args.get('max_amount', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    search_text = request.args.get('search_text', '')

    # Basic query without amount filters
    query = Expense.query.filter_by(user_id=current_user.id)

    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Expense.date >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            # Add 1 day to end_dt to make it inclusive of the entire end date
            end_dt = end_dt + timedelta(days=1)
            query = query.filter(Expense.date < end_dt)
        except ValueError:
            pass

    # Apply category filter if provided
    if category_filter:
        query = query.filter(Expense.category == category_filter)

    # Get all matching expenses
    expenses = query.order_by(Expense.date.desc()).all()

    # Filter by amount and search text in Python
    filtered_expenses = []
    for expense in expenses:
        amount = expense.amount  # This will decrypt the amount
        
        # Apply amount filters
        if min_amount and float(amount) < float(min_amount):
            continue
        if max_amount and float(amount) > float(max_amount):
            continue
            
        # Apply search text filter
        if search_text:
            description = expense.description or ""
            if search_text.lower() not in description.lower():
                continue
                
        filtered_expenses.append(expense)

    # Update pagination to work with filtered list
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_items = len(filtered_expenses)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_expenses = filtered_expenses[start_idx:end_idx]
    
    pagination = Pagination(None, page, per_page, total_items, current_expenses)

    return render_template(
        'search_expenses.html',
        filtered_expenses=current_expenses,
        pagination=pagination,
        categories=EXPENSE_CATEGORIES,
        selected_category=category_filter,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search_text=search_text
    )

@bp.route('/add-expense', methods=['POST'])
@login_required
@check_password_change_required
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
    return redirect(url_for('main.add_expense_page'))

@bp.route('/edit-expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
@check_password_change_required
def edit_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    
    # Merge categories similarly as in the home route
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
            return redirect(url_for('main.add_expense_page'))
        except Exception as e:
            flash(f"Error updating expense: {e}", "danger")
    
    return render_template('edit_expense.html', expense=expense, categories=categories)


@bp.route('/delete-expense/<int:expense_id>')
@login_required
@check_password_change_required
def delete_expense(expense_id):
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()
    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting expense: {e}", "danger")
    return redirect(url_for('main.add_expense_page'))

# ---------------------------
# Budget & Reporting Routes
# ---------------------------

@bp.route('/budget')
@login_required
@check_password_change_required
def budget():
    # Get all budgets
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    
    # Get monthly expenses
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1)
    
    monthly_expenses = db.session.query(
        Expense.category,
        Expense._encrypted_amount
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date < end_of_month
    ).all()

    # Calculate expenses by category
    expense_totals = {}
    for category, encrypted_amount in monthly_expenses:
        if category not in expense_totals:
            expense_totals[category] = 0.0
        if encrypted_amount:
            decrypted_amount = float(decrypt_to_numeric(encrypted_amount, current_user.get_encryption_key()))
            expense_totals[category] += decrypted_amount

    # Prepare budget status for each category
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
        'budget.html',
        budget_status=budget_status,
        categories=EXPENSE_CATEGORIES,
        budgets=budgets
    )

@bp.route('/set-budget', methods=['POST'])
@login_required
@check_password_change_required
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
    return redirect(url_for('main.budget'))

@bp.route('/dashboard')
@login_required
@check_password_change_required
def dashboard():
    # Get current month's start and end dates
    today = datetime.utcnow()
    start_of_month = datetime(today.year, today.month, 1)
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1)
    
    # Get monthly expenses per category
    monthly_expenses = db.session.query(
        Expense.category,
        Expense._encrypted_amount,
        Expense.date
    ).filter(
        Expense.user_id == current_user.id,
        Expense.date >= start_of_month,
        Expense.date < end_of_month
    ).all()

    # Process expenses and calculate totals by category
    expense_totals = {}
    total_spent = 0
    for category, encrypted_amount, date in monthly_expenses:
        if category not in expense_totals:
            expense_totals[category] = 0.0
        if encrypted_amount:
            decrypted_amount = float(decrypt_to_numeric(encrypted_amount, current_user.get_encryption_key()))
            expense_totals[category] += decrypted_amount
            total_spent += decrypted_amount
    
    # Get all budgets and calculate total budget
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    total_budget = sum(budget.amount for budget in budgets)
    
    # Calculate budget utilization percentage
    budget_utilization = (total_spent / total_budget * 100) if total_budget > 0 else 0
    
    # Calculate budget status for each category
    budget_status = []
    for category in EXPENSE_CATEGORIES:
        budget = next((b for b in budgets if b.category == category), None)
        spent = expense_totals.get(category, 0)
        status = {
            'category': category,
            'budget_amount': budget.amount if budget else 0,
            'spent': spent,
            'remaining': (budget.amount - spent) if budget else 0,
            'has_budget': budget is not None
        }
        budget_status.append(status)

    # Get real data for pie chart (current month's expense distribution)
    category_labels = list(expense_totals.keys())
    category_values = [expense_totals[cat] for cat in category_labels]

    # Get data for line chart (last 6 months of expenses)
    line_labels = []
    line_data = []
    for i in range(5, -1, -1):
        current_date = today - timedelta(days=30 * i)
        month_start = datetime(current_date.year, current_date.month, 1)
        if current_date.month == 12:
            month_end = datetime(current_date.year + 1, 1, 1)
        else:
            month_end = datetime(current_date.year, current_date.month + 1, 1)
        
        # Query expenses for this month
        month_expenses = db.session.query(
            Expense._encrypted_amount
        ).filter(
            Expense.user_id == current_user.id,
            Expense.date >= month_start,
            Expense.date < month_end
        ).all()
        
        # Calculate total for the month
        month_total = 0
        for (encrypted_amount,) in month_expenses:
            if encrypted_amount:
                decrypted_amount = float(decrypt_to_numeric(encrypted_amount, current_user.get_encryption_key()))
                month_total += decrypted_amount
        
        line_labels.append(current_date.strftime('%b'))
        line_data.append(month_total)
    
    return render_template(
        'dashboard.html',
        line_labels=line_labels,
        line_data=line_data,
        category_labels=category_labels,
        category_values=category_values,
        budget_status=budget_status,
        categories=EXPENSE_CATEGORIES,
        expense_totals=expense_totals,
        budgets=budgets,
        budget_utilization=budget_utilization,
        total_budget=total_budget,
        total_spent=total_spent
    )

if __name__ == '__main__':
    from final_project import create_app
    app = create_app()
    app.run(
        host='0.0.0.0',  # or 127.0.0.1 for localhost only
        port=5000,
        debug=True
    )
