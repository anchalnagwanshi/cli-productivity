# TODO/todo_app.py - MODIFIED
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box # For better table borders
from datetime import datetime, timedelta
from typing import Optional, List
from collections import defaultdict
from prodcli.TODO.database import delete_past_due_todos, refresh_all_recurring_tasks
from prodcli.TODO.database import get_all_todos
from prodcli.TODO.database import get_children_of_todo, update_todo
from prodcli.TODO.model import Todo
from prodcli.TODO.database import (
    create_tables, insert_todo, get_all_todos, delete_todo,
    update_todo, complete_todo, set_status, search_todos, get_children_of_todo,
    get_todo_by_id_or_alias 
)

console = Console()

todo_app = typer.Typer(help="A powerful command-line ToDo list application.")

@todo_app.callback()
def todo_main_callback():
    """
    Initializes the ToDo application.
    Ensures the database tables are created or updated before any command runs.
    """
    create_tables()


def short_date(date_str: Optional[str]) -> str:
    """Convert ISO datetime to DD-MM-YYYY format, handles None/string 'None' gracefully."""
    if date_str is None or date_str == 'None':
        return "-"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return date_str 


@todo_app.command("add")
def add_todo(
    task: str = typer.Argument(..., help="The description of the ToDo item."),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority of the task (low, medium, high)."),
    due_date: Optional[str] = typer.Option(None, "--due", "-d", help="Due date (YYYY-MM-DD)."),
    status: str = typer.Option("pending", "--status", "-s", help="Status of the task (pending, in-progress, done)."),
    recurrence: Optional[str] = typer.Option(None, "--repeat", "-r", help="Recurrence pattern (daily, weekly, monthly)."),
    parent_identifier: Optional[str] = typer.Option(None, "--parent", "-P", help="ID or alias of parent task."),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="Optional shortcode/alias for the task. Must be unique.")
):
    """Add a new ToDo item."""
    if due_date:
        try:
            datetime.fromisoformat(due_date).date()
        except ValueError:
            console.print("[red]Error: Due date must be in YYYY-MM-DD format.[/red]")
            raise typer.Exit(code=1)

    parent_id = None
    if parent_identifier:
        parent_todo = get_todo_by_id_or_alias(parent_identifier)
        if parent_todo:
            parent_id = parent_todo.id

            if not recurrence and parent_todo.recurrence:
                recurrence = parent_todo.recurrence
        else:
            console.print(f"[yellow]Warning: Parent task '{parent_identifier}' not found. Adding as a top-level task.[/yellow]")


    new_todo = Todo(
        task=task,
        priority=priority,
        due_date=due_date,
        status=status,
        date_added=datetime.now().date().isoformat(),
        recurrence=recurrence,
        parent_id=parent_id,
        alias=alias
    )
    insert_todo(new_todo)
    console.print(f"[green]Added ToDo: '{new_todo.task}'[/green]")


@todo_app.command("list")
def list_todos():
    """
    List today's ToDo items.
    Only shows tasks that are pending or in-progress and due today,
    or recurring tasks relevant for today that are not yet done.
    """
    all_todos = [t for t in get_all_todos() if t.status != "archived"]
    today_iso = datetime.now().date().isoformat()
    today_date = datetime.now().date()

    filtered_todos = []
    children_map = defaultdict(list)
    
    # Helper to check if a recurring task is relevant for today
    def is_recurring_today(todo: Todo, current_date: datetime.date) -> bool:
        if not todo.recurrence:
            return False
        
        task_start_date = datetime.fromisoformat(todo.date_added).date()
        if current_date < task_start_date:
            return False

        if todo.recurrence == "daily":
            return True
        elif todo.recurrence == "weekly":
            start_of_task_week = task_start_date - timedelta(days=task_start_date.weekday())
            start_of_current_week = current_date - timedelta(days=current_date.weekday())
            return start_of_current_week >= start_of_task_week
        elif todo.recurrence == "monthly":
            return current_date.day == task_start_date.day
        return False

    temp_children_map = defaultdict(list)
    for todo in all_todos:
        temp_children_map[todo.parent_id].append(todo)

    display_todo_ids = set()

    for todo in all_todos:
        should_display = False
        if (todo.status == "pending" or todo.status == "in-progress") and todo.due_date == today_iso:
            should_display = True
        elif todo.recurrence and is_recurring_today(todo, today_date) and \
             not (todo.status == "done" and todo.date_completed == today_iso):
            should_display = True

        if should_display:
            display_todo_ids.add(todo.id)
            if todo.parent_id: 
                current_id = todo.id
                while current_id is not None:
                    parent_id = None
                    for t in all_todos:
                        if t.id == current_id and t.parent_id is not None:
                            parent_id = t.parent_id
                            break
                    if parent_id is not None:
                        display_todo_ids.add(parent_id)
                        current_id = parent_id
                    else:
                        current_id = None 

    for todo in all_todos:
        if todo.id in display_todo_ids:
            filtered_todos.append(todo)
            children_map[todo.parent_id].append(todo)
    
    if not filtered_todos:
        console.print("[yellow]No ToDo items for today.[/yellow]")
        return

    for parent_id in children_map:
        children_map[parent_id].sort(key=lambda t: t.id if t.id is not None else float('inf'))

    table = Table(
        title=f"[bold cyan]Your ToDo List for Today ({today_iso})[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
        show_lines=True
    )
    table.add_column("ID / Alias", justify="center", style="dim")
    table.add_column("Task", justify="left")
    table.add_column("Due Date", justify="center")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Added Date", justify="center")
    table.add_column("Repeat", justify="center")

    def add_task_rows_recursive(tasks: List[Todo], level: int = 0):
        for task in tasks:
            indent = "  " * level
            task_text = f"{indent}{task.task}"
            row_style = ""
            status_text = Text(task.status.capitalize(), style="white")
            priority_style = "white" 

            if task.status == "done":
                row_style = "strike dim"
                status_text = Text("✔ Done", style="green")
            elif task.status == "in-progress":
                status_text = Text("In Progress", style="blue")
            elif task.status == "pending":
                if task.due_date:
                    try:
                        if datetime.fromisoformat(task.due_date).date() < datetime.now().date():
                            row_style = "red bold"
                            status_text = Text("Overdue", style="red bold")
                    except ValueError:
                        pass 

            if task.priority == "high":
                priority_style = "bold red"
            elif task.priority == "medium":
                priority_style = "yellow"
            elif task.priority == "low":
                priority_style = "green"
            
            safe_priority = task.priority.capitalize() if task.priority else "Medium"


            if task.parent_id:
                id_alias_display = f"{indent}↳"
            else:
                id_alias_display = "•"
            priority_display = safe_priority
            due_display = short_date(task.due_date) if task.due_date else "-"
            repeat_display = task.recurrence or "-"



            table.add_row(
                Text(id_alias_display, style=row_style), 
                Text(task_text, style=row_style),
                Text(due_display, style=row_style),
                Text(priority_display, style=priority_style),
                status_text,
                Text(short_date(task.date_added), style=row_style),
                Text(repeat_display, style=row_style)
            )
            
            if task.id in children_map and children_map[task.id]:
                add_task_rows_recursive(children_map[task.id], level + 1)
    
    top_level_tasks = children_map[None]
    add_task_rows_recursive(top_level_tasks)

    console.print(table)


@todo_app.command("update")
def update_todo_command(
    identifier: str = typer.Argument(..., help="The ID or alias of the ToDo to update."),
    task: Optional[str] = typer.Option(None, "--task", "-t", help="New task description."),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority (low, medium, high)."),
    due_date: Optional[str] = typer.Option(None, "--due", "-d", help="New due date (YYYY-MM-DD). Set to 'none' to clear."),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status (pending, in-progress, done)."),
    recurrence: Optional[str] = typer.Option(None, "--repeat", "-r", help="New recurrence pattern (daily, weekly, monthly). Set to 'none' to clear."),
    parent_identifier: Optional[str] = typer.Option(None, "--parent", "-P", help="ID or alias of parent task. Set to 'none' to clear parent."),
    alias: Optional[str] = typer.Option(None, "--alias", "-a", help="New alias for the task. Set to 'none' to clear.")
):
    """Update an existing ToDo item by its ID or alias."""
    todo_obj = get_todo_by_id_or_alias(identifier)
    if not todo_obj:
        console.print(f"[red]Error: ToDo '{identifier}' not found.[/red]")
        raise typer.Exit(code=1)

    update_params = {}
    if task is not None:
        update_params["task"] = task
    if priority is not None:
        update_params["priority"] = priority
    if due_date is not None:
        if due_date.lower() == 'none':
            update_params["due_date"] = None
        else:
            try:
                datetime.fromisoformat(due_date).date()
                update_params["due_date"] = due_date
            except ValueError:
                console.print("[red]Error: Due date must be in YYYY-MM-DD format or 'none'.[/red]")
                raise typer.Exit(code=1)
    if status is not None:
        update_params["status"] = status
    if recurrence is not None:
        if recurrence.lower() == 'none':
            update_params["recurrence"] = None
        else:
            update_params["recurrence"] = recurrence
    if alias is not None:
        if alias.lower() == 'none':
            update_params["alias"] = None
        else:
            update_params["alias"] = alias
    
    if parent_identifier is not None:
        if parent_identifier.lower() == 'none':
            update_params["parent_id"] = None
        else:
            parent_todo = get_todo_by_id_or_alias(parent_identifier)
            if parent_todo:
                update_params["parent_id"] = parent_todo.id
            else:
                console.print(f"[yellow]Warning: Parent task '{parent_identifier}' not found. Parent ID not updated.[/yellow]")

    if update_params:
    # Update the parent task
        update_todo(todo_obj.id, **update_params)
        console.print(f"[green]ToDo '{identifier}' updated successfully.[/green]")

        updated_fields = {"priority", "recurrence"}
        if updated_fields.intersection(update_params.keys()):
            children = get_children_of_todo(todo_obj.id)
            if children:
                for child in children:
                    child_updates = {}
                    if "priority" in update_params:
                        child_updates["priority"] = update_params["priority"]
                    if "recurrence" in update_params:
                        child_updates["recurrence"] = update_params["recurrence"]

                    if child_updates:
                        update_todo(child.id, **child_updates)

                console.print(f"[yellow]{len(children)} child task(s) updated to match parent.[/yellow]")
    else:
        console.print("[yellow]No updates provided.[/yellow]")



@todo_app.command("complete")
def complete_todo_command(
    identifier: str = typer.Argument(..., help="The ID or alias of the ToDo to mark as complete."),
):
    """Mark a ToDo as complete by its ID or alias."""
    todo_obj = get_todo_by_id_or_alias(identifier)
    if not todo_obj:
        console.print(f"[red]Error: ToDo '{identifier}' not found.[/red]")
        raise typer.Exit(code=1)
    
    if todo_obj.status == "done":
        console.print(f"[yellow]ToDo '{todo_obj.task}' is already marked as complete.[/yellow]")
        raise typer.Exit(code=0)

    complete_todo(todo_obj.id)
    console.print(f"[green]ToDo '{todo_obj.task}' marked as complete.[/green]")


@todo_app.command("status")
def set_status_command(
    identifier: str = typer.Argument(..., help="The ID or alias of the ToDo to update."),
    status: str = typer.Argument(..., help="New status (pending, in-progress, done).")
):
    """Set the status of a ToDo item by its ID or alias."""
    todo_obj = get_todo_by_id_or_alias(identifier)
    if not todo_obj:
        console.print(f"[red]Error: ToDo '{identifier}' not found.[/red]")
        raise typer.Exit(code=1)
    
    set_status(todo_obj.id, status)
    console.print(f"[green]Status for ToDo '{todo_obj.task}' set to '{status}'.[/green]")


@todo_app.command("delete")
def delete_todo_command(
    identifier: str = typer.Argument(..., help="The ID or alias of the ToDo to delete."),
):
    """Delete a ToDo item by its ID or alias."""
    todo_obj = get_todo_by_id_or_alias(identifier)
    if not todo_obj:
        console.print(f"[red]Error: ToDo '{identifier}' not found.[/red]")
        raise typer.Exit(code=1)

    delete_todo(todo_obj.id)
    console.print(f"[green]ToDo '{todo_obj.task}' (ID: {todo_obj.id}) deleted successfully.[/green]")

@todo_app.command("clean")
def clean_past_due_tasks():
    """
    Delete past-due non-recurring tasks and refresh recurring tasks for today.
    """
    deleted = delete_past_due_todos()
    refreshed = refresh_all_recurring_tasks()

    if deleted:
        console.print(f"[green]Deleted {deleted} past-due non-recurring task(s).[/green]")
    else:
        console.print("[yellow]No non-recurring past-due tasks found.[/yellow]")

    if refreshed:
        console.print(f"[green]Refreshed {refreshed} recurring task(s) (daily/weekly/monthly) for today.[/green]")
    else:
        console.print("[yellow]No outdated recurring tasks found.[/yellow]")



@todo_app.command("search")
def search_todos_command(keyword: str = typer.Argument(..., help="Keyword to search in tasks, priority, status, recurrence, or alias.")):
    """Search for ToDo items by a keyword."""
    results = search_todos(keyword)
    if not results:
        console.print(f"[yellow]No tasks found matching '{keyword}'.[/yellow]")
        return
    
    # Reuse list_todos's rendering logic (or part of it) for search results
    console.print(f"[bold blue]Search Results for '{keyword}':[/bold blue]")
    
    table = Table(
        title=f"[bold cyan]Search Results for '{keyword}'[/bold cyan]",
        show_header=True,
        header_style="bold magenta",
        box=box.ROUNDED,
        show_lines=True
    )
    table.add_column("ID / Alias", justify="center", style="dim")
    table.add_column("Task", justify="left")
    table.add_column("Due Date", justify="center")
    table.add_column("Priority", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Added Date", justify="center")
    table.add_column("Repeat", justify="center")

    children_map = defaultdict(list)
    for todo in results: 
        children_map[todo.parent_id].append(todo)

    def add_task_rows_recursive_search(tasks: List[Todo], level: int = 0):
        for task in tasks:
            indent = "  " * level
            task_text = f"{indent}{task.task}"
            row_style = ""
            status_text = Text(task.status.capitalize(), style="white")
            priority_style = "white"

            if task.status == "done":
                row_style = "strike dim"
                status_text = Text("✔ Done", style="green")
            elif task.status == "in-progress":
                status_text = Text("In Progress", style="blue")
            elif task.status == "pending":
                if task.due_date:
                    try:
                        if datetime.fromisoformat(task.due_date).date() < datetime.now().date():
                            row_style = "red bold"
                            status_text = Text("Overdue", style="red bold")
                    except ValueError:
                        pass

            if task.priority == "high":
                priority_style = "bold red"
            elif task.priority == "medium":
                priority_style = "yellow"
            elif task.priority == "low":
                priority_style = "green"
            
            safe_priority = task.priority.capitalize() if task.priority else "Medium"

            id_alias_display = str(task.id)
            if task.alias:
                id_alias_display += f" ({task.alias})"
            if task.parent_id:
                id_alias_display = f"{indent}↳ {id_alias_display}"

            due_display = short_date(task.due_date) if task.due_date and not task.parent_id else "-"
            priority_display = safe_priority if not task.parent_id else "-"
            repeat_display = task.recurrence or "-" if not task.parent_id else "-"

            table.add_row(
                Text(id_alias_display, style=row_style),
                Text(task_text, style=row_style),
                Text(due_display, style=row_style),
                Text(priority_display, style=priority_style),
                status_text,
                Text(short_date(task.date_added), style=row_style),
                Text(repeat_display, style=row_style)
            )
            
        
            if task.id in children_map and children_map[task.id]:
                add_task_rows_recursive_search(children_map[task.id], level + 1)
    
    top_level_search_results = [t for t in results if t.parent_id is None]
    add_task_rows_recursive_search(top_level_search_results)

    console.print(table)

if __name__ == "__main__":
    todo_app()