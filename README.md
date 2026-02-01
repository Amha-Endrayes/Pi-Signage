# CIKET Signage Pro 🚀

A DIY, lightweight, and powerful digital signage system designed for Raspberry Pi (and other Linux/Windows machines). Featuring a stunning glassmorphism dashboard and instant real-time controls.

![CIKET Signage Pro](https://via.placeholder.com/800x450?text=CIKET+Signage+Pro+Dashboard)

## ✨ Features

- **Master/Client Architecture**: One master dashboard to control multiple signage screens.
- **Premium Glassmorphism UI**: A dark-themed, modern dashboard for managing content.
- **Mobile Responsive**: Full control from your smartphone, tablet, or desktop.
- **Real-time Status**: "Now Playing" indicators and client heartbeat monitoring.
- **Instant Controls**: Near-instant (0.5s) playback control responsiveness.
- **Seamless Playback**: MPV-based engine for hardware-accelerated, gapless video loops.
- **Smart Sync**: Clients automatically download and cache content from the master.
- **Upload Progress**: Visual feedback and status updates for large video uploads.
- **Security**: PIN-protected dashboard access.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, SQLite
- **Frontend**: Vanilla JS (ES6+), CSS3 (Glassmorphism), HTML5
- **Player**: MPV (via `python-mpv` patterns)
- **Sync**: HTTP/REST API

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+
- `mpv` player installed in your system PATH.
- `ffmpeg` (optional, for thumbnail generation if added later).

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/Pi-Signage.git
cd Pi-Signage
pip install -r requirements.txt
```

### 3. Running the Master Node
The master node hosts the dashboard and serves content to clients.
```bash
python master/app.py
```
- **Login**: `http://localhost:5000`
- **PIN**: `1234`

### 4. Running the Client Agent
The agent runs on the display device, syncs files, and manages playback.
```bash
# Point to your master node URL
set MASTER_URL=http://your-master-ip:5000
python client/agent.py
```

## 📂 Project Structure

- `master/`: Flask backend and dashboard templates.
- `client/`: Agent logic for polling, syncing, and playback control.
- `shared/`: Shared player wrapper and utilities.
- `static/videos/`: Storage for uploaded media files.

## 🤝 Contributing
Feel free to open issues or submit pull requests to improve CIKET Signage Pro!

## 📜 License
MIT License. Free to use for personal and commercial projects.
