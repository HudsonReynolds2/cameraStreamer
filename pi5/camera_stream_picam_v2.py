#!/usr/bin/env python3
"""
Pi Camera v2 Web Streaming Server
Streams camera feed to web browser via MJPEG

Designed for: Raspberry Pi 4B + Camera Module v2 (8MP, fixed focus)

Resolution notes:
  - Camera v2 max is 3280x2464 (8MP). The "Full" option uses this.
  - 30 FPS is only reliably achievable at 1080p and below.
  - At Full resolution expect ~5-10 FPS depending on network/encoding load.
  - 60 FPS in the UI is only realistic at 480p; at higher resolutions the
    camera simply won't deliver that many frames.
"""

from flask import Flask, Response, render_template_string, request, jsonify
from picamera2 import Picamera2
from libcamera import Transform
import io
import os
import time

app = Flask(__name__)

# Initialize camera
picam2 = Picamera2()

# Camera state
current_resolution = (1920, 1080)
current_fps = 30
rotation = 0

# Available resolutions for Pi Camera v2 (max 3280x2464)
RESOLUTIONS = {
    "480p":  (640, 480),
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    # NOTE: "Full" is the Camera v2's native 8MP resolution (3280x2464).
    # Streaming at this resolution is bandwidth-heavy and will drop to ~5-10 FPS.
    # It's most useful for the /capture endpoint, not live streaming.
    "Full":  (3280, 2464),
}

# Capture output directory
CAPTURE_DIR = "/home/hudsonre/Desktop/camera_server/captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)


def configure_camera():
    """Configure camera with current resolution and rotation."""
    global picam2, current_resolution, rotation

    transform = Transform(hflip=0, vflip=0)
    if rotation == 90:
        transform = Transform(hflip=0, vflip=1)
    elif rotation == 180:
        transform = Transform(hflip=1, vflip=1)
    elif rotation == 270:
        transform = Transform(hflip=1, vflip=0)

    video_config = picam2.create_video_configuration(
        main={"size": current_resolution, "format": "RGB888"},
        transform=transform,
        buffer_count=2,  # 2 is safer on Pi 4B; increase to 4 if you see underruns
    )
    picam2.configure(video_config)


configure_camera()
picam2.start()
time.sleep(2)  # Camera warm-up


def generate_frames():
    """Yield MJPEG frames for the /video_feed route."""
    global current_fps
    while True:
        stream = io.BytesIO()
        picam2.capture_file(stream, format="jpeg")
        frame = stream.getvalue()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )

        time.sleep(1.0 / current_fps)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera v2 Stream</title>
    <style>
        body {
            margin: 0;
            padding: 20px;
            background-color: #1a1a1a;
            font-family: Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        h1 { color: #ffffff; margin-bottom: 20px; }
        .container { max-width: 100%; text-align: center; }
        img {
            max-width: 100%;
            height: auto;
            border: 2px solid #333;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.5);
        }
        .controls {
            margin: 20px 0;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            justify-content: center;
            align-items: center;
        }
        .control-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
            align-items: center;
        }
        .control-group label { color: #aaa; font-size: 14px; font-weight: bold; }
        select, button {
            padding: 10px 15px;
            font-size: 14px;
            border: 1px solid #444;
            border-radius: 5px;
            background-color: #2a2a2a;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
        }
        select { min-width: 180px; }
        button { min-width: 100px; }
        button:hover, select:hover { background-color: #3a3a3a; border-color: #666; }
        .rotate-btn  { background-color: #0066cc; border-color: #0066cc; }
        .rotate-btn:hover { background-color: #0052a3; }
        .capture-btn { background-color: #4CAF50; border-color: #4CAF50; font-weight: bold; }
        .capture-btn:hover { background-color: #45a049; }
        .info  { color: #aaa; margin-top: 15px; font-size: 14px; }
        .note  { color: #f0a500; margin-top: 6px; font-size: 12px; }
        .status { color: #4CAF50; font-size: 12px; margin-top: 5px; }
    </style>
</head>
<body>
    <h1>Pi Camera v2 - Live Stream</h1>

    <div class="controls">
        <div class="control-group">
            <label>Resolution</label>
            <select id="resolution" onchange="updateSettings()">
                <option value="480p">480p (640x480)</option>
                <option value="720p">720p (1280x720)</option>
                <option value="1080p" selected>1080p (1920x1080)</option>
                <option value="Full">Full (3280x2464) — low FPS</option>
            </select>
        </div>

        <div class="control-group">
            <label>Frame Rate</label>
            <select id="framerate" onchange="updateSettings()">
                <option value="15">15 FPS</option>
                <option value="24">24 FPS</option>
                <option value="30" selected>30 FPS</option>
                <option value="60">60 FPS (480p only)</option>
            </select>
        </div>

        <div class="control-group">
            <label>Rotation</label>
            <button class="rotate-btn" onclick="rotateCamera()">Rotate 90°</button>
        </div>

        <div class="control-group">
            <label>Capture</label>
            <button class="capture-btn" onclick="captureImage()">📷 Capture Image</button>
        </div>
    </div>

    <div class="container">
        <img src="{{ url_for('video_feed') }}" alt="Camera Stream" id="videoStream">
        <div class="info">
            Current: <span id="currentRes">1920x1080</span>
            @ <span id="currentFps">30</span> FPS
            | Rotation: <span id="currentRotation">0</span>°
        </div>
        <div class="note">
            Camera v2 max resolution is 3280x2464 (8MP, fixed focus).
            30 FPS is only reliable at 1080p and below.
        </div>
        <div class="status" id="status"></div>
    </div>

    <script>
        function updateSettings() {
            const resolution = document.getElementById('resolution').value;
            const framerate  = document.getElementById('framerate').value;
            document.getElementById('status').textContent = 'Updating settings...';

            fetch('/update_settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resolution, framerate: parseInt(framerate) })
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('currentRes').textContent = data.resolution;
                document.getElementById('currentFps').textContent = data.framerate;
                document.getElementById('status').textContent = 'Settings updated! Reloading stream...';
                setTimeout(() => {
                    const img = document.getElementById('videoStream');
                    img.src = img.src.split('?')[0] + '?t=' + Date.now();
                    document.getElementById('status').textContent = '';
                }, 1000);
            });
        }

        function rotateCamera() {
            document.getElementById('status').textContent = 'Rotating camera...';
            fetch('/rotate', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                document.getElementById('currentRotation').textContent = data.rotation;
                document.getElementById('status').textContent = 'Camera rotated! Reloading stream...';
                setTimeout(() => {
                    const img = document.getElementById('videoStream');
                    img.src = img.src.split('?')[0] + '?t=' + Date.now();
                    document.getElementById('status').textContent = '';
                }, 1000);
            });
        }

        function captureImage() {
            document.getElementById('status').textContent = '📷 Capturing image...';
            fetch('/capture', { method: 'POST' })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = '✓ Saved: ' + data.filename;
                    setTimeout(() => { document.getElementById('status').textContent = ''; }, 3000);
                } else {
                    document.getElementById('status').textContent = '✗ Capture failed: ' + data.error;
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/update_settings', methods=['POST'])
def update_settings():
    global current_resolution, current_fps

    data = request.json
    resolution_name = data.get('resolution', '1080p')
    fps = data.get('framerate', 30)

    current_resolution = RESOLUTIONS[resolution_name]
    current_fps = fps

    picam2.stop()
    configure_camera()
    picam2.start()
    time.sleep(1)

    return jsonify({
        'resolution': f"{current_resolution[0]}x{current_resolution[1]}",
        'framerate': current_fps,
    })


@app.route('/rotate', methods=['POST'])
def rotate():
    global rotation

    rotation = (rotation + 90) % 360

    picam2.stop()
    configure_camera()
    picam2.start()
    time.sleep(1)

    return jsonify({'rotation': rotation})


@app.route('/capture', methods=['POST'])
def capture():
    from datetime import datetime
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"capture_{timestamp}.jpg"
        filepath  = os.path.join(CAPTURE_DIR, filename)
        picam2.capture_file(filepath)
        return jsonify({'success': True, 'filename': filename, 'path': filepath})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    try:
        print("Starting Pi Camera v2 stream server...")
        print("Access the stream at: http://<your-pi-ip>:5000")
        print("Press Ctrl+C to stop")
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        picam2.stop()
        picam2.close()
