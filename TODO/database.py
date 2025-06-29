# TODO/database.py
import sqlite3
from typing import List, Optional, Any, Dict, Union
from datetime import datetime
from .model import Todo

DATABASE_NAME = "todo_list.db"

def get_db_connection():
    """Establishes and returns a database connection."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """
    Creates the database tables if they don't exist.
    Handles schema migrations gracefully, like adding the 'alias' column
    and its unique index without causing errors on existing databases.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the main todos table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            status TEXT DEFAULT 'pending',
            date_added TEXT,
            date_completed TEXT,
            recurrence TEXT,
            parent_id INTEGER,
            alias TEXT,
            FOREIGN KEY (parent_id) REFERENCES todos(id) ON DELETE CASCADE
        )
    """)

    # --- Schema Migration for Alias Column ---
    # This is the safe way to add a unique column to an existing table.
    
    # 1. Add the column first, without the UNIQUE constraint
    try:
        cursor.execute("ALTER TABLE todos ADD COLUMN alias TEXT")
    except sqlite3.OperationalError as e:
        if "duplicate column name: alias" not in str(e):
            raise # Re-raise if it's not the expected "column already exists" error
    
    # 2. Create a unique index on the alias column.
    # This will fail if there are existing non-NULL duplicate aliases.
    # If a real-world app, you'd handle duplicates before adding the constraint.
    # For a CLI tool, it's simpler to assume uniqueness will be managed by app logic.
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_alias ON todos (alias) WHERE alias IS NOT NULL")
    except sqlite3.OperationalError as e:
        if "index idx_alias already exists" not in str(e):
            raise
    
    conn.commit()
    conn.close()

def insert_todo(todo: Todo) -> Optional[int]:
    """Inserts a new ToDo into the database and returns its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO todos (task, priority, due_date, status, date_added, date_completed, recurrence, parent_id, alias)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            todo.task, todo.priority, todo.due_date, todo.status, todo.date_added,
            todo.date_completed, todo.recurrence, todo.parent_id, todo.alias
        ))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: todos.alias" in str(e):
            print(f"[red]Error: An item with alias '{todo.alias}' already exists. Please choose a different alias.[/red]")
        else:
            print(f"[red]Database Error: {e}[/red]")
        return None
    finally:
        conn.close()

def update_todo(todo_id: int, **kwargs: Any) -> bool:
    """Updates one or more fields of an existing ToDo."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    set_clauses = []
    values = []
    
    # Construct SET clauses and values dynamically
    for key, value in kwargs.items():
        if key in ["task", "priority", "due_date", "status", "date_completed", "recurrence", "parent_id", "alias"]:
            set_clauses.append(f"{key} = ?")
            values.append(value)
        else:
            print(f"[yellow]Warning: Attempted to update non-existent or restricted field: {key}[/yellow]")
            continue

    if not set_clauses: # No valid fields to update
        conn.close()
        return False

    values.append(todo_id) # Add the WHERE clause value
    
    try:
        cursor.execute(f"UPDATE todos SET {', '.join(set_clauses)} WHERE id = ?", values)
        conn.commit()
        return cursor.rowcount > 0 # Returns True if any row was updated
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: todos.alias" in str(e):
            print(f"[red]Error: An item with alias '{kwargs['alias']}' already exists. Please choose a different alias.[/red]")
        else:
            print(f"[red]Database Error: {e}[/red]")
        return False
    finally:
        conn.close()

def delete_todo(todo_id: int) -> bool:
    """Deletes a ToDo from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def complete_todo(todo_id: int) -> bool:
    """Marks a ToDo as complete and sets the completion date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    date_completed = datetime.now().date().isoformat()
    cursor.execute("UPDATE todos SET status = ?, date_completed = ? WHERE id = ?", ("done", date_completed, todo_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def set_status(todo_id: int, status: str) -> bool:
    """Sets the status of a ToDo item."""
    conn = get_db_connection()
    cursor = conn.cursor()
    date_completed = datetime.now().date().isoformat() if status == "done" else None
    cursor.execute("UPDATE todos SET status = ?, date_completed = ? WHERE id = ?", (status, date_completed, todo_id))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0

def get_all_todos() -> List[Todo]:
    """Retrieves all ToDo items from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM todos")
    rows = cursor.fetchall()
    conn.close()
    return [Todo(**row) for row in rows]

def search_todos(keyword: str) -> List[Todo]:
    """
    Searches for ToDo items matching a keyword in task, priority, status, recurrence, or alias.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Using LOWER() for case-insensitive search
    # Using LIKE with '%' for partial matches
    keyword_like = f"%{keyword.lower()}%"
    
    cursor.execute("""
        SELECT * FROM todos
        WHERE LOWER(task) LIKE ? OR
              LOWER(priority) LIKE ? OR
              LOWER(status) LIKE ? OR
              LOWER(recurrence) LIKE ? OR
              LOWER(alias) LIKE ?
    """, (keyword_like, keyword_like, keyword_like, keyword_like, keyword_like))
    
    rows = cursor.fetchall()
    conn.close()
    return [Todo(**row) for row in rows]

def get_children_of_todo(parent_id: int) -> List[Todo]:
    """Retrieves all immediate children of a given parent ToDo."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM todos WHERE parent_id = ?", (parent_id,))
    rows = cursor.fetchall()
    conn.close()
    return [Todo(**row) for row in rows]

def get_todo_by_id_or_alias(identifier: Union[int, str]) -> Optional[Todo]:
    conn = get_db_connection()
    cursor = conn.cursor()

    row = None
    if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
        cursor.execute("SELECT * FROM todos WHERE id = ?", (int(identifier),))
        row = cursor.fetchone()
    else:
        # First try alias
        cursor.execute("SELECT * FROM todos WHERE alias = ?", (identifier,))
        row = cursor.fetchone()

        # 🔁 Fallback: try task name if alias not found
        if not row:
            cursor.execute("SELECT * FROM todos WHERE task = ?", (identifier,))
            row = cursor.fetchone()

    conn.close()
    return Todo(**row) if row else None


def get_todo_by_path_string(path_string: str, all_todos: List[Todo]) -> Optional[Todo]:
    """
    Resolves a task by a path string (e.g., "parent/child/grandchild").
    Looks for alias first, then task name.
    """
    parts = path_string.split('/')
    current_parent_id = None
    target_todo = None

    for i, part in enumerate(parts):
        found_in_step = None
        # In each step, filter by parent_id
        potential_todos = [t for t in all_todos if t.parent_id == current_parent_id]

        # Try matching by alias first, then by task name
        for todo in potential_todos:
            if todo.alias and todo.alias.lower() == part.lower():
                found_in_step = todo
                break
        
        if not found_in_step:
            for todo in potential_todos:
                if todo.task.lower() == part.lower():
                    found_in_step = todo
                    break
        
        if found_in_step:
            target_todo = found_in_step
            current_parent_id = found_in_step.id
        else:
            # Part of the path not found
            return None
            
    return target_todo

def refresh_all_recurring_tasks() -> int:
    """
    Archives old recurring tasks and creates fresh instances for today.
    Returns number of tasks refreshed.
    """
    from .model import Todo
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.today().date()
    today_iso = today.isoformat()

    cursor.execute("""
        SELECT * FROM todos
        WHERE recurrence IN ('daily', 'weekly', 'monthly')
          AND date(date_added) < ?
    """, (today_iso,))
    old_tasks = cursor.fetchall()

    refreshed_count = 0

    for row in old_tasks:
        old = dict(row)
        recurrence = old["recurrence"]
        date_added = datetime.fromisoformat(old["date_added"]).date()

        # Determine if it needs to be refreshed today
        if recurrence == "daily":
            should_create = True
        elif recurrence == "weekly":
            should_create = today.isocalendar()[1] != date_added.isocalendar()[1]
        elif recurrence == "monthly":
            should_create = today.month != date_added.month
        else:
            should_create = False

        # ✅ Don't delete, just archive it
        cursor.execute("UPDATE todos SET status = 'archived' WHERE id = ?", (old["id"],))

        # ✅ Create a new fresh version for today
        if should_create:
            new_task = Todo(
                task=old["task"],
                priority=old["priority"],
                due_date=None,
                status="pending",
                date_added=today_iso,
                date_completed=None,
                recurrence=recurrence,
                parent_id=old["parent_id"],
                alias=old["alias"]
            )

            cursor.execute("""
                INSERT INTO todos (
                    task, priority, due_date, status, date_added,
                    date_completed, recurrence, parent_id, alias
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_task.task,
                new_task.priority,
                new_task.due_date,
                new_task.status,
                new_task.date_added,
                new_task.date_completed,
                new_task.recurrence,
                new_task.parent_id,
                new_task.alias
            ))

            refreshed_count += 1

    conn.commit()
    conn.close()
    return refreshed_count



def delete_past_due_todos() -> int:
    """Deletes non-recurring tasks whose due_date is before today."""
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.today().date().isoformat()

    cursor.execute("""
        DELETE FROM todos
        WHERE due_date IS NOT NULL
          AND date(due_date) < ?
          AND (recurrence IS NULL OR recurrence = '' OR recurrence = 'none')
    """, (today,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count
