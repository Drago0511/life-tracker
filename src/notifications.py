import subprocess
import sys


def notify(title: str, message: str) -> None:
    if sys.platform != "darwin":
        return
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], check=False)
