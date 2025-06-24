# timetrack/database.py
import sqlite3
from datetime import datetime
from typing import List, Optional

from TIMETRACK.model import Sheet, Entry

DATABASE_FILE = "timetrack.db" # Or dynamically get this from a config

def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            note TEXT,
            FOREIGN KEY (sheet_id) REFERENCES sheets (id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()

# --- Sheet Operations ---
def insert_sheet(sheet_name: str) -> Optional[Sheet]:
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO sheets (name) VALUES (?)", (sheet_name,))
        sheet_id = cursor.lastrowid
        conn.commit()
        return Sheet(name=sheet_name, id=sheet_id)
    except sqlite3.IntegrityError:
        print(f"Sheet '{sheet_name}' already exists.")
        return get_sheet_by_name(sheet_name)
    finally:
        conn.close()

def get_sheet_by_name(sheet_name: str) -> Optional[Sheet]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sheets WHERE name = ?", (sheet_name,))
    row = cursor.fetchone()
    conn.close()
    return Sheet(id=row['id'], name=row['name']) if row else None

def get_sheet_by_id(sheet_id: int) -> Optional[Sheet]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sheets WHERE id = ?", (sheet_id,))
    row = cursor.fetchone()
    conn.close()
    return Sheet(id=row['id'], name=row['name']) if row else None

def get_all_sheets() -> List[Sheet]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM sheets ORDER BY name")
    sheets = [Sheet(id=row['id'], name=row['name']) for row in cursor.fetchall()]
    conn.close()
    return sheets

# --- Entry Operations ---
def insert_entry(entry: Entry) -> Entry:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO entries (sheet_id, start_time, end_time, note) VALUES (?, ?, ?, ?)",
        (entry.sheet_id, entry.start_time.isoformat(),
         entry.end_time.isoformat() if entry.end_time else None, entry.note)
    )
    entry.id = cursor.lastrowid
    conn.commit()
    conn.close()
    return entry

def update_entry(entry_id: int,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None,
                 note: Optional[str] = None) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    updates = []
    params = []

    if start_time is not None:
        updates.append("start_time = ?")
        params.append(start_time.isoformat())
    if end_time is not None:
        updates.append("end_time = ?")
        params.append(end_time.isoformat())
    if note is not None:
        updates.append("note = ?")
        params.append(note)

    if not updates:
        conn.close()
        return False

    sql = f"UPDATE entries SET {', '.join(updates)} WHERE id = ?"
    params.append(entry_id)

    cursor.execute(sql, tuple(params))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def get_entry_by_id(entry_id: int) -> Optional[Entry]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sheet_id, start_time, end_time, note FROM entries WHERE id = ?", (entry_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Entry(
            id=row['id'],
            sheet_id=row['sheet_id'],
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
            note=row['note']
        )
    return None

def get_running_entries() -> List[Entry]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, sheet_id, start_time, end_time, note FROM entries WHERE end_time IS NULL")
    entries = [
        Entry(
            id=row['id'],
            sheet_id=row['sheet_id'],
            start_time=datetime.fromisoformat(row['start_time']),
            end_time=None,
            note=row['note']
        ) for row in cursor.fetchall()
    ]
    conn.close()
    return entries

def get_entries_for_sheet(sheet_id: int, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Entry]:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql = "SELECT id, sheet_id, start_time, end_time, note FROM entries WHERE sheet_id = ?"
    params = [sheet_id]

    if start_time:
        sql += " AND start_time >= ?"
        params.append(start_time.isoformat())
    if end_time:
        sql += " AND start_time <= ?" # Or end_time <= ? depending on desired filtering
        params.append(end_time.isoformat())

    sql += " ORDER BY start_time DESC"

    cursor.execute(sql, tuple(params))
    entries = []
    for row in cursor.fetchall():
        entries.append(
            Entry(
                id=row['id'],
                sheet_id=row['sheet_id'],
                start_time=datetime.fromisoformat(row['start_time']),
                end_time=datetime.fromisoformat(row['end_time']) if row['end_time'] else None,
                note=row['note']
            )
        )
    conn.close()
    return entries

def delete_sheet(sheet_name: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sheets WHERE name = ?", (sheet_name,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

def delete_entry(entry_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    conn.close()
    return rows_affected > 0

# Call this once at the start of your application
create_tables()