# app.py
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from models import db, User, Expense, Budget
from datetime import datetime
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
        identifier = request.form.get('identifier')
        password = request.form.get('password')
        # Identify user by username or email
        user = User.query.filter((User.username==identifier) | (User.email==identifier)).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid credentials.", "danger")
            return redirect(url_for('login'))
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
    return render_template('index.html', expenses=expenses)

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
    return render_template('edit_expense.html', expense=expense)

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
    summary = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).filter(Expense.user_id == current_user.id).group_by(Expense.category).all()
    budgets = Budget.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', summary=summary, budgets=budgets)

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
    app.run(debug=True)
