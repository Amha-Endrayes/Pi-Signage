import logging
import sys
import os
import time

# Add parent dir to path to import shared
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from shared.player import Player

logging.basicConfig(level=logging.INFO)

def test_launch():
    print("Initializing Player...")
    p = Player()
    
    print("Attempting to start MPV...")
    try:
        p._start_mpv()
        time.sleep(5)
        
        if p.process and p.process.poll() is None:
            print("SUCCESS: MPV is running!")
            print(f"Process PID: {p.process.pid}")
            # Try to send a command
            print("Sending get_property(version)...")
            ver = p.get_property("mpv-version")
            print(f"MPV Version via IPC: {ver}")
            p.stop()
        else:
            print("FAILURE: MPV is not running.")
            if p.process:
                print(f"Exit code: {p.process.poll()}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_launch()
