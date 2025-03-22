import pytest
from app import app, db
from models import User, Expense, Budget
import uuid
@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test_secret_key'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Create test user
            # Create test user with unique email
            unique_id = str(uuid.uuid4())
            test_user = User(
                username=f'testuser_{unique_id}',
                email=f'test_{unique_id}@test.com'
            )
            test_user.set_password('password123')
            db.session.add(test_user)
            db.session.commit()
            
            # Log in the test user
            client.post('/login', data={
                'identifier': test_user.username,
                'password': 'password123'
            }, follow_redirects=True)
            
        yield client
        with app.app_context():
            db.session.remove()
            db.drop_all()

def test_home_page(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"Expense Tracker" in response.data

def test_add_expense(client):
    data = {
        'date': '2025-03-20',
        'category': 'Food',
        'amount': '12.50',
        'description': 'Lunch'
    }
    response = client.post('/add-expense', data=data, follow_redirects=True)
    assert b"Expense added successfully!" in response.data
    # Verify the expense is in the database
    with app.app_context():
        expense = Expense.query.filter_by(category='Food').first()
        assert expense is not None
        assert expense.amount == 12.50
def test_set_budget(client):
    data = {
        'category': 'Food',
        'amount': '300',
        'period': 'monthly'
    }
    response = client.post('/set-budget', data=data, follow_redirects=True)
    assert b"Budget set successfully!" in response.data
    # Verify the budget is in the database
    with app.app_context():
        budget = Budget.query.filter_by(category='Food', period='monthly').first()
        assert budget is not None
        assert budget.amount == 300.0
