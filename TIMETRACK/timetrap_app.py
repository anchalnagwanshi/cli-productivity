# timetrack/timetrap_app.py
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text
from datetime import datetime, timedelta
from typing import Optional, List
import os
import dateparser # For natural language parsing

# Assuming your database.py and model.py are in the same directory or correctly imported
from TIMETRACK.model import Sheet, Entry
from TIMETRACK.database import (
    create_tables, get_db_connection, insert_sheet, get_sheet_by_name, get_all_sheets,
    insert_entry, update_entry, get_running_entries, get_entries_for_sheet,
    get_entry_by_id, delete_sheet, delete_entry, get_sheet_by_id
)

console = Console()
timetrap_app = typer.Typer()

# --- Global State / Configuration ---
CURRENT_SHEET_FILE = os.path.expanduser("~/.timetrap_current_sheet") # Store current sheet name

def get_current_sheet_name() -> Optional[str]:
    if os.path.exists(CURRENT_SHEET_FILE):
        with open(CURRENT_SHEET_FILE, "r") as f:
            return f.read().strip()
    return None

def set_current_sheet_name(sheet_name: str):
    with open(CURRENT_SHEET_FILE, "w") as f:
        f.write(sheet_name)

def get_current_sheet() -> Optional[Sheet]:
    sheet_name = get_current_sheet_name()
    if sheet_name:
        return get_sheet_by_name(sheet_name)
    return None

def parse_time_arg(time_str: Optional[str]) -> Optional[datetime]:
    if time_str:
        try:
            # Try ISO format first for explicit parsing
            return datetime.fromisoformat(time_str)
        except ValueError:
            # Then try natural language parsing
            parsed_date = dateparser.parse(time_str)
            if parsed_date:
                return parsed_date
            else:
                console.print(f"[bold red]Error:[/bold red] Could not parse time: '{time_str}'")
                raise typer.Exit(code=1)
    return None

def get_duration_str(start: datetime, end: Optional[datetime]) -> str:
    if end is None:
        duration = datetime.now() - start
    else:
        duration = end - start

    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02}:{minutes:02}:{seconds:02}"


# --- Commands ---

@timetrap_app.callback()
def main():
    """
    Timetrap: A simple command-line time tracker.
    """
    create_tables() # Ensure tables exist when any command is run

@timetrap_app.command()
def sheet(sheet_name: Optional[str] = typer.Argument(None)):
    """
    Switch to a timesheet, creating it if necessary.
    If no sheet is specified, list all existing sheets.
    """
    if sheet_name:
        sheet_obj = get_sheet_by_name(sheet_name)
        if not sheet_obj:
            sheet_obj = insert_sheet(sheet_name)
            if sheet_obj:
                console.print(f"Created new sheet: '[bold green]{sheet_name}[/bold green]'")
            else:
                console.print(f"[bold red]Error:[/bold red] Could not create sheet '{sheet_name}'.")
                raise typer.Exit(code=1)

        set_current_sheet_name(sheet_name)
        console.print(f"Switching to sheet '[bold cyan]{sheet_name}[/bold cyan]'")
    else:
        # List all sheets
        sheets = get_all_sheets()
        if not sheets:
            console.print("No timesheets created yet. Use 't sheet <name>' to create one.")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID")
        table.add_column("Sheet Name")
        table.add_column("Current")

        current_sheet_name = get_current_sheet_name()
        for s in sheets:
            is_current = "[bold green]YES[/bold green]" if s.name == current_sheet_name else ""
            table.add_row(str(s.id), s.name, is_current)
        console.print(table)


@timetrap_app.command("in")
def check_in(note: Optional[str] = typer.Argument(None),
             at: Optional[str] = typer.Option(None, "--at", "-a", help="Specify check-in time (e.g., '5 minutes ago', '2023-01-01 10:00').")):
    """
    Start the timer for the current timesheet.
    """
    current_sheet = get_current_sheet()
    if not current_sheet:
        console.print("[bold red]Error:[/bold red] No current timesheet selected. Use 't sheet <name>' first.")
        raise typer.Exit(code=1)

    # Check for existing running entries in the current sheet and auto-checkout if configured
    running_entries_in_current_sheet = [
        entry for entry in get_running_entries() if entry.sheet_id == current_sheet.id
    ]
    if running_entries_in_current_sheet:
        # Implement auto_checkout logic here if desired. For now, just warn.
        console.print("[bold yellow]Warning:[/bold yellow] You have a running entry in this sheet. "
                      "Checking in will create a new one.")

    start_time = parse_time_arg(at) if at else datetime.now()

    entry = Entry(sheet_id=current_sheet.id, start_time=start_time, note=note)
    insert_entry(entry)
    console.print(f"Checked into sheet '[bold cyan]{current_sheet.name}[/bold cyan]'. Note: '{note or ''}'")


@timetrap_app.command("out")
def check_out(at: Optional[str] = typer.Option(None, "--at", "-a", help="Specify check-out time."),
              sheet_name: Optional[str] = typer.Argument(None, help="Check out of a specific sheet")):
    """
    Stop the timer for the current timesheet, or a specified sheet.
    """
    entries_to_checkout = []

    if sheet_name:
        sheet_obj = get_sheet_by_name(sheet_name)
        if not sheet_obj:
            console.print(f"[bold red]Error:[/bold red] Sheet '{sheet_name}' not found.")
            raise typer.Exit(code=1)
        running = get_running_entries()
        entries_to_checkout = [e for e in running if e.sheet_id == sheet_obj.id]
        if not entries_to_checkout:
            console.print(f"No running entry found in sheet '{sheet_name}'.")
            return
    else:
        # Default to current sheet
        current_sheet = get_current_sheet()
        if not current_sheet:
            console.print("[bold red]Error:[/bold red] No current timesheet selected. Use 't sheet <name>' first.")
            raise typer.Exit(code=1)
        running_in_current = [
            entry for entry in get_running_entries() if entry.sheet_id == current_sheet.id
        ]
        if not running_in_current:
            console.print(f"No running entry found in current sheet '[bold cyan]{current_sheet.name}[/bold cyan]'.")
            return
        # If multiple running entries in current sheet (shouldn't happen with typical usage but for robustness)
        # We check out the latest one.
        entries_to_checkout.append(max(running_in_current, key=lambda e: e.start_time))

    end_time = parse_time_arg(at) if at else datetime.now()

    for entry in entries_to_checkout:
        if entry.start_time > end_time:
            console.print(f"[bold yellow]Warning:[/bold yellow] End time '{end_time.strftime('%H:%M')}' is before start time '{entry.start_time.strftime('%H:%M')}' for entry ID {entry.id}. Not checking out.")
            continue

        update_entry(entry.id, end_time=end_time)
        sheet_name_for_msg = get_sheet_by_id(entry.sheet_id).name
        console.print(f"Checked out of entry '{entry.note or 'No note'}' in sheet '[bold cyan]{sheet_name_for_msg}[/bold cyan]'.")


@timetrap_app.command("now")
def show_now():
    """
    Print a description of all running entries.
    """
    running_entries = get_running_entries()
    if not running_entries:
        console.print("No entries currently running.")
        return

    table = Table(show_header=True, header_style="bold green")
    table.add_column("Sheet")
    table.add_column("Start Time")
    table.add_column("Duration")
    table.add_column("Note")

    for entry in running_entries:
        sheet = get_sheet_by_id(entry.sheet_id)
        sheet_name = sheet.name if sheet else "Unknown"
        duration_str = get_duration_str(entry.start_time, None)
        table.add_row(
            f"[bold cyan]{sheet_name}[/bold cyan]",
            entry.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_str,
            entry.note or "[italic dim]No note[/italic dim]"
        )
    console.print(table)


@timetrap_app.command("display")
def display(
    sheet_name: Optional[str] = typer.Argument(None, help="The timesheet to display. Use 'all' or 'full' for all sheets."),
    ids: bool = typer.Option(False, "--ids", "-v", help="Include entry IDs in the output."),
    start: Optional[str] = typer.Option(None, "--start", help="Filter entries starting from this time."),
    end: Optional[str] = typer.Option(None, "--end", help="Filter entries ending by this time."),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text, csv, json, ids.")
):
    """
    Display a given timesheet. If no timesheet is specified, show the current timesheet.
    """
    target_start_time = parse_time_arg(start)
    target_end_time = parse_time_arg(end)

    sheets_to_display: List[Sheet] = []
    if sheet_name == "all" or sheet_name == "full": # 'full' includes archived in original, we'll keep it simple for now
        sheets_to_display = get_all_sheets()
    elif sheet_name:
        sheet_obj = get_sheet_by_name(sheet_name)
        if sheet_obj:
            sheets_to_display.append(sheet_obj)
        else:
            console.print(f"[bold red]Error:[/bold red] Sheet '{sheet_name}' not found.")
            raise typer.Exit(code=1)
    else:
        current_sheet = get_current_sheet()
        if current_sheet:
            sheets_to_display.append(current_sheet)
        else:
            console.print("[bold yellow]Warning:[/bold yellow] No current sheet selected. Use 't sheet <name>' or 't display all'.")
            return

    if not sheets_to_display:
        console.print("No sheets to display.")
        return

    # For text format
    if format == "text":
        for sheet_obj in sheets_to_display:
            console.print(f"\nTimesheet: [bold cyan]{sheet_obj.name}[/bold cyan]")
            entries = get_entries_for_sheet(sheet_obj.id, target_start_time, target_end_time)

            if not entries:
                console.print("    No entries for this sheet in the specified range.")
                continue

            table = Table(show_header=True, header_style="bold blue")
            if ids:
                table.add_column("Id", width=4)
            table.add_column("Day")
            table.add_column("Start")
            table.add_column("End")
            table.add_column("Duration")
            table.add_column("Notes")

            total_duration_sheet = timedelta(0)

            # Group entries by day for display as in original timetrap
            entries_by_day = {}
            for entry in entries:
                day_key = entry.start_time.strftime("%a %b %d, %Y")
                if day_key not in entries_by_day:
                    entries_by_day[day_key] = []
                entries_by_day[day_key].append(entry)

            for day_key in sorted(entries_by_day.keys()):
                day_total_duration = timedelta(0)
                first_entry_of_day = True
                for entry in entries_by_day[day_key]:
                    start_str = entry.start_time.strftime("%H:%M:%S")
                    end_str = entry.end_time.strftime("%H:%M:%S") if entry.end_time else "-"
                    duration_td = entry.end_time - entry.start_time if entry.end_time else datetime.now() - entry.start_time
                    duration_str = get_duration_str(entry.start_time, entry.end_time)
                    day_total_duration += duration_td
                    total_duration_sheet += duration_td

                    row_data = []
                    if ids:
                        row_data.append(str(entry.id))
                    row_data.extend([
                        day_key if first_entry_of_day else "", # Only show day once
                        start_str,
                        end_str,
                        duration_str,
                        entry.note or ""
                    ])
                    table.add_row(*row_data)
                    first_entry_of_day = False
                
                # Add daily total
                table.add_row(
                    Text("Total", style="bold"),
                    "", "", "", get_duration_str(datetime.min, datetime.min + day_total_duration), # dummy dates
                    style="bold"
                )
                table.add_section() # Adds a separator after each day

            table.add_row(
                Text("Total", style="bold blue"),
                "", "", "", get_duration_str(datetime.min, datetime.min + total_duration_sheet),
                "", style="bold blue"
            )
            console.print(table)
    elif format == "csv":
        console.print("start,end,note,sheet")
        for sheet_obj in sheets_to_display:
            entries = get_entries_for_sheet(sheet_obj.id, target_start_time, target_end_time)
            for entry in entries:
                start_str = entry.start_time.isoformat()
                end_str = entry.end_time.isoformat() if entry.end_time else ""
                note_str = entry.note.replace('"', '""') if entry.note else ""
                console.print(f'"{start_str}","{end_str}","{note_str}","{sheet_obj.name}"')
    elif format == "json":
        # Placeholder for JSON output
        import json
        output_data = []
        for sheet_obj in sheets_to_display:
            entries = get_entries_for_sheet(sheet_obj.id, target_start_time, target_end_time)
            sheet_entries_data = []
            for entry in entries:
                sheet_entries_data.append({
                    "id": entry.id,
                    "sheet_id": entry.sheet_id,
                    "sheet_name": sheet_obj.name,
                    "start_time": entry.start_time.isoformat(),
                    "end_time": entry.end_time.isoformat() if entry.end_time else None,
                    "note": entry.note
                })
            output_data.extend(sheet_entries_data)
        console.print(json.dumps(output_data, indent=2))
    elif format == "ids":
        for sheet_obj in sheets_to_display:
            entries = get_entries_for_sheet(sheet_obj.id, target_start_time, target_end_time)
            for entry in entries:
                console.print(str(entry.id))
    else:
        console.print(f"[bold red]Error:[/bold red] Unsupported format: '{format}'")
        raise typer.Exit(code=1)


@timetrap_app.command("edit")
def edit_entry(
    id: Optional[int] = typer.Option(None, "--id", "-i", help="ID of the entry to edit."),
    start: Optional[str] = typer.Option(None, "--start", help="New start time for the entry."),
    end: Optional[str] = typer.Option(None, "--end", help="New end time for the entry."),
    note: Optional[str] = typer.Argument(None, help="New note for the entry."),
    append: bool = typer.Option(False, "--append", help="Append to the existing note.")
):
    """
    Edit an entry's note, start, or end times. Defaults to the running entry or last checked out entry.
    """
    target_entry: Optional[Entry] = None

    if id:
        target_entry = get_entry_by_id(id)
        if not target_entry:
            console.print(f"[bold red]Error:[/bold red] Entry with ID {id} not found.")
            raise typer.Exit(code=1)
    else:
        # Try to find running entry first
        running_entries = get_running_entries()
        if running_entries:
            # Assume the most recent running entry if multiple exist
            target_entry = max(running_entries, key=lambda e: e.start_time)
        else:
            # If no running, try to find the last checked out entry in the current sheet
            current_sheet = get_current_sheet()
            if current_sheet:
                entries_in_sheet = get_entries_for_sheet(current_sheet.id) # Get all, then find last
                if entries_in_sheet:
                    target_entry = max(entries_in_sheet, key=lambda e: e.end_time or e.start_time)
            if not target_entry:
                console.print("[bold red]Error:[/bold red] No running entry or last entry found to edit. Specify an ID or check in/out first.")
                raise typer.Exit(code=1)

    new_start_time = parse_time_arg(start) if start else None
    new_end_time = parse_time_arg(end) if end else None

    new_note = note
    if append and target_entry.note and note:
        new_note = f"{target_entry.note} {note}"
    elif append and not target_entry.note and note:
        new_note = note


    updated = update_entry(target_entry.id,
                           start_time=new_start_time,
                           end_time=new_end_time,
                           note=new_note)
    if updated:
        console.print(f"Editing entry with ID {target_entry.id}")
    else:
        console.print(f"[bold yellow]Warning:[/bold yellow] No changes applied to entry ID {target_entry.id}.")


@timetrap_app.command("kill")
def kill_command(
    id: Optional[int] = typer.Option(None, "--id", "-i", help="ID of the entry to delete."),
    sheet_name: Optional[str] = typer.Argument(None, help="Name of the sheet to delete."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Assume 'yes' to confirmation prompts.")
):
    """
    Delete a timesheet or an entry.
    """
    if id and sheet_name:
        console.print("[bold red]Error:[/bold red] Cannot specify both an entry ID and a sheet name.")
        raise typer.Exit(code=1)

    if id:
        entry_to_delete = get_entry_by_id(id)
        if not entry_to_delete:
            console.print(f"[bold red]Error:[/bold red] Entry with ID {id} not found.")
            raise typer.Exit(code=1)
        if not yes:
            confirm = typer.confirm(f"Are you sure you want to delete entry ID {id} ('{entry_to_delete.note}')?")
            if not confirm:
                console.print("Deletion cancelled.")
                raise typer.Exit()
        if delete_entry(id):
            console.print(f"Entry ID {id} deleted successfully.")
        else:
            console.print(f"[bold red]Error:[/bold red] Failed to delete entry ID {id}.")
    elif sheet_name:
        sheet_to_delete = get_sheet_by_name(sheet_name)
        if not sheet_to_delete:
            console.print(f"[bold red]Error:[/bold red] Sheet '{sheet_name}' not found.")
            raise typer.Exit(code=1)
        if not yes:
            confirm = typer.confirm(f"Are you sure you want to delete sheet '{sheet_name}' and all its entries?")
            if not confirm:
                console.print("Deletion cancelled.")
                raise typer.Exit()
        if delete_sheet(sheet_name):
            # If the deleted sheet was the current one, unset it
            if get_current_sheet_name() == sheet_name:
                if os.path.exists(CURRENT_SHEET_FILE):
                    os.remove(CURRENT_SHEET_FILE)
            console.print(f"Sheet '{sheet_name}' and all its entries deleted successfully.")
        else:
            console.print(f"[bold red]Error:[/bold red] Failed to delete sheet '{sheet_name}'.")
    else:
        console.print("[bold red]Error:[/bold red] Please specify either an --id or a sheet name to kill.")
        raise typer.Exit(code=1)

@timetrap_app.command("list")
def list_sheets():
    """
    List the available timesheets.
    """
    sheet(None) # Re-use the sheet command's listing functionality


# --- Main execution ---
if __name__ == "__main__":
    timetrap_app()