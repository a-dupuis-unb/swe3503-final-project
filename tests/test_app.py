import pytest
from final_project.app import app, db, User, Expense, Budget
from datetime import datetime

@pytest.fixture
def client():
    """
    Pytest fixture to set up a test client with an in-memory database.
    """
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False  # If you're using CSRF, disable it for testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client
        # Teardown
        with app.app_context():
            db.drop_all()


def register_user(client, username, email, password):
    return client.post('/register', data={
        'username': username,
        'email': email,
        'password': password
    }, follow_redirects=True)

def login_user(client, identifier, password):
    return client.post('/login', data={
        'identifier': identifier,
        'password': password
    }, follow_redirects=True)

def logout_user(client):
    return client.get('/logout', follow_redirects=True)


def test_registration_login_logout(client):
    """
    Test user registration, login, and logout flow.
    """
    # 1. Register a new user
    resp = register_user(client, 'testuser', 'test@example.com', 'Password1')
    assert resp.status_code == 200
    assert b"Registration successful. Please log in." in resp.data

    # 2. Attempt to log in with the new user
    resp = login_user(client, 'testuser', 'Password1')
    assert b"Logged in successfully!" in resp.data
    # We should now be redirected to the index page
    assert resp.status_code == 200

    # 3. Log out
    resp = logout_user(client)
    assert b"Logged out successfully." in resp.data


def test_invalid_login(client):
    """
    Test login with invalid credentials.
    """
    # Register a user first
    register_user(client, 'testuser2', 'test2@example.com', 'Password1')

    # Attempt to login with wrong password
    resp = login_user(client, 'testuser2', 'WrongPassword')
    assert b"Invalid credentials." in resp.data
    assert resp.status_code == 200


def test_add_expense(client):
    """
    Test adding an expense when logged in.
    """
    # Register + login
    register_user(client, 'testuser3', 'test3@example.com', 'Password1')
    login_user(client, 'testuser3', 'Password1')

    # Add an expense
    resp = client.post('/add-expense', data={
        'date': '2025-04-10',
        'category': 'Food',
        'amount': '12.50',
        'description': 'Lunch'
    }, follow_redirects=True)
    assert b"Expense added successfully!" in resp.data

    # Check if the expense is actually in the DB
    with app.app_context():
        expense = Expense.query.filter_by(category='Food').first()
        assert expense is not None
        assert expense.amount == 12.50
        assert expense.description == 'Lunch'


def test_edit_expense(client):
    """
    Test editing an existing expense.
    """
    # Register + login
    register_user(client, 'testuser4', 'test4@example.com', 'Password1')
    login_user(client, 'testuser4', 'Password1')

    # Add an expense
    client.post('/add-expense', data={
        'date': '2025-04-10',
        'category': 'Utilities',
        'amount': '50',
        'description': 'Electric Bill'
    }, follow_redirects=True)

    # Retrieve the expense from DB
    with app.app_context():
        expense = Expense.query.filter_by(category='Utilities').first()
        expense_id = expense.id

    # Edit the expense
    resp = client.post(f'/edit-expense/{expense_id}', data={
        'date': '2025-04-11',
        'category': 'Utilities',
        'amount': '60',
        'description': 'Updated Electric Bill'
    }, follow_redirects=True)
    assert b"Expense updated successfully!" in resp.data

    # Verify DB changes
    with app.app_context():
        updated_expense = Expense.query.get(expense_id)
        assert updated_expense.date.strftime('%Y-%m-%d') == '2025-04-11'
        assert updated_expense.amount == 60.0
        assert updated_expense.description == 'Updated Electric Bill'


def test_delete_expense(client):
    """
    Test deleting an expense.
    """
    # Register + login
    register_user(client, 'testuser5', 'test5@example.com', 'Password1')
    login_user(client, 'testuser5', 'Password1')

    # Add an expense
    client.post('/add-expense', data={
        'date': '2025-05-01',
        'category': 'Entertainment',
        'amount': '20',
        'description': 'Movie Ticket'
    }, follow_redirects=True)

    # Grab the expense
    with app.app_context():
        expense = Expense.query.filter_by(category='Entertainment').first()
        expense_id = expense.id

    # Delete it
    resp = client.post(f'/delete-expense/{expense_id}', follow_redirects=True)
    assert b"Expense deleted successfully!" in resp.data

    # Check DB
    with app.app_context():
        deleted_expense = Expense.query.get(expense_id)
        assert deleted_expense is None


def test_set_budget(client):
    """
    Test setting a budget.
    """
    # Register + login
    register_user(client, 'testuser6', 'test6@example.com', 'Password1')
    login_user(client, 'testuser6', 'Password1')

    # Set a budget
    resp = client.post('/set-budget', data={
        'category': 'Food',
        'amount': '300',
        'period': 'monthly'
    }, follow_redirects=True)
    assert b"Budget set successfully!" in resp.data

    # Check DB
    with app.app_context():
        budget = Budget.query.filter_by(category='Food', period='monthly').first()
        assert budget is not None
        assert budget.amount == 300.0


def test_dashboard(client):
    """
    Test accessing the dashboard.
    """
    # Register + login
    register_user(client, 'testuser7', 'test7@example.com', 'Password1')
    login_user(client, 'testuser7', 'Password1')

    resp = client.get('/dashboard')
    assert resp.status_code == 200
    # You might check for certain text or placeholders in the dashboard
    # For example:
    assert b"Budget Overview" in resp.data


def test_lockout_after_failed_logins(client):
    """
    Test the lockout mechanism after multiple failed logins.
    """
    # Register user
    register_user(client, 'lockoutuser', 'lockout@example.com', 'Password1')

    # Fail 4 times
    for i in range(4):
        resp = login_user(client, 'lockoutuser', 'WrongPass')
        assert b"Invalid credentials." in resp.data
        assert resp.status_code == 200

    # 5th time triggers lockout
    resp = login_user(client, 'lockoutuser', 'WrongPass')
    assert b"You have reached 5 failed attempts." in resp.data
    assert resp.status_code == 200

    # Attempt again should show locked out
    resp = login_user(client, 'lockoutuser', 'Password1')
    assert b"You are locked out." in resp.data
