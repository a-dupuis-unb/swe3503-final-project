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
- **Responsive UI (Optional):** Basic CSS styling and optional navigation bar for ease of use.

## Prerequisites
- **Python 3.8+**
- **pip** (Python package manager)

## Installation

1. **Clone the Repository**  
   ```bash
   git clone <repository-url>
   cd final_project

2. **Create and Activate a Virtual Environment**(Recommended)

`python -m venv venv`
`source venv/bin/activate        # On macOS/Linux`
`# or venv\Scripts\activate.bat  # On Windows`

3. **Install Dependencies**

    `pip install -r requirements.txt`

4. **Initialize the Database**
    - The app automatically creates an SQLite database (finance.db) if it doesn’t exist.

    - No manual migrations are required—simply run the app once.

## Usage
### Running the Application

`python app.py`
- By default, Flask listens on 127.0.0.1:5000.
- Open your web browser and navigate to http://127.0.0.1:5000.

**Port Conflicts**

If port 5000 is in use, either:

- Kill the process using port 5000 (for macOS, lsof -i :5000 to find it), or
- Specify a new port in app.run(host='0.0.0.0', port=5001, debug=False).

**Lockout Mechanism**

- After a certain number of failed login attempts (e.g., 5), the user is locked out for 3 minutes.
- Lockout data may be stored either in-memory or in the database, depending on your configuration.
- If using in-memory, lockouts reset when the server restarts.

**Debug Mode**

- To enable Flask’s debug mode, update the app.run line in app.py:

- if __name__ == '__main__':
        app.run(debug=True)

This auto-reloads the server on code changes and provides detailed error pages.

## Testing (Optional)

If you have a tests/ folder with Pytest tests, you can run:

`pytest`
This will discover and run all tests in the project.

## Project Structure

A typical layout might look like this:

final_project/
├── app.py
├── models.py
├── requirements.txt
├── README.md
├── static/
│   └── css/
│       └── style.css
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── login.html
│   ├── register.html
│   ├── edit_expense.html
│   └── navbar.html
└── tests/
    └── test_app.py

## Common Troubleshooting

- Port Already in Use:
    - Run lsof -i :5000 on macOS or Linux to find and kill the process, or just change the port in app.run.

- Lockout Not Persisting:
    - If you’re using in-memory lockout data, it resets on server restart. Consider storing lockout info in the database for production.

- Cannot Edit or Delete Expenses:
    - Ensure you’re logged in and that the routes (/edit-expense/<id> or /delete-expense/<id>) exist and match the buttons in your templates.

## License

MIT License