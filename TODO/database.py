# TODO/database.py
import sqlite3
from typing import List, Optional
from datetime import datetime
from TODO.model import Todo

DATABASE_FILE = "todos.db"

def get_db_connection():
    """Establishes and returns a new database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # This allows accessing columns by name
    return conn

def create_tables():
    """
    Creates the 'todos' table if it doesn't exist and adds missing columns.
    This function should be called at application startup.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            priority TEXT NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL,
            date_added TEXT NOT NULL,
            date_completed TEXT,
            repeat TEXT -- 'repeat' is the column name in DB for 'recurrence' in model
        )
    """)

    # Add columns if they don't exist (for existing databases that might be old)
    try:
        cursor.execute("ALTER TABLE todos ADD COLUMN repeat TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name: repeat" not in str(e).lower():
            raise
    
    try:
        cursor.execute("ALTER TABLE todos ADD COLUMN date_completed TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name: date_completed" not in str(e).lower():
            raise

    conn.commit()
    conn.close()


def insert_todo(todo: Todo):
    """Inserts a new Todo item into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    # The 'id' is AUTOINCREMENT, so we don't insert it.
    # Ensure None values are passed as actual None, SQLite will store as NULL.
    cursor.execute(
        "INSERT INTO todos (task, priority, due_date, status, date_added, date_completed, repeat) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (todo.task, todo.priority, todo.due_date, todo.status, todo.date_added, todo.date_completed, todo.recurrence)
    )
    todo.id = cursor.lastrowid # Assign the generated ID back to the Todo object
    conn.commit()
    conn.close()

def get_all_todos() -> List[Todo]:
    """Retrieves all Todo items from the database, handling 'None' strings."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, task, priority, due_date, status, date_added, date_completed, repeat FROM todos ORDER BY id")
    todos = []
    for row in cursor.fetchall():
        # Retrieve values and convert string 'None' to Python None
        row_dict = dict(row) # Convert Row object to dict for easier manipulation
        for key in ['due_date', 'date_completed', 'repeat']:
            if row_dict.get(key) == 'None': # If the string 'None' is found
                row_dict[key] = None # Convert to Python None

        todos.append(Todo(
            id=row_dict['id'],
            task=row_dict['task'],
            priority=row_dict['priority'],
            due_date=row_dict['due_date'],
            status=row_dict['status'],
            date_added=row_dict['date_added'],
            date_completed=row_dict['date_completed'],
            recurrence=row_dict['repeat'] # Map 'repeat' from DB to 'recurrence' in model
        ))
    conn.close()
    return todos

def delete_todo(todo_id: int) -> bool:
    """Deletes a todo item by its database ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    rows_affected = cursor.rowcount
    conn.commit()
    conn.close()
    return rows_affected > 0

def update_todo(todo_id: int,
                task: Optional[str] = None,
                priority: Optional[str] = None,
                due_date: Optional[str] = None, # Can be a date string or None
                status: Optional[str] = None,
                date_completed: Optional[str] = None, # Can be a date string or None
                recurrence: Optional[str] = None) -> bool: # Can be a string or None
    """
    Updates an existing todo task's fields in the database by its ID.
    Only fields that are explicitly provided (not None) will be updated.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if task is not None:
        updates.append("task = ?")
        params.append(task)
    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)
    
    # Handle due_date explicitly: if passed as None, set to None; otherwise, use value.
    # This ensures that `due_date=None` in update_todo clears the DB column.
    if 'due_date' in locals() and due_date is None:
        updates.append("due_date = ?")
        params.append(None)
    elif due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)

    if status is not None:
        updates.append("status = ?")
        params.append(status)
    
    # Handle date_completed explicitly: if passed as None, set to None; otherwise, use value.
    if 'date_completed' in locals() and date_completed is None:
        updates.append("date_completed = ?")
        params.append(None)
    elif date_completed is not None:
        updates.append("date_completed = ?")
        params.append(date_completed)

    # Handle recurrence explicitly: if passed as None, set to None; otherwise, use value.
    if 'recurrence' in locals() and recurrence is None:
        updates.append("repeat = ?") # Database column is 'repeat'
        params.append(None)
    elif recurrence is not None:
        updates.append("repeat = ?") # Database column is 'repeat'
        params.append(recurrence)


    if not updates:
        conn.close()
        return False

    sql = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
    params.append(todo_id)

    cursor.execute(sql, tuple(params))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def complete_todo(todo_id: int):
    """Marks a todo item as complete by its ID."""
    completed_date = datetime.today().date().isoformat()
    update_todo(todo_id, status="done", date_completed=completed_date)

def set_status(todo_id: int, status: str):
    """Sets the status of a todo item by its ID."""
    status_lower = status.lower().strip()
    completed_date = datetime.today().date().isoformat() if status_lower == "done" else None
    update_todo(todo_id, status=status_lower, date_completed=completed_date)

def search_todos(keyword: str) -> List[Todo]:
    """Searches for todo items based on a keyword across multiple fields."""
    conn = get_db_connection()
    cursor = conn.cursor()
    search_term = f"%{keyword.lower()}%"
    cursor.execute(
        "SELECT id, task, priority, due_date, status, date_added, date_completed, repeat FROM todos WHERE LOWER(task) LIKE ? OR LOWER(priority) LIKE ? OR LOWER(due_date) LIKE ? OR LOWER(status) LIKE ? OR LOWER(repeat) LIKE ?",
        (search_term, search_term, search_term, search_term, search_term)
    )
    todos = []
    for row in cursor.fetchall():
        row_dict = dict(row) # Convert Row object to dict
        for key in ['due_date', 'date_completed', 'repeat']:
            if row_dict.get(key) == 'None':
                row_dict[key] = None

        todos.append(Todo(
            id=row_dict['id'],
            task=row_dict['task'],
            priority=row_dict['priority'],
            due_date=row_dict['due_date'],
            status=row_dict['status'],
            date_added=row_dict['date_added'],
            date_completed=row_dict['date_completed'],
            recurrence=row_dict['repeat']
        ))
    conn.close()
    return todos
