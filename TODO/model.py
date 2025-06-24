# TODO/model.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class Todo:
    task: str
    priority: str = "medium"  # default: "low", "medium", "high"
    due_date: Optional[str] = None
    status: str = "pending"   # default: "pending", "in-progress", "done"
    date_added: str = field(default_factory=lambda: datetime.now().date().isoformat())
    date_completed: Optional[str] = None
    recurrence: Optional[str] = None # Renamed from 'repeat' in model for clarity, but DB column is 'repeat'
    id: Optional[int] = None # Added 'id' to capture database primary key

    # Adding a post-init method to ensure status is always lowercased and valid on creation
    def __post_init__(self):
        self.status = self.status.lower().strip()
        if self.status not in ["pending", "in-progress", "done"]:
            self.status = "pending" # Default to pending if invalid status is somehow passed

        self.priority = self.priority.lower().strip()
        if self.priority not in ["low", "medium", "high"]:
            self.priority = "medium" # Default if invalid priority

        if self.recurrence is not None:
            self.recurrence = self.recurrence.lower().strip()
            if self.recurrence not in ["daily", "weekly", "monthly", "none"]:
                self.recurrence = None # Default if invalid recurrence


    def __repr__(self):
        return (f"Todo(id={self.id}, task='{self.task}', priority='{self.priority}', "
                f"due_date='{self.due_date}', status='{self.status}', "
                f"date_added='{self.date_added}', date_completed='{self.date_completed}', "
                f"recurrence='{self.recurrence}')")

    def to_dict(self):
        # Useful for debugging or if you ever need to serialize
        return {
            "id": self.id,
            "task": self.task,
            "priority": self.priority, # Ensured priority is here
            "due_date": self.due_date,
            "status": self.status,
            "date_added": self.date_added,
            "date_completed": self.date_completed,
            "recurrence": self.recurrence
        }
