from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
import time
import os
import platform
from datetime import datetime
import typer
import json
from pathlib import Path

focus_app = typer.Typer()

def play_sound():
    if platform.system() == "Windows":
        import winsound
        winsound.Beep(1000, 500)
    else:
        print('\a') 

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
    hours: int = typer.Option(0, "--hours", "-h", help="Focus session duration in hours"),
    break_every: int = typer.Option(0, "--break-every", help="Take a break every N minutes"),
    break_duration: int = typer.Option(0, "--break-duration", help="Break duration in minutes")
):
    """Starts a focus session with optional breaks."""
    console = Console()
    total_seconds = (hours * 60 + minutes) * 60

    if total_seconds == 0:
        console.print("[bold red]Error:[/bold red] Duration must be greater than 0.")
        raise typer.Exit()

    if break_every and break_duration and break_every * 60 >= total_seconds:
        console.print("[yellow]⚠️ Break interval is greater than or equal to session time. Ignoring breaks.[/yellow]")
        break_every = 0

    console.print(Text(f"🔔 Starting {hours}h {minutes}m focus session...", style="bold green"))

    seconds_passed = 0
    with Live(refresh_per_second=4) as live:
        while seconds_passed < total_seconds:
            remaining = total_seconds - seconds_passed
            mins, secs = divmod(remaining, 60)
            hrs, mins = divmod(mins, 60)
            time_str = f"{hrs:02}:{mins:02}:{secs:02}"
            quote = get_quote(remaining)
            timer_text = f"⏳ [bold magenta]{time_str}[/bold magenta]\n[italic yellow]{quote}[/italic yellow]"
            panel = Panel.fit(timer_text, title="🎯 Focus Mode")
            live.update(panel)
            time.sleep(1)
            seconds_passed += 1

            if break_every and seconds_passed % (break_every * 60) == 0 and seconds_passed < total_seconds:
                play_sound()
                console.print(f"\n[cyan]⏸️ Time for a {break_duration}-minute break![/cyan]")
                
                # Ask user to skip
                skip = typer.confirm("❓ Do you want to skip this break?", default=False)
                if skip:
                    console.print("[yellow]⏭️ Skipping break... Back to work![/yellow]")
                    continue

                break_secs = break_duration * 60
                for b in range(break_secs, 0, -1):
                    b_min, b_sec = divmod(b, 60)
                    b_time = f"{b_min:02}:{b_sec:02}"
                    live.update(Panel(f"🧘 Break Time: [bold magenta]{b_time}[/bold magenta]", title="☕ Take a Break"))
                    time.sleep(1)
                
                console.print("[green]✅ Break over. Back to focus![/green]")

        live.update(Panel("[bold green]✅ Done! Take a longer break now.[/bold green]", title="👏 Session Complete"))
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