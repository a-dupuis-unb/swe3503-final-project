import sqlite3
import os

def migrate():
    """Add has_temp_password column to User table"""
    # Get path to the database file - adjust as needed
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'expense_tracker.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'has_temp_password' not in columns:
            # Add the column
            cursor.execute("ALTER TABLE user ADD COLUMN has_temp_password BOOLEAN DEFAULT 0")
            print("Added has_temp_password column to User table")
        else:
            print("Column has_temp_password already exists")
        
        # Commit the changes
        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()

