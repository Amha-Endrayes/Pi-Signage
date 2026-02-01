import sqlite3
import os

DB_PATH = 'signage.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Videos table
    c.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            rotation INTEGER DEFAULT 0
        )
    ''') 
    
    # Settings/State table (Single row preferred for global state)
    c.execute('''
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Playlist table (Links videos to playlist order)
    c.execute('''
        CREATE TABLE IF NOT EXISTS playlist (
            position INTEGER PRIMARY KEY,
            video_id INTEGER,
            FOREIGN KEY(video_id) REFERENCES videos(id)
        )
    ''')

    # Insert default state if not exists
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('mode', 'single')")
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('current_video_id', '')")
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('paused', 'false')")
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('restart_id', '0')")
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('now_playing', 'Stopped')")
    c.execute("INSERT OR IGNORE INTO state (key, value) VALUES ('last_heartbeat', '0')")
    
    conn.commit()
    conn.close()

def add_video(filename, rotation=0):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO videos (filename, rotation) VALUES (?, ?)', (filename, rotation))
    videoid = c.lastrowid
    conn.commit()
    conn.close()
    return videoid

def get_all_videos():
    conn = get_db_connection()
    videos = conn.execute('SELECT * FROM videos').fetchall()
    conn.close()
    return [dict(v) for v in videos]

def delete_video(video_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    # Also remove from playlist
    conn.execute('DELETE FROM playlist WHERE video_id = ?', (video_id,))
    conn.commit()
    conn.close()

def update_video_rotation(video_id, rotation):
    conn = get_db_connection()
    conn.execute('UPDATE videos SET rotation = ? WHERE id = ?', (rotation, video_id))
    conn.commit()
    conn.close()

def get_state():
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM state').fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def set_state(key, value):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)', (key, str(value)))
    conn.commit()
    conn.close()

def get_playlist():
    conn = get_db_connection()
    # Join to get filenames
    query = '''
        SELECT playlist.position, videos.id, videos.filename, videos.rotation
        FROM playlist
        JOIN videos ON playlist.video_id = videos.id
        ORDER BY playlist.position ASC
    '''
    items = conn.execute(query).fetchall()
    conn.close()
    return [dict(i) for i in items]

def set_playlist(video_ids):
    """
    Replaces the current playlist with a new ordered list of video IDs.
    """
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('DELETE FROM playlist')
    for idx, vid in enumerate(video_ids):
        c.execute('INSERT INTO playlist (position, video_id) VALUES (?, ?)', (idx, vid))
    conn.commit()
    conn.close()
