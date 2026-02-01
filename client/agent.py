import sys
import os
import time
import requests
import logging

# Add parent dir to path to import shared modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.player import Player

# Configuration
MASTER_URL = os.environ.get('MASTER_URL', 'http://localhost:5000')
CLIENT_VIDEO_DIR = os.path.join(os.path.dirname(__file__), 'videos')
CHECK_INTERVAL = 0.5  # Reduced for near-instant responsiveness (0.5s is safe for local network)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ensure_dir_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)

def sync_files(remote_videos):
    """
    Downloads missing videos from master.
    Returns True if any file was downloaded (implies we might need to refresh).
    """
    ensure_dir_exists(CLIENT_VIDEO_DIR)
    local_files = set(os.listdir(CLIENT_VIDEO_DIR))
    remote_map = {v['filename']: v for v in remote_videos}
    remote_filenames = set(remote_map.keys())
    
    changed = False

    # Download missing
    for fname in remote_filenames:
        if fname not in local_files:
            logging.info(f"Downloading new video: {fname}")
            try:
                url = f"{MASTER_URL}/static/videos/{fname}"
                r = requests.get(url, stream=True)
                if r.status_code == 200:
                    with open(os.path.join(CLIENT_VIDEO_DIR, fname), 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                    changed = True
                else:
                    logging.error(f"Failed to download {fname}: {r.status_code}")
            except Exception as e:
                logging.error(f"Download error: {e}")

    # Cleanup extra (Optional: strict sync)
    for fname in local_files:
        if fname not in remote_filenames:
            logging.info(f"Removing old video: {fname}")
            try:
                os.remove(os.path.join(CLIENT_VIDEO_DIR, fname))
            except OSError:
                pass

    return changed

def main():
    player = Player()
    
    current_mode = None
    current_single_id = None
    playlist_index = 0
    was_paused = False
    last_restart_id = '0'
    
    logging.info(f"Starting Client Agent for Master: {MASTER_URL}")

    while True:
        try:
            # Poll Master
            r = requests.get(f"{MASTER_URL}/api/manifest", timeout=2)
            if r.status_code == 200:
                data = r.json()
                
                # 0. Check Restart
                remote_restart = data.get('restart_id', '0')
                if remote_restart != '0' and remote_restart != last_restart_id:
                    if last_restart_id != '0':
                        logging.info("Restart signal received. Hard stopping player.")
                        player.stop()
                    last_restart_id = remote_restart

                # 1. Sync Files
                sync_files(data['all_videos'])
                
                # 2. Determine State
                server_mode = data['mode']
                server_single_id = int(data['current_single_id']) if data['current_single_id'] else None
                server_paused = data.get('paused', False)
                
                # Update Playlist logic
                video_map = {v['id']: v for v in data['all_videos']}
                new_playlist = []
                for item in data['playlist']:
                    vid = video_map.get(item['id'])
                    if vid:
                        new_playlist.append(vid)

                # --- Handle Play/Pause ---
                if server_paused != was_paused:
                    logging.info(f"Setting pause: {server_paused}")
                    player.set_pause(server_paused)
                    was_paused = server_paused

                # --- State Machine ---
                
                # Case A: Single Video Mode
                if server_mode == 'single':
                    target_vid = video_map.get(server_single_id)
                    if target_vid:
                        # Logic to switch video or rotation
                        should_play = False
                        if current_mode != 'single' or current_single_id != server_single_id:
                            should_play = True
                        elif player.rotation != target_vid['rotation']:
                             player.set_rotation(target_vid['rotation'])
                        elif not player.is_playing() and not server_paused:
                             should_play = True
                        
                        if should_play:
                            logging.info(f"Switching to Single: {target_vid['filename']}")
                            path = os.path.join(CLIENT_VIDEO_DIR, target_vid['filename'])
                            player.play(path, target_vid['rotation'], loop=True)
                            
                            current_mode = 'single'
                            current_single_id = server_single_id
                
                # Case B: Playlist Mode
                elif server_mode == 'playlist':
                    if not new_playlist:
                        player.stop()
                        current_mode = 'playlist'
                    else:
                        if current_mode != 'playlist':
                            logging.info("Switching to Playlist mode")
                            current_mode = 'playlist'
                            playlist_index = 0
                            
                            # Initial play
                            track = new_playlist[playlist_index % len(new_playlist)]
                            path = os.path.join(CLIENT_VIDEO_DIR, track['filename'])
                            player.play(path, track['rotation'], loop=False)
                            playlist_index += 1
                        
                        # Monitor for transition: either not playing OR specifically idle
                        elif not player.is_playing() and not server_paused:
                            # It's idle (finished playing)
                            track = new_playlist[playlist_index % len(new_playlist)]
                            logging.info(f"Playlist auto-advance: {track['filename']}")
                            path = os.path.join(CLIENT_VIDEO_DIR, track['filename'])
                            player.play(path, track['rotation'], loop=False)
                            playlist_index += 1
            
                # --- Report Status to Master ---
                playing_filename = "Stopped"
                if player.is_playing():
                    if server_mode == 'single' and target_vid:
                        playing_filename = target_vid['filename']
                    elif server_mode == 'playlist' and len(new_playlist) > 0:
                        # For playlist, we need to know which one is actually playing
                        # Since we track index, we use the one before the increment (or current)
                        # Actually playlist_index is incremented AFTER play()
                        track = new_playlist[(playlist_index - 1) % len(new_playlist)]
                        playing_filename = track['filename']
                
                try:
                    requests.post(f"{MASTER_URL}/api/status", json={'current_video': playing_filename}, timeout=1)
                except:
                    pass # Don't block loop if status fails

            else:
                logging.warning(f"Master returned {r.status_code}")

        except requests.exceptions.ConnectionError:
            logging.warning("Connection to Master failed...")
        except Exception as e:
            logging.error(f"Agent Loop Error: {e}", exc_info=True)
            
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
