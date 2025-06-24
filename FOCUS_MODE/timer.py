import time
import sys

def countdown(seconds: int):
    while seconds:
        mins, secs = divmod(seconds, 60)
        timer = f"{mins:02d}:{secs:02d}"
        print(f"\r⏳ {timer}", end="")
        time.sleep(1)
        seconds -= 1
    print("\r🛎️  Time's up!                        ")
