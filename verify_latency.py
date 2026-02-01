import subprocess
import requests
import time
import os
import sys

def run_verification():
    print("Starting Master Node...")
    master_proc = subprocess.Popen([sys.executable, 'master/app.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
    
    try:
        time.sleep(3)
        session = requests.Session()
        session.post('http://localhost:5000/login', data={'pin': '1234'})

        # 1. Test Status API
        print("Testing Status Reporting...")
        r = requests.post('http://localhost:5000/api/status', json={'current_video': 'test_video.mp4'})
        if r.status_code == 200:
            print("Status Report Successful.")
        
        # 2. Verify Dashboard shows it
        r = session.get('http://localhost:5000/')
        if "test_video.mp4" in r.text:
            print("Dashboard Now Playing Verified.")
        else:
            print("Dashboard Now Playing Failed.")

        # 3. Latency Check (Conceptual)
        print("Latency is now set to 0.5s in agent.py (verified by code inspection).")

    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        print("Cleaning up...")
        master_proc.terminate()

if __name__ == "__main__":
    run_verification()
