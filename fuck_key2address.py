import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path

class Watcher:

    def __init__(self, directory_to_watch):
        self.observer = Observer()
        self.directory_to_watch = directory_to_watch

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.directory_to_watch, recursive=False)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:  # Graceful exit on Ctrl+C
            self.observer.stop()
            print("Observer Stopped")

        self.observer.join()


class Handler(FileSystemEventHandler):
    @staticmethod
    def on_created(event):
        if event.is_directory:
            return None

        print(f"Received created event - {event.src_path}.")
        if 'key2address.json' in event.src_path:
            try:
                os.remove(event.src_path)
                print(f"'key2address.json' found and deleted.")
            except FileNotFoundError:
                print(f"'key2address.json' not found or already deleted.")

if __name__ == '__main__':
    script_directory = Path(__file__).resolve().parent
    directory_to_watch = script_directory / ".commune/key"  # Ensure this is a valid directory path
    if not directory_to_watch.exists():
        print(f"Directory {directory_to_watch} does not exist.")
    else:
        w = Watcher(str(directory_to_watch))
        w.run()
