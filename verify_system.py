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
    
    # Wait for startup
    time.sleep(3)
    
    base_url = 'http://localhost:5000'
    session = requests.Session()
    
    try:
        # 1. Test Login
        print("Testing Login...")
        res = session.post(f'{base_url}/login', data={'pin': '1234'})
        if res.url == f'{base_url}/':
            print("Login Successful.")
        else:
            print("Login Failed!")
            return

        # 2. Upload Dummy Video
        print("Testing Upload...")
        with open('dummy.mp4', 'w') as f:
            f.write('dummy content')
            
        with open('dummy.mp4', 'rb') as f:
            files = {'file': ('test_video.mp4', f, 'video/mp4')}
            res = session.post(f'{base_url}/api/upload', files=files)
            print("Upload Response:", res.json())
            
        # 3. Test Rotation API
        print("Testing Rotation...")
        # Get ID from previous response or list
        res = session.get(f'{base_url}/') # HTML page, hard to parse.
        # Let's check manifest for video ID
        res = requests.get(f'{base_url}/api/manifest').json()
        print("Manifest:", res)
        
        video_id = res['all_videos'][0]['id']
        print(f"Found video ID: {video_id}, Rotation: {res['all_videos'][0]['rotation']}")
        
        # Rotate
        session.post(f'{base_url}/api/rotate/{video_id}', json={'rotation': 90})
        
        # Verify
        res = requests.get(f'{base_url}/api/manifest').json()
        new_rot = res['all_videos'][0]['rotation']
        print(f"New Rotation: {new_rot}")
        if new_rot == 90:
            print("Rotation Verified.")
        else:
            print("Rotation Failed.")

        # 4. Test Playlist Setting
        print("Testing Playlist Config...")
        session.post(f'{base_url}/api/playlist', json={'video_ids': [video_id]})
        session.post(f'{base_url}/api/state', json={'mode': 'playlist'})
        
        res = requests.get(f'{base_url}/api/manifest').json()
        if res['mode'] == 'playlist' and len(res['playlist']) > 0:
             print("Playlist Mode Verified.")
        else:
             print("Playlist Mode Failed.")

    except Exception as e:
        print(f"Test Failed with Exception: {e}")
    finally:
        print("Cleaning up...")
        master_proc.terminate()
        if os.path.exists('dummy.mp4'):
            os.remove('dummy.mp4')
            
if __name__ == '__main__':
    run_verification()
