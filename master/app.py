from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
import os
import database
import hashlib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'videos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB
database.init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'mp4', 'mkv', 'avi', 'mov'}

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    videos = database.get_all_videos()
    state = database.get_state()
    playlist = database.get_playlist()
    return render_template('dashboard.html', videos=videos, state=state, playlist=playlist)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        state = database.get_state()
        db_pin = state.get('pin', '1234')
        if request.form.get('pin') == db_pin:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid PIN")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/api/upload', methods=['POST'])
def upload_file():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)
        
        # Add to DB
        new_id = database.add_video(filename)
        return jsonify({'success': True, 'id': new_id, 'filename': filename})
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/api/delete/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    videos = database.get_all_videos()
    target = next((v for v in videos if v['id'] == video_id), None)
    
    if target:
        # Remove file
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, target['filename']))
        except OSError:
            pass # File might be gone already
            
        database.delete_video(video_id)
        return jsonify({'success': True})
    return jsonify({'error': 'Video not found'}), 404

@app.route('/api/rotate/<int:video_id>', methods=['POST'])
def rotate_video(video_id):
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    rotation = int(data.get('rotation', 0))
    database.update_video_rotation(video_id, rotation)
    return jsonify({'success': True})

@app.route('/api/state', methods=['POST'])
def update_state():
    """Update global playback mode or basic settings"""
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    if 'mode' in data:
        database.set_state('mode', data['mode'])
    if 'current_video_id' in data:
        database.set_state('current_video_id', data['current_video_id'])
    if 'paused' in data:
        database.set_state('paused', 'true' if data['paused'] else 'false')
        
    return jsonify({'success': True})

@app.route('/api/restart', methods=['POST'])
def restart_clients():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Update restart_id to current timestamp
    import time
    database.set_state('restart_id', str(int(time.time())))
    return jsonify({'success': True})

@app.route('/api/playlist', methods=['POST'])
def update_playlist():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json
    # Expects {'video_ids': [1, 3, 2]}
    database.set_playlist(data.get('video_ids', []))
    return jsonify({'success': True})

@app.route('/api/pin', methods=['POST'])
def update_pin():
    if not session.get('logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    new_pin = data.get('pin')
    
    if not new_pin or not str(new_pin).isdigit():
        return jsonify({'error': 'PIN must be numeric'}), 400
        
    database.set_state('pin', str(new_pin))
    return jsonify({'success': True})

@app.route('/api/status', methods=['POST'])
def update_client_status():
    data = request.json
    now_playing = data.get('current_video', 'Stopped')
    database.set_state('now_playing', now_playing)
    # Update heartbeat as well
    import time
    database.set_state('last_heartbeat', str(int(time.time())))
    return jsonify({'success': True})

@app.route('/api/manifest', methods=['GET'])
def get_manifest():
    """
    Called by clients to get the current state and list of required files.
    """
    state = database.get_state()
    videos = database.get_all_videos()
    playlist = database.get_playlist()
    
    # We provide a full list of videos so client can download them
    # And the current logic (what to play)
    return jsonify({
        'mode': state.get('mode', 'single'),
        'current_single_id': state.get('current_video_id'),
        'paused': state.get('paused', 'false') == 'true',
        'restart_id': state.get('restart_id', '0'),
        'now_playing': state.get('now_playing', 'Stopped'),
        'last_heartbeat': state.get('last_heartbeat', '0'),
        'playlist': playlist,
        'all_videos': videos,  # Metadata for all available videos
        'timestamp': os.stat(database.DB_PATH).st_mtime # Simple change detection
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
