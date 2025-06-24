# TODO/todo_app.py
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from typing import Optional, List

from TODO.model import Todo
from TODO.database import (
    create_tables, insert_todo, get_all_todos, delete_todo,
    update_todo, complete_todo, set_status, search_todos
)

console = Console()

todo_app = typer.Typer(help="A powerful command-line ToDo list application.")

# --- Typer Callback for TODO App Initialization ---
@todo_app.callback()
def todo_main_callback():
    """
    Initializes the ToDo application.
    Ensures the database tables are created or updated before any command runs.
    """
    create_tables()


def short_date(date_str: Optional[str]) -> str:
    """Convert ISO datetime to DD-MM-YYYY format, handles None gracefully."""
    if date_str is None: # Check for Python None explicitly
        return "-"
    if date_str == 'None': # Handle the string 'None' that might come from older DB entries
        return "-"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        try: # Try parsing only the date part if full iso fails
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            return "-" # Return hyphen for unparseable dates


@todo_app.command()
def add(
    task: str = typer.Option(...,
        prompt="Task",
        help="The detailed description of the task to be added. This is a required field."
    ),
    priority: str = typer.Option("medium",
        prompt="Priority (low/medium/high)",
        show_choices=True,
        help="The priority level of the task. Choose from 'low', 'medium', or 'high'. Defaults to 'medium'."
    ),
    due: Optional[str] = typer.Option(None,
        prompt="Due Date (YYYY-MM-DD or type 'none')", # Updated prompt
        show_default=False,
        help="The due date for the task in YYYY-MM-DD format. Type 'none' if no due date."
    ),
    status: str = typer.Option("pending",
        prompt="Status (pending/in-progress/done)",
        show_choices=True,
        help="The initial status of the task. Choose from 'pending', 'in-progress', or 'done'. Defaults to 'pending'."
    ),
    repeat: Optional[str] = typer.Option(None,
        prompt="Repeat (daily/weekly/monthly/none)",
        show_default=False,
        help="Sets a recurrence pattern for the task. Choose from 'daily', 'weekly', 'monthly', or 'none'. Type 'none' for no repeat."
    )
):
    """
    Adds a new task to your ToDo list.

    This command allows you to specify the task description, priority,
    due date, initial status, and an optional recurrence pattern.
    """
    # Manual validation and normalization
    priority = priority.lower().strip()
    if priority not in ["low", "medium", "high"]:
        console.print("[bold red]Error:[/bold red] Invalid priority. Please choose from: [green]low[/green], [yellow]medium[/yellow], [red]high[/red].")
        raise typer.Exit(code=1)

    status = status.lower().strip()
    if status not in ["pending", "in-progress", "done"]:
        console.print("[bold red]Error:[/bold red] Invalid status. Please choose from: [blue]pending[/blue], [yellow]in-progress[/yellow], [green]done[/green].")
        raise typer.Exit(code=1)

    repeat = repeat.lower().strip() if repeat else None # Convert empty string to None
    if repeat == 'none': # User might type 'none' to signify no repeat
        repeat = None
    if repeat not in [None, "daily", "weekly", "monthly"]:
        console.print("[bold red]Error:[/bold red] Invalid recurrence. Choose from: [cyan]daily[/cyan], [cyan]weekly[/cyan], [cyan]monthly[/cyan], or type 'none'.")
        raise typer.Exit(code=1)

    # --- Start of fix for 'Due Date' handling ---
    parsed_due_date = None
    if due: # If user provided any input for 'due'
        stripped_due = due.lower().strip()
        if stripped_due == "none" or stripped_due == "leave blank": # Explicitly check for "none" or "leave blank"
            parsed_due_date = None
        else:
            try:
                # Ensure due is YYYY-MM-DD format and convert to ISO for consistency
                parsed_due_date = datetime.strptime(due, "%Y-%m-%d").date().isoformat()
            except ValueError:
                console.print("[bold red]Error:[/bold red] Invalid due date format. Please use YYYY-MM-DD or type 'none' to leave blank.")
                raise typer.Exit(code=1)
    # --- End of fix for 'Due Date' handling ---

    created_date = datetime.today().date().isoformat()
    console.print(f"Adding task: '[bold green]{task}[/bold green]' with priority [bold {priority}]{priority}[/bold {priority}], due by {parsed_due_date or 'N/A'}, status [bold {status}]{status}[/bold {status}], repeating {repeat or 'none'}.")
    
    todo = Todo(task=task, priority=priority, due_date=parsed_due_date, status=status, date_added=created_date, recurrence=repeat)
    insert_todo(todo)
    show()

@todo_app.command()
def delete(position: int = typer.Argument(..., help="The #ID of the task to delete (as shown in 'todo show').")):
    """
    Deletes a task from your ToDo list by its position.
    This action is irreversible. The position refers to the #ID column in 'todo show'.
    """
    all_todos = get_all_todos()
    if 0 < position <= len(all_todos) and all_todos[position-1].id is not None:
        todo_id = all_todos[position-1].id
        if delete_todo(todo_id):
            console.print(f"Task at position [bold yellow]{position}[/bold yellow] (ID: {todo_id}) deleted.")
        else:
            console.print(f"[bold red]Error:[/bold red] Task at position [bold yellow]{position}[/bold yellow] (ID: {todo_id}) not found or could not be deleted.")
    else:
        console.print("[bold red]Error:[/bold red] Invalid task position or task not found.")
        raise typer.Exit(code=1)
    show()

@todo_app.command()
def update(
    position: int = typer.Argument(..., help="The #ID of the task to update."),
    task: Optional[str] = typer.Option(None, help="New task description."),
    priority: Optional[str] = typer.Option(None, help="New priority (low/medium/high)."),
    due: Optional[str] = typer.Option(None, help="New due date (YYYY-MM-DD). Set to 'none' to clear."),
    status: Optional[str] = typer.Option(None, help="New status (pending/in-progress/done)."),
    repeat: Optional[str] = typer.Option(None, help="New recurrence pattern (daily/weekly/monthly/none). Set to 'none' to remove recurrence.")
):
    """
    Updates an existing task by its position.

    You can update the task description, priority, due date, status, or recurrence.
    Only provided options will be updated.
    The position refers to the #ID column in 'todo show'.
    """
    all_todos = get_all_todos()
    if not (0 < position <= len(all_todos) and all_todos[position-1].id is not None):
        console.print("[bold red]Error:[/bold red] Invalid task position or task not found.")
        raise typer.Exit(code=1)

    todo_to_update = all_todos[position - 1]
    todo_id = todo_to_update.id

    # Validate inputs before attempting update
    update_params = {}

    if task is not None:
        update_params['task'] = task

    if priority is not None:
        priority_lower = priority.lower().strip()
        if priority_lower not in ["low", "medium", "high"]:
            console.print("[bold red]Error:[/bold red] Invalid priority. Not updating.")
            raise typer.Exit(code=1)
        update_params['priority'] = priority_lower
    
    if status is not None:
        status_lower = status.lower().strip()
        if status_lower not in ["pending", "in-progress", "done"]:
            console.print("[bold red]Error:[/bold red] Invalid status. Not updating.")
            raise typer.Exit(code=1)
        update_params['status'] = status_lower
        # If status is set to done, record completion date; otherwise, clear it
        if status_lower == "done":
            update_params['date_completed'] = datetime.today().date().isoformat()
        elif todo_to_update.date_completed is not None: # Only clear if it currently has a date
            update_params['date_completed'] = None
    
    if due is not None:
        if due.lower().strip() == 'none': # Special string to clear the due date
            update_params['due_date'] = None
        else:
            try:
                # Ensure due is YYYY-MM-DD format and convert to ISO for consistency
                update_params['due_date'] = datetime.strptime(due, "%Y-%m-%d").date().isoformat()
            except ValueError:
                console.print("[bold red]Error:[/bold red] Invalid due date format. Please use YYYY-MM-DD or type 'none' to clear. Not updating.")
                raise typer.Exit(code=1)

    if repeat is not None:
        repeat_lower = repeat.lower().strip()
        if repeat_lower == 'none': # User typed 'none' to signify no repeat
            update_params['recurrence'] = None
        elif repeat_lower not in ["daily", "weekly", "monthly"]:
            console.print("[bold red]Error:[/bold red] Invalid recurrence. Choose from: [cyan]daily[/cyan], [cyan]weekly[/cyan], [cyan]monthly[/cyan], or 'none'. Not updating.")
            raise typer.Exit(code=1)
        else:
            update_params['recurrence'] = repeat_lower
        
    if not update_params:
        console.print("[bold yellow]Warning:[/bold yellow] No update options provided.")
        raise typer.Exit()

    # Perform update using database function
    updated = update_todo(todo_id=todo_id, **update_params)
    
    if updated:
        console.print(f"Task at position [bold green]{position}[/bold green] (ID: {todo_id}) updated.")
    else:
        console.print(f"[bold yellow]Warning:[/bold yellow] No changes applied or task not found at position [bold yellow]{position}[/bold yellow] (ID: {todo_id}).")
    show()

@todo_app.command()
def complete(position: int = typer.Argument(..., help="The #ID of the task to mark as complete.")):
    """
    Marks a task as complete by its position.

    This sets the task's status to 'done' and records the completion date.
    The position refers to the #ID column in 'todo show'.
    """
    all_todos = get_all_todos()
    if 0 < position <= len(all_todos) and all_todos[position-1].id is not None:
        todo_id = all_todos[position-1].id
        complete_todo(todo_id)
        console.print(f"Task at position [bold green]{position}[/bold green] (ID: {todo_id}) marked as [bold green]done[/bold green].")
    else:
        console.print("[bold red]Error:[/bold red] Invalid task position or task not found.")
        raise typer.Exit(code=1)
    show()

@todo_app.command()
def setstatus(
    position: int = typer.Argument(..., help="The #ID of the task to change status for."),
    status: str = typer.Argument(..., help="The new status (pending/in-progress/done).", show_choices=True)
):
    """
    Sets the status of a task.

    You can set the task's status to 'pending', 'in-progress', or 'done'.
    The position refers to the #ID column in 'todo show'.
    """
    status_lower = status.lower().strip()
    if status_lower not in ["pending", "in-progress", "done"]:
        console.print("[bold red]Error:[/bold red] Invalid status. Please choose from: [blue]pending[/blue], [yellow]in-progress[/yellow], [green]done[/green].")
        raise typer.Exit(code=1)
    
    all_todos = get_all_todos()
    if 0 < position <= len(all_todos) and all_todos[position-1].id is not None:
        todo_id = all_todos[position-1].id
        set_status(todo_id, status_lower)
        console.print(f"Task at position [bold green]{position}[/bold green] (ID: {todo_id}) status set to [bold {status_lower}]{status_lower}[/bold {status_lower}].")
    else:
        console.print("[bold red]Error:[/bold red] Invalid task position or task not found.")
        raise typer.Exit(code=1)
    show()

@todo_app.command()
def show():
    """
    Displays all tasks in your ToDo list.

    This provides a comprehensive view of all your tasks, regardless of their status.
    """
    tasks = get_all_todos()
    display_todos(tasks)

@todo_app.command()
def search(keyword: str = typer.Argument(..., help="Keyword to search for in task, priority, due date, status, or recurrence.")):
    """
    Search tasks by keyword.

    Finds tasks where the keyword appears in the task description, priority, due date, status, or recurrence.
    """
    results = search_todos(keyword)
    if not results:
        console.print(f"No matching tasks found for keyword '[italic]{keyword}[/italic]'.")
    else:
        console.print(f"Found [bold green]{len(results)}[/bold green] matching task(s) for '[italic]{keyword}[/italic]':")
        display_todos(results)

@todo_app.command()
def repeat():
    """
    Generates new instances of recurring tasks.

    It checks for tasks marked 'done' with a recurrence pattern and creates new pending tasks for their next due date.
    This helps in automating repetitive task management.
    """
    tasks = get_all_todos()
    today = datetime.today().date()
    generated_count = 0

    for task in tasks:
        if task.status == "done" and task.recurrence and task.recurrence.lower() != "none":
            # Determine base date
            base_str = task.date_completed or task.date_added
            try:
                base_date = datetime.fromisoformat(base_str).date()
            except Exception:
                console.print(f"[yellow]⚠ Could not parse date for task: {task.task}[/yellow]")
                continue

            # Get next due date
            if task.recurrence == "daily":
                next_due = base_date + timedelta(days=1)
            elif task.recurrence == "weekly":
                next_due = base_date + timedelta(weeks=1)
            elif task.recurrence == "monthly":
                next_due = base_date + relativedelta(months=1)
            else:
                continue

            # Make sure next due date is not in the past
            while next_due < today:
                if task.recurrence == "daily":
                    next_due += timedelta(days=1)
                elif task.recurrence == "weekly":
                    next_due += timedelta(weeks=1)
                elif task.recurrence == "monthly":
                    next_due += relativedelta(months=1)

            # Prevent duplicate future/pending tasks
            duplicate = False
            for existing in tasks:
                if (
                    existing.task == task.task and
                    existing.status != "done" and
                    existing.recurrence == task.recurrence
                ):
                    if existing.due_date:
                        try:
                            existing_due = datetime.fromisoformat(existing.due_date).date()
                            if existing_due >= next_due:
                                duplicate = True
                                break
                        except Exception:
                            pass

            if duplicate:
                continue

            # Create new task
            new_task = Todo(
                task=task.task,
                priority=task.priority,
                due_date=next_due.isoformat(),
                date_added=next_due.isoformat(),  # ✅ ensures calendar/week shows correctly
                status="pending",
                recurrence=task.recurrence
            )
            insert_todo(new_task)
            generated_count += 1
            console.print(f"[green]✓ New task generated:[/green] {new_task.task} → [yellow]{next_due.isoformat()}[/yellow]")

    if generated_count == 0:
        console.print("[cyan]No recurring tasks generated.[/cyan]")
    else:
        console.print(f"[bold green]{generated_count}[/bold green] task(s) added.")

    show()

@todo_app.command("now")
def show_now_todos():
    """
    Displays tasks that are currently 'in-progress' or 'pending' and due today/overdue.

    This provides a quick overview of what you should be focusing on right now.
    """
    all_tasks = get_all_todos()
    now_tasks: List[Todo] = []
    today = datetime.today().date()

    for task in all_tasks:
        if task.status == "in-progress":
            now_tasks.append(task)
        elif task.status == "pending":
            if task.due_date:
                try:
                    # Parse due_date in ISO format, then compare
                    due_date_dt = datetime.fromisoformat(task.due_date).date()
                    if due_date_dt <= today: # Due today or overdue
                        now_tasks.append(task)
                except ValueError:
                    # Ignore tasks with unparseable due dates that might come from older DB entries
                    pass
            else: # If a pending task has no due date, it's always 'now' for consideration
                now_tasks.append(task)
    
    if not now_tasks:
        console.print("No tasks currently [bold yellow]in-progress[/bold yellow] or [bold blue]pending[/bold blue] and [bold red]due today/overdue[/bold red]. You're all caught up!")
        return
    
    # Sort tasks: in-progress first, then by priority (high, medium, low), then by due date
    now_tasks.sort(key=lambda t: (
        0 if t.status == "in-progress" else 1, # In-progress first (0)
        {"high": 0, "medium": 1, "low": 2}.get(t.priority.lower(), 3), # Priority order (0, 1, 2, 3)
        # Handle cases where due_date might be None (or "None" string, though short_date fixes that)
        datetime.fromisoformat(t.due_date).date() if t.due_date and t.due_date != 'None' else datetime.max.date() # Earliest due first
    ))

    console.print("[bold green]Tasks for now:[/bold green]")
    display_todos(now_tasks)


def display_todos(tasks: List[Todo]):
    """
    Helper function to display a list of Todo objects in a Rich table.
    """
    if not tasks:
        console.print("No tasks to display.")
        return

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("#", width=4)
    table.add_column("Task", style="bold")
    table.add_column("Due", justify="center")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Date Added", justify="center")
    table.add_column("Repeat", justify="center")

    # Style helper
    def apply_style(text: str, style: str) -> str:
        return f"[{style}]{text}[/{style}]" if style else text

    # Color mapping
    priority_colors = {"low": "green", "medium": "yellow", "high": "red"}
    status_colors = {"pending": "blue", "in-progress": "yellow", "done": "green"}
    status_icons = {"pending": "🕒", "in-progress": "🔄", "done": "✅"}

    for idx, task in enumerate(tasks, start=1):
        safe_priority = task.priority if isinstance(task.priority, str) else "medium"
        safe_status = task.status if isinstance(task.status, str) else "pending"

        priority_style = priority_colors.get(safe_priority.lower(), "white")
        status_style = status_colors.get(safe_status.lower(), "white")
        status_text = apply_style(f"{status_icons.get(safe_status, '')} {safe_status}", status_style)

        # Row highlight
        row_style = ""
        if safe_status == "done":
            row_style = "dim"
        elif safe_status == "in-progress":
            row_style = "bold yellow"
        elif safe_status == "pending" and task.due_date:
            try:
                due_date_dt = datetime.fromisoformat(task.due_date).date()
                today = datetime.today().date()
                if due_date_dt < today:
                    row_style = "bold red"
                elif due_date_dt == today:
                    row_style = "bold magenta"
            except ValueError:
                pass

        table.add_row(
            apply_style(str(idx), row_style),
            apply_style(task.task, row_style),
            apply_style(short_date(task.due_date), row_style),
            apply_style(safe_priority, priority_style),
            status_text,
            apply_style(short_date(task.date_added), row_style),
            apply_style(task.recurrence or "-", row_style),
        )

    console.print(table)

# This __main__ block is for direct testing of todo_app.py if needed,
# but the primary way to run is via main.py.
if __name__ == "__main__":
    todo_app()

