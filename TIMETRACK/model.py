# timetrack/model.py
from datetime import datetime
from typing import Optional

class Sheet:
    def __init__(self, name: str, id: Optional[int] = None):
        self.id = id
        self.name = name

    def __repr__(self):
        return f"<Sheet(id={self.id}, name='{self.name}')>"

class Entry:
    def __init__(self,
                 sheet_id: int,
                 start_time: datetime,
                 end_time: Optional[datetime] = None,
                 note: Optional[str] = None,
                 id: Optional[int] = None):
        self.id = id
        self.sheet_id = sheet_id
        self.start_time = start_time
        self.end_time = end_time
        self.note = note

    def __repr__(self):
        return (f"<Entry(id={self.id}, sheet_id={self.sheet_id}, "
                f"start_time={self.start_time}, end_time={self.end_time}, "
                f"note='{self.note}')>")