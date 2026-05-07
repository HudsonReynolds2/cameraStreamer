#!/usr/bin/env python3
"""
Pi Camera v3 Web Streaming Server
Streams camera feed at maximum quality to web browser
"""

from flask import Flask, Response, render_template_string, request, jsonify
from picamera2 import Picamera2
from libcamera import Transform
import io
import time

app = Flask(__name__)

# Initialize camera
picam2 = Picamera2()

# Camera settings
current_resolution = (1920, 1080)
current_fps = 30
rotation = 0
autofocus_mode = "continuous"  # continuous or manual
manual_focus_value = 0.0  # 0.0 (infinity) to 10.0 (close)

# Available resolutions for Pi Camera v3
RESOLUTIONS = {
    "480p": (640, 480),
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "2K": (2304, 1296),
    "4K": (4608, 2592)
}

# Create captures directory
import os
CAPTURE_DIR = "/home/hudsonre/Desktop/camera_server/captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)

def configure_camera():
    """Configure camera with current settings"""
    global picam2, current_resolution, rotation, autofocus_mode, manual_focus_value
    
    # Create transform for rotation
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
        buffer_count=4
    )
    
    picam2.configure(video_config)
    
    # Set focus mode
    if autofocus_mode == "continuous":
        picam2.set_controls({"AfMode": 2})  # 2 = Continuous AF
    else:
        picam2.set_controls({"AfMode": 0, "LensPosition": manual_focus_value})  # 0 = Manual

configure_camera()
picam2.start()

# Give camera time to warm up
time.sleep(2)


def generate_frames():
    """Generator function to yield JPEG frames for streaming"""
    global current_fps
    while True:
        # Capture frame as JPEG
        stream = io.BytesIO()
        picam2.capture_file(stream, format='jpeg')
        frame = stream.getvalue()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        
        # Delay based on current FPS setting
        time.sleep(1.0 / current_fps)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Camera v3 Stream</title>
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
        h1 {
            color: #ffffff;
            margin-bottom: 20px;
        }
        .container {
            max-width: 100%;
            text-align: center;
        }
        img {
            max-width: 100%;
            height: auto;
            border: 2px solid #333;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.5);
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
        .control-group label {
            color: #aaa;
            font-size: 14px;
            font-weight: bold;
        }
        select, button, input[type="range"] {
            padding: 10px 15px;
            font-size: 14px;
            border: 1px solid #444;
            border-radius: 5px;
            background-color: #2a2a2a;
            color: #fff;
            cursor: pointer;
            transition: all 0.3s;
        }
        input[type="range"] {
            width: 150px;
            padding: 5px;
        }
        select {
            min-width: 120px;
        }
        button {
            min-width: 100px;
        }
        button:hover, select:hover {
            background-color: #3a3a3a;
            border-color: #666;
        }
        button:active {
            background-color: #1a1a1a;
        }
        .rotate-btn {
            background-color: #0066cc;
            border-color: #0066cc;
        }
        .rotate-btn:hover {
            background-color: #0052a3;
        }
        .capture-btn {
            background-color: #4CAF50;
            border-color: #4CAF50;
            font-weight: bold;
        }
        .capture-btn:hover {
            background-color: #45a049;
        }
        .focus-btn {
            background-color: #ff9800;
            border-color: #ff9800;
        }
        .focus-btn:hover {
            background-color: #e68900;
        }
        .focus-controls {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 15px;
            background-color: #2a2a2a;
            border-radius: 8px;
            border: 1px solid #444;
        }
        #manualFocusControls {
            display: none;
        }
        .focus-value {
            color: #fff;
            font-size: 12px;
        }
        .info {
            color: #aaa;
            margin-top: 15px;
            font-size: 14px;
        }
        .status {
            color: #4CAF50;
            font-size: 12px;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <h1>Pi Camera v3 - Live Stream</h1>
    
    <div class="controls">
        <div class="control-group">
            <label>Resolution</label>
            <select id="resolution" onchange="updateSettings()">
                <option value="480p">480p (640x480)</option>
                <option value="720p">720p (1280x720)</option>
                <option value="1080p" selected>1080p (1920x1080)</option>
                <option value="2K">2K (2304x1296)</option>
                <option value="4K">4K (4608x2592)</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>Frame Rate</label>
            <select id="framerate" onchange="updateSettings()">
                <option value="15">15 FPS</option>
                <option value="24">24 FPS</option>
                <option value="30" selected>30 FPS</option>
                <option value="60">60 FPS</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>Rotation</label>
            <button class="rotate-btn" onclick="rotateCamera()">Rotate 90°</button>
        </div>
        
        <div class="control-group">
            <label>Focus Mode</label>
            <select id="focusMode" onchange="changeFocusMode()">
                <option value="continuous" selected>Auto Focus</option>
                <option value="manual">Manual Focus</option>
            </select>
        </div>
        
        <div class="control-group">
            <label>Capture</label>
            <button class="capture-btn" onclick="captureImage()">📷 Capture Image</button>
        </div>
    </div>
    
    <div class="controls" id="manualFocusControls">
        <div class="focus-controls">
            <label>Manual Focus Position</label>
            <input type="range" id="focusSlider" min="0" max="10" step="0.1" value="5.0" oninput="updateFocus()">
            <div class="focus-value">
                <span id="focusValue">5.0</span> (0=Infinity, 10=Close)
            </div>
        </div>
    </div>
    
    <div class="container">
        <img src="{{ url_for('video_feed') }}" alt="Camera Stream" id="videoStream">
        <div class="info">
            Current: <span id="currentRes">1920x1080</span> @ <span id="currentFps">30</span> FPS | Rotation: <span id="currentRotation">0</span>°
        </div>
        <div class="status" id="status"></div>
    </div>
    
    <script>
        function updateSettings() {
            const resolution = document.getElementById('resolution').value;
            const framerate = document.getElementById('framerate').value;
            
            document.getElementById('status').textContent = 'Updating settings...';
            
            fetch('/update_settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    resolution: resolution,
                    framerate: parseInt(framerate)
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('currentRes').textContent = data.resolution;
                document.getElementById('currentFps').textContent = data.framerate;
                document.getElementById('status').textContent = 'Settings updated! Reloading stream...';
                
                // Reload the video stream
                setTimeout(() => {
                    const img = document.getElementById('videoStream');
                    img.src = img.src.split('?')[0] + '?t=' + new Date().getTime();
                    document.getElementById('status').textContent = '';
                }, 1000);
            });
        }
        
        function rotateCamera() {
            document.getElementById('status').textContent = 'Rotating camera...';
            
            fetch('/rotate', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('currentRotation').textContent = data.rotation;
                document.getElementById('status').textContent = 'Camera rotated! Reloading stream...';
                
                // Reload the video stream
                setTimeout(() => {
                    const img = document.getElementById('videoStream');
                    img.src = img.src.split('?')[0] + '?t=' + new Date().getTime();
                    document.getElementById('status').textContent = '';
                }, 1000);
            });
        }
        
        function changeFocusMode() {
            const mode = document.getElementById('focusMode').value;
            const manualControls = document.getElementById('manualFocusControls');
            
            if (mode === 'manual') {
                manualControls.style.display = 'flex';
            } else {
                manualControls.style.display = 'none';
            }
            
            document.getElementById('status').textContent = 'Changing focus mode...';
            
            fetch('/set_focus_mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    mode: mode
                })
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('status').textContent = data.message;
                setTimeout(() => {
                    document.getElementById('status').textContent = '';
                }, 2000);
            });
        }
        
        function updateFocus() {
            const focusValue = document.getElementById('focusSlider').value;
            document.getElementById('focusValue').textContent = focusValue;
            
            fetch('/set_focus', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    focus: parseFloat(focusValue)
                })
            })
            .then(response => response.json())
            .then(data => {
                // Silent update, no status message
            });
        }
        
        function captureImage() {
            document.getElementById('status').textContent = '📷 Capturing image...';
            
            fetch('/capture', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('status').textContent = '✓ Image saved: ' + data.filename;
                    setTimeout(() => {
                        document.getElementById('status').textContent = '';
                    }, 3000);
                } else {
                    document.getElementById('status').textContent = '✗ Capture failed!';
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Main page with video stream"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/update_settings', methods=['POST'])
def update_settings():
    """Update resolution and framerate"""
    global current_resolution, current_fps, picam2
    
    data = request.json
    resolution_name = data.get('resolution', '1080p')
    fps = data.get('framerate', 30)
    
    # Update settings
    current_resolution = RESOLUTIONS[resolution_name]
    current_fps = fps
    
    # Restart camera with new settings
    picam2.stop()
    configure_camera()
    picam2.start()
    time.sleep(1)  # Wait for camera to stabilize
    
    return jsonify({
        'resolution': f"{current_resolution[0]}x{current_resolution[1]}",
        'framerate': current_fps
    })


@app.route('/rotate', methods=['POST'])
def rotate():
    """Rotate camera view by 90 degrees"""
    global rotation, picam2
    
    # Cycle through rotations: 0 -> 90 -> 180 -> 270 -> 0
    rotation = (rotation + 90) % 360
    
    # Restart camera with new rotation
    picam2.stop()
    configure_camera()
    picam2.start()
    time.sleep(1)  # Wait for camera to stabilize
    
    return jsonify({'rotation': rotation})


@app.route('/set_focus_mode', methods=['POST'])
def set_focus_mode():
    """Set focus mode (continuous or manual)"""
    global autofocus_mode, picam2
    
    data = request.json
    mode = data.get('mode', 'continuous')
    autofocus_mode = mode
    
    # Update camera focus mode
    if autofocus_mode == "continuous":
        picam2.set_controls({"AfMode": 2})  # Continuous AF
        message = "Auto focus enabled"
    else:
        picam2.set_controls({"AfMode": 0})  # Manual
        message = "Manual focus enabled"
    
    return jsonify({'mode': autofocus_mode, 'message': message})


@app.route('/set_focus', methods=['POST'])
def set_focus():
    """Set manual focus position"""
    global manual_focus_value, picam2, autofocus_mode
    
    data = request.json
    focus_value = data.get('focus', 5.0)
    manual_focus_value = focus_value
    
    # Only apply if in manual mode
    if autofocus_mode == "manual":
        picam2.set_controls({"LensPosition": manual_focus_value})
    
    return jsonify({'focus': manual_focus_value})


@app.route('/capture', methods=['POST'])
def capture():
    """Capture a high-resolution image"""
    from datetime import datetime
    
    try:
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        filepath = os.path.join(CAPTURE_DIR, filename)
        
        # Capture image at current resolution
        picam2.capture_file(filepath)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'path': filepath
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })



if __name__ == '__main__':
    try:
        print("Starting camera stream server...")
        print("Access the stream at: http://<your-pi-ip>:5000")
        print("Press Ctrl+C to stop")
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        picam2.stop()
        picam2.close()
