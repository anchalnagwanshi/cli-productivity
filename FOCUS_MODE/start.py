from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
import time

from datetime import datetime
import typer
import json
from pathlib import Path

focus_app = typer.Typer()

MOTIVATIONAL_QUOTES = [
    "Stay focused and keep coding.",
    "Success is the sum of small efforts repeated day in and day out.",
    "Work hard in silence, let your success be the noise.",
    "Discipline is the bridge between goals and accomplishment."
]

def get_quote(seconds_left):
    index = (seconds_left // 60) % len(MOTIVATIONAL_QUOTES)
    return MOTIVATIONAL_QUOTES[index]

@focus_app.command()
def start(
    minutes: int = typer.Option(0, "--minutes", "-m", help="Focus session duration in minutes"),
    hours: int = typer.Option(0, "--hours", "-h", help="Focus session duration in hours")
):
    console = Console()
    total_seconds = (hours * 60 + minutes) * 60

    if total_seconds == 0:
        console.print("[bold red]Error:[/bold red] Duration must be greater than 0.")
        raise typer.Exit()

    console.print(Text(f"🔔 Starting {hours}h {minutes}m focus session...", style="bold green"))

    with Live(refresh_per_second=4) as live:
        for remaining in range(total_seconds, 0, -1):
            mins, secs = divmod(remaining, 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs:02}:{mins:02}:{secs:02}"
            quote = get_quote(remaining)
            timer_text = f"⏳ [bold magenta]{time_str}[/bold magenta]\n[italic yellow]{quote}[/italic yellow]"
            panel = Panel.fit(timer_text, title="🎯 Focus Mode")
            live.update(panel)
            time.sleep(1)

        live.update(Panel("[bold green]✅ Done! Take a break.[/bold green]", title="👏 Session Complete"))
        log_focus_session(total_seconds)

LOG_FILE = Path("focus_log.json")

def log_focus_session(duration_seconds):
    now = datetime.now()
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "duration_minutes": duration_seconds // 60
    }

    if LOG_FILE.exists():
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(entry)

    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)


if __name__ == "__main__":
    focus_app()