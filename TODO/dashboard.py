import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich import box
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List
from rich.style import Style
from rich.text import Text
import calendar as cal

from TODO.database import get_all_todos # Get Todo objects directly
from TODO.model import Todo # Import the Todo dataclass

app = typer.Typer()
GOAL_PER_DAY = 5 # Example daily goal

console = Console()

def load_todos_for_stats() -> List[Todo]:
    """Loads all todos, which are already Todo objects."""
    return get_all_todos()

@app.command("stats")
def show_stats():
    """
    Displays daily and monthly statistics for completed tasks.
    Shows progress towards a daily goal and a bar chart of tasks completed per day.
    """
    todos = load_todos_for_stats()
    if not todos:
        console.print("[red]No tasks found.[/red]")
        raise typer.Exit()

    today_date_str = datetime.today().date().isoformat() # YYYY-MM-DD
    current_month_prefix = today_date_str[:7] # YYYY-MM

    daily_done = defaultdict(int)
    for todo in todos:
        # Check for both status and valid date_completed
        if todo.status == "done" and todo.date_completed:
            try:
                # Ensure date_completed is a valid ISO format string or convertible
                completed_date_obj = datetime.fromisoformat(todo.date_completed).date()
                completed_date_iso = completed_date_obj.isoformat()
                
                if completed_date_iso.startswith(current_month_prefix):
                    daily_done[completed_date_iso] += 1
            except ValueError:
                console.print(f"[bold yellow]Warning:[/bold yellow] Skipping task '{todo.task}' due to malformed completion date: '{todo.date_completed}'")


    today_done = daily_done.get(today_date_str, 0)
    console.print(Panel(f"[bold green]Today:[/bold green] {today_done}/{GOAL_PER_DAY} tasks done", title="🎯 Goal Progress"))
    
    with Progress(console=console) as progress: # Pass console to Progress
        task = progress.add_task("Daily Goal", total=GOAL_PER_DAY, completed=today_done) # Set initial completed value

    console.print("\n[bold cyan]📊 Tasks Completed This Month[/bold cyan]")
    table = Table(box=box.MINIMAL_DOUBLE_HEAD)
    table.add_column("Date", justify="right")
    table.add_column("Done", justify="left")

    # Sort days chronologically
    for day in sorted(daily_done.keys()):
        # Display only the day part for brevity (e.g., "01", "15")
        day_display = datetime.fromisoformat(day).strftime("%d") # Format to get "DD"
        bar = "█" * min(daily_done[day], GOAL_PER_DAY) # Cap bar at GOAL_PER_DAY
        table.add_row(day_display, f"{bar} ([bold]{daily_done[day]}[/bold])")

    console.print(table)

@app.command("calendar")
def show_calendar(
    month: int = typer.Option(datetime.today().month, help="Month to display (1-12)"),
    year: int = typer.Option(datetime.today().year, help="Year to display"),
):
    """
    Display a calendar-style view of tasks for the current month.
    """
    tasks = get_all_todos()
    today = datetime.today()
    start_of_month = datetime(year, month, 1)
    _, end_day = cal.monthrange(year, month)

    month_name = datetime(year, month, 1).strftime("%B")
    table = Table(
        title=f"[bold magenta]🗓️ {month_name} {year} Task Calendar[/bold magenta]",
        show_lines=True,
        border_style="bright_blue"
    )

    week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for idx, day in enumerate(week_days):
        color = "yellow" if idx >= 5 else "white"
        table.add_column(f"[bold {color}]{day}[/bold {color}]", justify="center")

    def format_task(task, date_str):
        is_done = (task.status == "done" and task.date_completed and task.date_completed.startswith(date_str))
        bullet = "✔" if is_done else "•"
        emoji = "🔁 " if task.recurrence == "daily" else ""

        if is_done:
            return f"[green]{bullet} [strike]{task.task}[/strike][/green]"
        elif task.recurrence == "daily":
            return f"[bright_cyan]{bullet} {emoji}{task.task}[/bright_cyan]"
        else:
            return f"[bold red]{bullet} {task.task}[/bold red]"

    day_cells = []
    for day in range(1, end_day + 1):
        current_date = datetime(year, month, day).date()
        date_str = current_date.isoformat()

        specific_tasks = []
        daily_tasks = []

        for t in tasks:
            # Only show tasks if they existed on or before current_date
            try:
                added_date = datetime.fromisoformat(t.date_added).date()
                if added_date > current_date:
                    continue  # Skip future-added tasks
            except:
                continue

            if t.due_date:
                try:
                    due_date = datetime.fromisoformat(t.due_date).date()
                    if due_date == current_date:
                        specific_tasks.append(t)
                except:
                    continue
            elif t.recurrence == "daily":
                daily_tasks.append(t)

        all_tasks_for_day = specific_tasks + daily_tasks

        # Optional: Remove duplicates (if same task appears twice)
        seen = set()
        display_lines = []
        for t in all_tasks_for_day:
            if t.task not in seen:
                seen.add(t.task)
                display_lines.append(format_task(t, date_str))

        day_label = f"[bold cyan]{day}[/bold cyan]"
        if current_date == today.date():
            day_label = f"[reverse bold yellow]{day}[/reverse bold yellow]"

        day_cells.append(f"{day_label}\n" + "\n".join(display_lines))

    start_weekday = start_of_month.weekday()
    day_cells = [""] * start_weekday + day_cells

    for i in range(0, len(day_cells), 7):
        week = day_cells[i:i+7]
        week += [""] * (7 - len(week))
        table.add_row(*week)

    console.print(table)


@app.command("weekly")
def weekly():
    """
    Shows a weekly calendar-style ToDo dashboard with tasks, indicating completion.
    Displays recurring tasks and those due/added this week.
    """
    todos = load_todos_for_stats()
    week_days_names = ["Mon", "Tues", "Wed", "Thur", "Fri", "Sat", "Sun"]
    week_table = Table(show_header=True, header_style="bold magenta")
    for day_name in week_days_names:
        week_table.add_column(day_name)

    today = datetime.today().date()
    # Find the Monday of the current week (weekday() returns 0 for Monday)
    start_of_week = today - timedelta(days=today.weekday())
    # Generate dates for the current week in ISO format
    week_dates_iso = [(start_of_week + timedelta(days=i)).isoformat() for i in range(7)]

    # Use a dictionary to store tasks for each day of the week
    # Key: weekday index (0-6), Value: list of formatted task strings
    columns_content = defaultdict(list)

    def format_task(task_title: str, is_completed: bool, is_overdue: bool) -> str:
        bullet = "•"
        if is_completed:
            return f"[green]{bullet} [strike]{task_title}[/strike][/green]"
        elif is_overdue:
            return f"[red]{bullet} {task_title}[/red]"
        else:
            return f"[white]{bullet} {task_title}[/white]"

    for todo in todos:
        task_title = todo.task
        recurrence = todo.recurrence
        
        # Check if task is completed and on what date
        completed_on_date = None
        if todo.status == "done" and todo.date_completed and todo.date_completed != 'None':
            try:
                completed_on_date = datetime.fromisoformat(todo.date_completed).date()
            except ValueError:
                pass # Malformed date

        # Determine if the task is overdue relative to today
        is_task_overdue = False
        if todo.status == "pending" and todo.due_date and todo.due_date != 'None':
            try:
                due_date_dt = datetime.fromisoformat(todo.due_date).date()
                if due_date_dt < today:
                    is_task_overdue = True
            except ValueError:
                pass


        if recurrence == "daily":
            # Daily tasks appear on every day of the week
            for idx, day_iso in enumerate(week_dates_iso):
                is_done_on_this_day = (completed_on_date is not None and completed_on_date.isoformat() == day_iso)
                columns_content[idx].append(format_task(task_title, is_done_on_this_day, is_task_overdue and not is_done_on_this_day)) # Overdue only if not done
        
        elif recurrence == "weekly":
            # Weekly tasks appear on the day of the week they were added/intended
            if todo.date_added and todo.date_added != 'None':
                try:
                    added_day_of_week_idx = datetime.fromisoformat(todo.date_added).weekday() # 0 for Monday
                    if 0 <= added_day_of_week_idx < 7:
                        day_iso = week_dates_iso[added_day_of_week_idx]
                        is_done_on_this_day = (completed_on_date is not None and completed_on_date.isoformat() == day_iso)
                        columns_content[added_day_of_week_idx].append(format_task(task_title, is_done_on_this_day, is_task_overdue and not is_done_on_this_day))
                except ValueError:
                    pass

        elif recurrence == "monthly":
            # Monthly tasks appear on the same day number of the month, if it falls in this week
            if todo.date_added and todo.date_added != 'None': # Using date_added for monthly anchor
                try:
                    added_day_number = datetime.fromisoformat(todo.date_added).day
                    for idx, day_iso in enumerate(week_dates_iso):
                        current_day_number = datetime.fromisoformat(day_iso).day
                        if current_day_number == added_day_number:
                            is_done_on_this_day = (completed_on_date is not None and completed_on_date.isoformat() == day_iso)
                            columns_content[idx].append(format_task(task_title, is_done_on_this_day, is_task_overdue and not is_done_on_this_day))
                            break # Found the day, no need to check other days in the week
                except ValueError:
                    pass

        else: # Non-recurring tasks
            if todo.due_date and todo.due_date != 'None': # Prioritize due date for non-recurring tasks
                try:
                    due_date_dt = datetime.fromisoformat(todo.due_date).date()
                    if due_date_dt.isoformat() in week_dates_iso:
                        idx = week_dates_iso.index(due_date_dt.isoformat())
                        is_done_on_this_day = (completed_on_date is not None and completed_on_date.isoformat() == week_dates_iso[idx])
                        columns_content[idx].append(format_task(task_title, is_done_on_this_day, is_task_overdue and not is_done_on_this_day))
                except ValueError:
                    pass
            elif todo.date_added and todo.date_added != 'None': # Fallback to added date if no due date
                try:
                    added_date_dt = datetime.fromisoformat(todo.date_added).date()
                    if added_date_dt.isoformat() in week_dates_iso:
                        idx = week_dates_iso.index(added_date_dt.isoformat())
                        is_done_on_this_day = (completed_on_date is not None and completed_on_date.isoformat() == week_dates_iso[idx])
                        columns_content[idx].append(format_task(task_title, is_done_on_this_day, is_task_overdue and not is_done_on_this_day))
                except ValueError:
                    pass


    # Determine the maximum height needed for rows to prevent alignment issues
    max_rows = max((len(v) for v in columns_content.values()), default=0)

    # Fill empty slots in columns if they don't reach max_rows
    for col_idx in range(7):
        while len(columns_content[col_idx]) < max_rows:
            columns_content[col_idx].append("") # Add empty string for alignment

    # Add rows to the table
    for i in range(max_rows):
        row_data = [columns_content[j][i] for j in range(7)]
        week_table.add_row(*row_data)

    week_range_start = datetime.fromisoformat(week_dates_iso[0]).strftime("%Y-%m-%d")
    week_range_end = datetime.fromisoformat(week_dates_iso[-1]).strftime("%Y-%m-%d")
    console.print(Panel(week_table, title=f"📅 Weekly View: {week_range_start} to {week_range_end}"))


if __name__ == "__main__":
    app()
