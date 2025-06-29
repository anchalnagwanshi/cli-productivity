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
    parent_id: Optional[int] = None # For parent-child task relationships
    alias: Optional[str] = None # NEW: Optional shortcode/alias for the task

    def __post_init__(self):
        self.status = self.status.lower().strip()
        if self.status not in ["pending", "in-progress", "done", "archived"]:
            self.status = "pending"


        self.priority = self.priority.lower().strip()
        if self.priority not in ["low", "medium", "high"]:
            self.priority = "medium" 


        if self.recurrence:
            self.recurrence = self.recurrence.lower().strip()
            if self.recurrence not in ["daily", "weekly", "monthly", "none"]:
                self.recurrence = None 
        
       
        if self.alias:
            self.alias = self.alias.strip().lower().replace(" ", "-") 
            if not self.alias: 
                self.alias = None
        else:
            self.alias = None


    def __repr__(self):
        return (f"Todo(id={self.id}, task='{self.task}', priority='{self.priority}', "
                f"due_date='{self.due_date}', status='{self.status}', "
                f"date_added='{self.date_added}', date_completed='{self.date_completed}', "
                f"recurrence='{self.recurrence}', parent_id={self.parent_id}, alias='{self.alias}')")

    def to_dict(self):
        return {
            "id": self.id,
            "task": self.task,
            "priority": self.priority,
            "due_date": self.due_date,
            "status": self.status,
            "date_added": self.date_added,
            "date_completed": self.date_completed,
            "recurrence": self.recurrence,
            "parent_id": self.parent_id,
            "alias": self.alias
        }