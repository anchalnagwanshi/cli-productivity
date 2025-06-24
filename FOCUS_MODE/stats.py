import typer
import datetime
import json
import os


stats_app = typer.Typer()

LOG_FILE = "focus_log.json"

def log_session(duration: int):
    now = datetime.datetime.now().isoformat()
    data = {"timestamp": now, "duration_minutes": duration}
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(data)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=4)

def get_today_sessions():
    if not os.path.exists(LOG_FILE):
        return 0, 0

    with open(LOG_FILE, "r") as f:
        logs = json.load(f)
    
    today = datetime.date.today().isoformat()
    today_logs = [log for log in logs if log["date"] == today]
    count = len(today_logs)
    total_minutes = sum(log["duration_minutes"] for log in today_logs)
    return count, total_minutes

@stats_app.command()
def stats():
    """Show how many focus sessions you've completed today."""
    count, total_minutes = get_today_sessions()
    if count == 0:
        typer.echo("No focus sessions completed today.")
    else:
        typer.echo(f"📅 Sessions today: {count}")
        typer.echo(f"⏱️ Total focused time: {total_minutes} minutes")


if __name__ == "__main__":
    stats_app()
