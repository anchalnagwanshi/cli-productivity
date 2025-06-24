import typer
from FOCUS_MODE.start import focus_app
from FOCUS_MODE.stats import stats_app
from TODO.todo_app import todo_app 
from TIMETRACK.timetrap_app import timetrap_app
from TODO import dashboard
import threading
import time
from plyer import notification
import sys

app = typer.Typer()
app.add_typer(todo_app, name="todo")
app.add_typer(focus_app, name="focus")
app.add_typer(stats_app, name="stats")
app.add_typer(dashboard.app, name="dashboard")
app.add_typer(timetrap_app, name="timetrack")

def show_reminder():
    notification.notify(
        title="⏰ Reminder",
        message="Don't forget to check or update your ToDo tasks!",
        timeout=10
    )

def reminder_loop():
    while True:
        time.sleep(3 * 60 * 60)  # every 3 hours
        show_reminder()

@app.callback()
def main_callback():
    # Start the background reminder thread
    threading.Thread(target=reminder_loop, daemon=True).start()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No command provided → show popup and keep alive briefly
        show_reminder()
        time.sleep(5)  # wait for notification to show
    else:
        app()