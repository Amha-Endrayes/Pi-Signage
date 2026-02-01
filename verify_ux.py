import subprocess
import requests
import time
import os
import sys

def run_verification():
    print("Starting Master Node...")
    # Start flask app in background
    master_proc = subprocess.Popen([sys.executable, 'master/app.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
    
    try:
        time.sleep(3) # Wait for startup
        
        session = requests.Session()
        
        # 1. Login
        print("Testing Login...")
        r = session.post('http://localhost:5000/login', data={'pin': '1234'})
        if r.status_code == 200 and 'Dashboard' in r.text:
            print("Login Successful.")
        else:
            print(f"Login Failed: {r.status_code}")
            return

        # 2. Check Branding
        print("Checking Rebranding...")
        if "CIKET Signage" in r.text:
            print("Rebranding Verified.")
        else:
            print("Rebranding Failed: 'CIKET Signage' not found in dashboard.")

        # 3. Test Restart API
        print("Testing Restart API...")
        r = session.post('http://localhost:5000/api/restart')
        if r.status_code == 200 and r.json()['success']:
            print("Restart Signal Sent.")
        else:
            print(f"Restart API Failed: {r.status_code}")

    except Exception as e:
        print(f"Verification Failed: {e}")
    finally:
        print("Cleaning up...")
        master_proc.terminate()

if __name__ == "__main__":
    run_verification()
