import subprocess
import os
import time
import logging
import json
import socket
import platform

class Player:
    def __init__(self):
        self.process = None
        self.current_video = None
        self.rotation = 0
        self.is_paused = False
        
        # Consistent IPC path
        if platform.system() == 'Windows':
            # Use a clean, unique pipe name
            self.ipc_path = r'\\.\pipe\mpv-signage'
        else:
            self.ipc_path = '/tmp/mpv-socket'

    def _build_mpv_cmd(self, mode: str):
        # Base flags (common)
        cmd = [
            "mpv",
            "--idle",
            "--fs",
            f"--input-ipc-server={self.ipc_path}",
            "--force-window=yes",
            "--no-terminal",
        
            # Headless DRM target
            "--drm-device=/dev/dri/card1",
            "--drm-connector=HDMI-A-1",
            "--drm-mode=1920x1080",
            "--drm-atomic=no",
        
            # No UI
            "--no-osc",
            "--osd-level=0",
            "--background=0.0/0.0/0.0",
        
            # HW decode (Pi best path)
            "--hwdec=v4l2m2m-copy",
            "--hwdec-codecs=h264,hevc",
        
            # HDMI audio (Pi)
            "--ao=alsa",
            "--audio-device=alsa/hdmi:CARD=vc4hdmi0,DEV=0",
            "--audio-channels=stereo",
            "--gapless-audio=yes",
        
            f"--log-file=/tmp/mpv-signage-{mode}.log",
        ]
        if mode == "gpu-fast":
            cmd += [
                "--vo=gpu",
                "--gpu-context=drm",
            ]
        elif mode == "gpu-safe":
            cmd += [
                "--vo=gpu",
                "--gpu-context=drm",
                "--gpu-dumb-mode=yes",
            ]
        elif mode == "drm":
            cmd += [
                "--vo=drm",
            ]
        else:
            raise ValueError(f"Unknown mpv mode: {mode}")

        return cmd

    def _mpv_log_has_errors(self, mode: str) -> bool:
        log_path = f"/tmp/mpv-signage-{mode}.log"
        try:
            if not os.path.exists(log_path):
                return False
            with open(log_path, "r", errors="ignore") as f:
                tail = f.read()[-4000:]  # last few KB
            bad = [
                "Failed to commit atomic request",
                "failed to set mode",
                "Permission denied",
                "No connected connectors found",
            ]
            return any(s in tail for s in bad)
        except Exception:
            return False

    def _start_mpv_with_fallback(self):
        # Remove stale IPC socket if mpv crashed previously
        try:
            if os.path.exists(self.ipc_path):
                os.remove(self.ipc_path)
        except Exception:
            pass

        for mode in ("gpu-fast", "gpu-safe", "drm"):
            cmd = self._build_mpv_cmd(mode)
            logging.info(f"Starting player process ({mode}): {' '.join(cmd)}")

            self.process = subprocess.Popen(cmd)
            time.sleep(1.0)  # give mpv time to init and write logs

            # If mpv died immediately, try next mode
            if self.process.poll() is not None:
                logging.warning(f"mpv exited early in mode {mode}, trying fallback...")
                continue

            # If mpv is running but log shows known DRM failures, restart with next mode
            if self._mpv_log_has_errors(mode):
                logging.warning(f"mpv reported DRM errors in mode {mode}, restarting with fallback...")
                try:
                    self._send(["quit"])
                    self.process.wait(timeout=2)
                except Exception:
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                self.process = None
                continue

            # Success
            return

        raise RuntimeError("Failed to start mpv in all modes (gpu-fast, gpu-safe, drm).")

    def _start_mpv(self):
        """Starts mpv in idle mode."""
        if self.process and self.process.poll() is None:
            return

        cmd = [
            "mpv",
            "--idle",
            "--fs",
            f"--input-ipc-server={self.ipc_path}",
            "--force-window=yes",
            "--background=000000",
            "--osd-level=0",
            "--no-terminal",
        ]

        if platform.system() != "Windows":
            is_headless = (os.environ.get("DISPLAY") is None) and (os.environ.get("WAYLAND_DISPLAY") is None)
            if is_headless:
                try:
                    self._start_mpv_with_fallback()
                    return
                except Exception as e:
                    logging.error(f"Critical error starting mpv with fallback: {e}")
                    return
            else:
                cmd += ["--hwdec=auto"]
        else:
            cmd += ["--hwdec=auto"]

        logging.info(f"Starting player process: {' '.join(cmd)}")
        try:
            self.process = subprocess.Popen(cmd)
            time.sleep(3)
        except Exception as e:
            logging.error(f"Critical error starting mpv: {e}")


    def _send(self, cmd_args, wait=False, retries=3):
        """Reliable IPC command delivery."""
        self._start_mpv()
        payload = json.dumps({"command": cmd_args}) + "\n"
        
        for attempt in range(retries):
            try:
                if platform.system() == 'Windows':
                    # Named Pipes on Windows work well with binary file I/O
                    with open(self.ipc_path, 'r+b', buffering=0) as f:
                        f.write(payload.encode())
                        if wait:
                            res = f.readline().decode()
                            return json.loads(res)
                else:
                    # Unix Sockets for Linux/macOS
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        s.settimeout(1.5)
                        s.connect(self.ipc_path)
                        s.sendall(payload.encode())
                        if wait:
                            res = s.recv(4096).decode()
                            return json.loads(res)
                return {"error": "success", "data": True}
            except Exception as e:
                logging.debug(f"IPC attempt {attempt+1} failed: {e}")
                time.sleep(0.5)
        
        return None

    def get_property(self, name):
        """Queries MPV state via IPC."""
        res = self._send(["get_property", name], wait=True)
        if res and res.get('error') == 'success':
            return res.get('data')
        return None

    def is_idle(self):
        """Returns True if MPV is sitting in idle mode (file finished)."""
        return self.get_property("idle-active") is True

    def play(self, video_path, rotation=0, loop=True):
        """Loads and plays a video seamlessly."""
        self._start_mpv()
        
        # 1. Switch file
        self._send(["loadfile", video_path, "replace"])
        
        # 2. Configure playback properties
        self.set_rotation(rotation)
        loop_val = "inf" if loop else "no"
        self._send(["set_property", "loop-file", loop_val])
        
        self.current_video = video_path
        self.rotation = rotation
        self.is_paused = False

    def set_pause(self, pause):
        """Remote pause/play."""
        state = "yes" if pause else "no"
        if self._send(["set_property", "pause", state]):
            self.is_paused = pause

    def set_rotation(self, rotation):
        """Real-time rotation adjustment."""
        # Property expects a string on some versions
        if self._send(["set_property", "video-rotate", str(rotation)]):
            self.rotation = rotation

    def stop(self):
        """Terminate the player."""
        if self.process:
            self._send(["quit"])
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            self.process = None

    def is_playing(self):
        """Checks if video data is actively being processed."""
        if self.process and self.process.poll() is None:
            # Not idle means it is playing a file
            return not self.is_idle()
        return False
