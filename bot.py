import time
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import psutil

class MyHandler(FileSystemEventHandler):
    def __init__(self):
        self.bot_process = None
        self.running = False  # Flag to indicate if the process is running

    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print("Reloading main.py...")
            self.restart_bot()  # Always restart the process when a change is detected

    def restart_bot(self):
        if self.bot_process:
            if self.is_process_running(self.bot_process.pid):
                print("Terminating previous main.py process...")
                self.bot_process.kill()
        # Start new process
        print("Starting new main.py process...")
        self.running = True  # Set the flag to indicate the process is running
        self.bot_process = subprocess.Popen(["python3", "main.py"])

    def is_process_running(self, pid):
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False

if __name__ == "__main__":
    event_handler = MyHandler()
    observer = Observer()
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()

    # Start the initial process when running the code
    event_handler.restart_bot()
    
    try:
        print("Watchdog is running...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping Watchdog...")
        observer.stop()
    observer.join()
