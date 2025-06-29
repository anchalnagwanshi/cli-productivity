# FOCUS_MODE/dashboard.py - MODIFIED
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress
from rich import box
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Optional, Dict, Tuple
from rich.style import Style
from rich.text import Text
import calendar as cal
from prodcli.TODO.database import get_all_todos
from prodcli.TODO.model import Todo

dashboard_app = typer.Typer()
GOAL_PER_DAY = 5

console = Console()

def load_todos_for_stats() -> Tuple[List[Todo], Dict[Optional[int], List[Todo]]]:
    """Loads all todos and their children map for stats purposes."""
    all_todos = get_all_todos()
    children_map = defaultdict(list)
    for todo in all_todos:
        children_map[todo.parent_id].append(todo)
    return all_todos, children_map

def get_all_and_children() -> Tuple[List[Todo], Dict[Optional[int], List[Todo]]]:
    """Helper to fetch all todos and build a parent-child map."""
    all_todos = get_all_todos()
    children_map = defaultdict(list)
    for todo in all_todos:
        children_map[todo.parent_id].append(todo)
    return all_todos, children_map

def is_done(todo: Todo, day_iso: str) -> bool:
    """Checks if a todo was completed on the given day."""
    return todo.status == "done" and todo.date_completed == day_iso

def is_late_done(todo: Todo, day_iso: str) -> bool:
    """Checks if a todo was completed on the given day but was overdue."""
    if todo.status == "done" and todo.date_completed == day_iso and todo.due_date:
        return datetime.fromisoformat(todo.due_date).date() < datetime.fromisoformat(day_iso).date()
    return False

def short_date(date_str: Optional[str]) -> str:
    """Convert ISO datetime to DD-MM-YYYY format, handles None/string 'None' gracefully."""
    if date_str is None or date_str == 'None':
        return "-"
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return date_str 

def is_display_daily(todo: Todo, day_iso: str) -> bool:
    """
    Determines if a todo should be displayed on a specific day in the calendar.
    Considers due dates, completion dates, and recurrence patterns.
    """
    day_date = datetime.fromisoformat(day_iso).date()

    if not todo.recurrence:
        if todo.status == "done" and todo.date_completed == day_iso:
            return True

        day_date = datetime.fromisoformat(day_iso).date()
        added_date = datetime.fromisoformat(todo.date_added).date()
        today_date = datetime.today().date()

        if added_date < today_date and day_date < today_date and added_date <= day_date and todo.status != "done":
            return True

        if added_date == day_date and todo.status != "done":
            return True

        return False


    task_start_date = datetime.fromisoformat(todo.date_added).date() 
    
    if day_date < task_start_date:
        return False

    if todo.recurrence == "daily":
        return True
    elif todo.recurrence == "weekly":
        # Show weekly tasks on all days of the week they are active.
        # An active week is one that contains the task's date_added (and any subsequent week).
        # Get the Monday of the week for both dates
        start_of_task_week = task_start_date - timedelta(days=task_start_date.weekday())
        start_of_current_day_week = day_date - timedelta(days=day_date.weekday())
        return start_of_task_week == start_of_current_day_week or start_of_current_day_week > start_of_task_week
    elif todo.recurrence == "monthly":
        return day_date.day == task_start_date.day

    return False

def format_task_for_calendar(task_obj: Todo, day_iso: str, level: int = 0) -> Text:
    """Formats a single task for display in the calendar view."""
    indent = "  " * level
    task_name = task_obj.task
    
    current_day_date = datetime.fromisoformat(day_iso).date()

    status_icon = "•"
    task_name_style = Style(color="cyan") 

    if task_obj.status == "done" and task_obj.date_completed == day_iso:
        status_icon = "✔"
        task_name_style = Style(color="green", strike=True)
   
    elif (task_obj.status == "pending" or task_obj.status == "in-progress"):
        added_date = datetime.fromisoformat(task_obj.date_added).date()
        today_date = datetime.today().date()
        if added_date < today_date and current_day_date < today_date:
            status_icon = "⚠"
            task_name_style = Style(color="yellow", bold=True)

    elif task_obj.status == "in-progress":
        status_icon = "▶"
        task_name_style = Style(color="blue")
    else:
        status_icon = "•"
        task_name_style = Style(color="cyan")

    prefix = status_icon
    if task_obj.recurrence:
        prefix = f"{status_icon} 🔁"

    task_display_text = Text(f"{prefix} {indent}{task_name}", style=task_name_style)
    return task_display_text 


def format_task_for_weekly(task_obj: Todo, day_iso: str, level: int = 0) -> Text:
    """Formats a single task for display in the weekly view."""
    indent_str = "  " * level
    task_name = task_obj.task

    current_day_date = datetime.fromisoformat(day_iso).date()

    status_icon = "•" 
    task_name_style = Style(color="cyan") 

    if task_obj.status == "done" and task_obj.date_completed == day_iso:
        status_icon = "✔"
        task_name_style = Style(color="green", strike=True)
   
    elif (task_obj.status == "pending" or task_obj.status == "in-progress"):
        added_date = datetime.fromisoformat(task_obj.date_added).date()
        today_date = datetime.today().date()
       
        if added_date < today_date and current_day_date < today_date:
            status_icon = "⚠"
            task_name_style = Style(color="yellow", bold=True)

    elif task_obj.status == "in-progress":
        status_icon = "▶"
        task_name_style = Style(color="blue")
    else:
        status_icon = "•"
        task_name_style = Style(color="cyan")
    
    prefix = status_icon
    if task_obj.recurrence:
        prefix = f"{status_icon} 🔁"

    task_display_text = Text(f"{prefix} {indent_str}{task_name}", style=task_name_style)
    return task_display_text 


@dashboard_app.command("stats")
def show_stats():
    """
    Displays daily and monthly statistics for completed tasks.
    Shows progress towards a daily goal and a bar chart of tasks completed per day.
    """
    todos, children_map = load_todos_for_stats()
    if not todos:
        console.print("[red]No tasks found.[/red]")
        raise typer.Exit()

    today_date_str = datetime.today().date().isoformat()
    current_month_prefix = today_date_str[:7]

    daily_done = defaultdict(int)
    for todo in todos:
        
        if todo.status == "done" and todo.date_completed:
            daily_done[todo.date_completed] += 1
        
    
        if todo.id in children_map:
            for child in children_map[todo.id]:
                
                if child.status == "done" and child.date_completed == todo.date_completed:
                    daily_done[child.date_completed] += 1

    # Monthly Summary
    monthly_done = defaultdict(int)
    for date_str, count in daily_done.items():
        month_prefix = date_str[:7]
        monthly_done[month_prefix] += count

    # Display Daily Stats
    console.print(Panel(f"[bold blue]Today's Progress ({today_date_str})[/bold blue]", expand=False))
    today_completed = daily_done[today_date_str]
    progress_ratio = min(today_completed / GOAL_PER_DAY, 1.0)

    progress_bar = Progress(
        "[progress.description]{task.description}",
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        "[green]{task.completed}/{task.total}",
        "•",
        "[progress.remaining]{task.fields[remaining_str]}",
        console=console,
        transient=True
    )

    with progress_bar:
        task_progress = progress_bar.add_task(
            f"[bold cyan]Tasks completed today:[/bold cyan]",
            total=GOAL_PER_DAY,
            completed=today_completed,
            remaining_str=f"Goal: {GOAL_PER_DAY}"
        )
        progress_bar.update(task_progress, advance=0) 

    console.print(f"Total tasks completed today: [bold green]{today_completed}[/bold green]\n")

    console.print(Panel(f"[bold blue]Monthly Progress - {datetime.today().strftime('%B %Y')}[/bold blue]", expand=False))
    
    first_day_of_month = datetime.today().replace(day=1).date()
    last_day_of_month = (first_day_of_month.replace(month=first_day_of_month.month % 12 + 1, day=1) - timedelta(days=1)).date()
    
    dates_in_month = []
    for d in range(1, last_day_of_month.day + 1):
        try:
            date_obj = datetime(first_day_of_month.year, first_day_of_month.month, d).date()
            dates_in_month.append(date_obj.isoformat())
        except ValueError:
            pass

    dates_in_month.sort()

    max_daily_done = max(daily_done.values()) if daily_done else 0
    if max_daily_done == 0:
        console.print("[yellow]No tasks completed this month yet.[/yellow]")
    else:
        scale = max(1, max_daily_done // 20) 

        for date_iso in dates_in_month:
            count = daily_done.get(date_iso, 0)
            bars = "#" * (count // scale)
            
            date_display = f"[bold yellow]{date_iso}[/bold yellow]" if date_iso == today_date_str else date_iso
            console.print(f"{date_display}: {bars} ({count})")
    console.print("\n")


@dashboard_app.command("calendar")
def show_calendar(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year for the calendar (e.g., 2023)."),
    month: Optional[int] = typer.Option(None, "--month", "-m", help="Month for the calendar (1-12)."),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="Week number for the calendar (1-53).")
):
    """
    Displays a monthly or weekly calendar view of ToDo items.
    Highlights current day and displays tasks relevant to each day.
    """
    todos, children_map = get_all_and_children() # Using the existing helper
    today = datetime.today().date()

    display_month_year: datetime.date
    if year and month:
        display_month_year = datetime(year, month, 1).date()
    elif year and week:
        try:
            
            display_month_year = datetime.fromisocalendar(year, week, 1).date()
        except ValueError:
            console.print(f"[red]Invalid week number {week} for year {year}.[/red]")
            raise typer.Exit(1)
    else:
        display_month_year = today

   
    calendar_table = Table(
        title=f"\n[bold blue]{display_month_year.strftime('%B %Y')}[/bold blue]\n",
        show_header=True,
        header_style="bold green",
        box=box.ROUNDED,
        padding=(0, 1) 
    )

    days_of_week_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day_name in days_of_week_names:
        calendar_table.add_column(day_name, justify="left")

    cal_obj = cal.Calendar()
   
    month_days_data = cal_obj.monthdayscalendar(display_month_year.year, display_month_year.month)

    for week_num, week_of_days_list in enumerate(month_days_data):
        # Row for just the dates (e.g., 1, 2, 3...)
        date_row_content = []
        for day_num in week_of_days_list:
            if day_num == 0: 
                date_row_content.append(Text(""))
            else:
                current_day_date = datetime(display_month_year.year, display_month_year.month, day_num).date()
                day_style = "white"
                if current_day_date == today:
                    day_style = "bold yellow" 
                
                date_row_content.append(Text(f"{day_num}", style=day_style))
        calendar_table.add_row(*date_row_content) 

        
        columns_content: Dict[int, List[Text]] = defaultdict(list)
        
        for idx, day_num in enumerate(week_of_days_list):
            if day_num == 0:
                continue # Skip days from other months for task display

            day_iso = datetime(display_month_year.year, display_month_year.month, day_num).date().isoformat()
            
          
            current_day_tasks = [
                todo for todo in todos
                if is_display_daily(todo, day_iso) and todo.parent_id is None 
            ]
            current_day_tasks.sort(key=lambda t: (t.priority, t.due_date or "9999-12-31", t.task)) # Sort tasks

            all_formatted_lines_for_day: List[Text] = []
            seen_todo_ids_on_day = set()

            for task_obj in current_day_tasks:
                lines_from_task = [format_task_for_calendar(task_obj, day_iso, level=0)]
                seen_todo_ids_on_day.add(task_obj.id) 
                
                def add_children_recursive_calendar(t_obj, current_level):
                    for child in children_map.get(t_obj.id, []):
                        if child.id not in seen_todo_ids_on_day:
                            lines_from_task.append(format_task_for_calendar(child, day_iso, level=current_level + 1))
                            seen_todo_ids_on_day.add(child.id) # Mark child as seen
                            add_children_recursive_calendar(child, current_level + 1)
                
                add_children_recursive_calendar(task_obj, 0)
                all_formatted_lines_for_day.extend(lines_from_task)
            
            columns_content[idx].extend(all_formatted_lines_for_day)

        max_task_rows = max((len(v) for v in columns_content.values()), default=0)

        for col_idx in range(7):
            while len(columns_content[col_idx]) < max_task_rows:
                columns_content[col_idx].append(Text(""))

        if max_task_rows > 0:
            for i in range(max_task_rows):
                row_data = [columns_content[j][i] for j in range(7)]
                calendar_table.add_row(*row_data) 
      
        if week_num < len(month_days_data) - 1:
            calendar_table.add_section()

    console.print(calendar_table)


@dashboard_app.command("weekly")
def show_weekly(
    year: Optional[int] = typer.Option(None, "--year", "-y", help="Year for the weekly view (e.g., 2023)."),
    week: Optional[int] = typer.Option(None, "--week", "-w", help="Week number for the weekly view (1-53).")
):
    """
    Displays a weekly view of ToDo items, showing tasks for each day of the specified week.
    """
    todos, children_map = get_all_and_children()
    today = datetime.today().date()

    if year is None:
        year = today.year
    if week is None:
        week = today.isocalendar()[1] 

    try:
        # Get the date of the Monday of the specified week
        start_of_week = datetime.fromisocalendar(year, week, 1).date()
    except ValueError:
        console.print(f"[red]Invalid week number {week} for year {year}.[/red]")
        raise typer.Exit(1)

    end_of_week = start_of_week + timedelta(days=6)

    weekly_table = Table(
        title=f"\n[bold blue]Weekly ToDo Summary: Week {week}, {year}[/bold blue]\n"
              f"[dim]({start_of_week.strftime('%d %b')} - {end_of_week.strftime('%d %b')})[/dim]",
        show_header=True,
        header_style="bold green",
        box=box.ROUNDED,
        padding=(0, 1)
    )

    days_of_week_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for day_name in days_of_week_names:
        weekly_table.add_column(day_name, justify="left")

    columns_content: Dict[int, List[Text]] = defaultdict(list)
    
    for idx in range(7):
        current_day_date = start_of_week + timedelta(days=idx)
        day_iso = current_day_date.isoformat()

      
        day_header_style = "white"
        if current_day_date == today:
            day_header_style = "bold yellow" 
        columns_content[idx].append(Text(f"{current_day_date.day}", style=day_header_style))


        current_day_tasks = [
            todo for todo in todos
            if is_display_daily(todo, day_iso) and todo.parent_id is None 
        ]
        current_day_tasks.sort(key=lambda t: (t.priority, t.due_date or "9999-12-31", t.task)) # Sort tasks

        all_formatted_lines_for_day: List[Text] = []
        seen_todo_ids_on_day = set() 

        for task_obj in current_day_tasks:
            lines_from_task = [format_task_for_weekly(task_obj, day_iso, level=0)]
            seen_todo_ids_on_day.add(task_obj.id) 
            
            def add_children_recursive_weekly(t_obj, current_level):
                for child in children_map.get(t_obj.id, []):
                    if child.id not in seen_todo_ids_on_day:
                        lines_from_task.append(format_task_for_weekly(child, day_iso, level=current_level + 1))
                        seen_todo_ids_on_day.add(child.id)
                        add_children_recursive_weekly(child, current_level + 1)
            
            add_children_recursive_weekly(task_obj, 0)
            all_formatted_lines_for_day.extend(lines_from_task)
        
        columns_content[idx].extend(all_formatted_lines_for_day)


    max_rows = max((len(v) for v in columns_content.values()), default=0)

    for col_idx in range(7):
        while len(columns_content[col_idx]) < max_rows:
            columns_content[col_idx].append(Text("")) 

    for i in range(max_rows):
        row_data = [columns_content[j][i] for j in range(7)]
        weekly_table.add_row(*row_data)

    console.print(weekly_table)

if __name__ == "__main__":
    dashboard_app()