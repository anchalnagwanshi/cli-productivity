import typer
from prodcli.FOCUS_MODE.start import focus_app
from prodcli.FOCUS_MODE.stats import stats_app
from prodcli.TODO.todo_app import todo_app 
from prodcli.TIMETRACK.timetrap_app import timetrap_app
from prodcli.LEARNING.learning_app import learning_app 
from prodcli.TODO.dashboard import dashboard_app
import threading
import time
from plyer import notification
import sys

app = typer.Typer()
app.add_typer(todo_app, name="todo", help="Manage your ToDo tasks.")
app.add_typer(focus_app, name="focus", help="Start and manage focus sessions.")
app.add_typer(stats_app, name="stats", help="View focus session statistics.")
app.add_typer(dashboard_app, name="dashboard", help="View your productivity dashboard and calendar.")
app.add_typer(timetrap_app, name="timetrack", help="Track your time across different sheets.")
app.add_typer(learning_app, name="learning", help="Track your coding problems and learning progress.")


def show_reminder():
    notification.notify(
        title="⏰ Reminder",
        message="Don't forget to check or update your ToDo tasks!",
        timeout=10
    )

def reminder_loop():
    while True:
        time.sleep(3 * 60 * 60) 
        show_reminder()


@app.callback()
def main_callback():
   # Start the background reminder thread only once
    if not hasattr(main_callback, 'reminder_thread_started'):
        threading.Thread(target=reminder_loop, daemon=True).start()
        main_callback.reminder_thread_started = True

if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_reminder()
        time.sleep(5)
        sys.exit(0)
    else:
        app()



