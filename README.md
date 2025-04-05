# Personal Finance Management Application

## Overview
This application helps users track expenses, set budgets, and visualize their financial health. It is built with **Flask** (Python) and uses **SQLite** for data storage. User authentication is included, along with a **lockout mechanism** that temporarily prevents brute-force login attempts after a set number of failures.

## Features
- **User Authentication:** Register, log in, and log out securely.
- **Lockout After Failed Attempts:**  
  - Locks a user out for a set time (e.g., 3 minutes) if they exceed the allowed number of failed logins (e.g., 5).
- **Expense Tracking:** Add, view, edit, and delete expenses, categorized for easy organization.
- **Budget Management:** Set and update budgets by category (monthly or weekly).
- **Dashboard:**  
  - Visual overview of expenses vs. budgets.  
  - Progress bars indicate if you’re under or over budget.
- **Responsive UI:** Basic CSS styling and optional navigation bar for ease of use.

## Prerequisites
- **Python 3.8+**
- **pip** (Python package manager)
- **SQLite** (included with Python)

## Installation

1. **Clone the Repository**  
   ```bash
   git clone <repository-url>
   cd final_project
   ```

2. **Create and Activate a Virtual Environment** (Recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate        # On macOS/Linux
   # or 
   venv\Scripts\activate.bat       # On Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Setup**
   Set the Flask environment variables:
   ```bash
   # On macOS/Linux
   export FLASK_APP=final_project
   export MASTER_KEY=defaultmasterkey  # For development only
   
   # On Windows CMD
   set FLASK_APP=final_project
   set MASTER_KEY=defaultmasterkey  # For development only
   
   # On Windows PowerShell
   $env:FLASK_APP = "final_project"
   $env:MASTER_KEY = "defaultmasterkey"  # For development only
   ```

5. **Initialize the Database**
   The app automatically creates an SQLite database (finance.db) if it doesn't exist.
   ```bash
   python migration_script.py
   ```

## Usage
### Running the Application

With your virtual environment activated and environment variables set:

```bash
flask run
```

- By default, Flask listens on 127.0.0.1:5000
- Open your web browser and navigate to http://127.0.0.1:5000

### Initial Setup and First User

1. Register a new user at http://127.0.0.1:5000/register
2. Log in with your credentials
3. Begin adding expenses and budgets

### Generating Test Data (Optional)

To populate the database with sample data for testing purposes:

```bash
python generate_dummy_data.py
```

This will create sample budgets and expenses for testing.

### Port Conflicts

If port 5000 is in use, either:

- Kill the process using port 5000: `lsof -i :5000` on macOS/Linux to find it, then `kill PID`
- Specify a different port when running Flask: `flask run --port=5001`

### Lockout Mechanism

- After a certain number of failed login attempts (e.g., 5), the user is locked out for 3 minutes
- Lockout data is stored in-memory
- Lockouts reset when the server restarts

### Debug Mode

To enable Flask's debug mode:

```bash
# On macOS/Linux
export FLASK_ENV=development

# On Windows CMD
set FLASK_ENV=development

# On Windows PowerShell
$env:FLASK_ENV = "development"

flask run
```

This auto-reloads the server on code changes and provides detailed error pages.

## Testing (Optional)

If you have a tests/ folder with Pytest tests, you can run:

`pytest`
This will discover and run all tests in the project.

## Project Structure

The actual project structure:

```
final_project/
├── instance/                    # Application instance data
│   └── finance.db               # SQLite database file
├── migration_script.py          # Database migration script
├── generate_dummy_data.py       # Script to populate test data
├── requirements.txt             # Python dependencies
├── README.md                    # This documentation
├── final_project/               # Application package
│   ├── app.py                   # Main application file
│   ├── models.py                # Database models
│   ├── __init__.py              # Package initialization
│   ├── encryption_utils.py      # Encryption utilities
│   ├── migrations/              # Database migrations
│   │   ├── __init__.py
│   │   └── add_has_temp_password.py
│   ├── static/                  # Static assets
│   │   └── css/
│   │       └── style.css        # Application styles
│   └── templates/               # HTML templates
│       ├── add_expense.html     # Form to add new expenses
│       ├── base.html            # Base template with common elements
│       ├── budget.html          # Budget management page
│       ├── change_password.html # Password change form
│       ├── dashboard.html       # Main dashboard with visualizations
│       ├── edit_expense.html    # Form to edit expenses
│       ├── home.html            # Landing page
│       ├── login.html           # User login
│       ├── navbar.html          # Navigation partial
│       ├── register.html        # User registration
│       ├── reset_password.html  # Password reset request
│       └── search_expenses.html # Expense search page
└── tests/                       # Test suite (if available)
    └── test_app.py              # Application tests
```

## Security Considerations

### Data Encryption

This application uses encryption to protect sensitive financial data:

- Expense amounts and descriptions are encrypted in the database
- A master key (MASTER_KEY) is required for the encryption to work
- Data is decrypted only when needed for display

### Password Management

- Passwords are securely hashed before storage
- A password reset mechanism is implemented for account recovery

## Common Troubleshooting

- **Flask Command Not Found:**
  - Ensure your virtual environment is activated
  - Verify Flask is installed with `pip install flask`

- **Port Already in Use:**
  - Run `lsof -i :5000` on macOS/Linux to find and kill the process
  - Or run Flask on a different port: `flask run --port=5001`

- **Module Not Found Errors:**
  - Verify FLASK_APP environment variable is set correctly
  - Ensure all dependencies are installed: `pip install -r requirements.txt`

- **Encryption/Decryption Issues:**
  - Verify MASTER_KEY is set correctly in your environment

- **Lockout Not Persisting:**
  - In-memory lockout data resets on server restart
  - For production, consider storing lockout info in the database

- **Cannot Edit or Delete Expenses:**
  - Ensure you're logged in and that the routes match the buttons in your templates

## License

MIT License
