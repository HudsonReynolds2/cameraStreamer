#!/usr/bin/env python3
"""
Pi Camera v2 Web Streaming Server
Raspberry Pi 4B + Camera Module v2 (8MP, fixed focus, imx219)

File layout:
  camera_stream.py        <- this file (Flask app + camera logic)
  templates/index.html    <- stream page
  templates/gallery.html  <- capture gallery
  static/style.css        <- shared styles
  static/stream.js        <- stream page JS
  static/gallery.js       <- gallery JS

CMA memory — add to /boot/firmware/config.txt and reboot:
  dtoverlay=vc4-kms-v3d,cma-512
(default 256MB causes DMA OOM at full still resolution)
Do NOT set max_framebuffers=2 — that is for dual HDMI, irrelevant headless.
"""

from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from picamera2 import Picamera2
from libcamera import Transform, controls as libcamera_controls
import io
import os
import time

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Camera init
# ---------------------------------------------------------------------------

picam2 = Picamera2()

# Streaming state
current_resolution = (1920, 1080)
current_fps        = 30
rotation           = 0

# Exposure/gain state
auto_exposure   = True
exposure_us     = 10000   # microseconds; only used in manual mode
analogue_gain   = 1.0     # 1.0–16.0; only used in manual mode

# Noise reduction: 0=off, 1=fast, 2=high quality
noise_mode = 1

RESOLUTIONS = {
    "480p":  (640, 480),
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
}

CAPTURE_DIR = "/home/hudsonre/Desktop/camera_server/captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_transform(rot: int) -> Transform:
    """Return a libcamera Transform for the given rotation (0/90/180/270)."""
    if rot == 90:
        return Transform(hflip=0, vflip=1)
    elif rot == 180:
        return Transform(hflip=1, vflip=1)
    elif rot == 270:
        return Transform(hflip=1, vflip=0)
    return Transform(hflip=0, vflip=0)


def fps_to_frame_duration(fps: int) -> int:
    """Convert FPS to frame duration in microseconds for FrameDurationLimits."""
    return int(1_000_000 / fps)


def configure_camera():
    """
    Configure the video stream with the current resolution, FPS, and rotation.
    FrameDurationLimits tells the sensor what frame rate to actually run at —
    this is what makes 60 FPS work, not just throttling the read loop.
    """
    global current_resolution, current_fps, rotation

    fd = fps_to_frame_duration(current_fps)

    video_config = picam2.create_video_configuration(
        main={"size": current_resolution, "format": "RGB888"},
        transform=make_transform(rotation),
        controls={"FrameDurationLimits": (fd, fd)},
        buffer_count=2,
    )
    picam2.configure(video_config)
    _apply_exposure_controls()


def _apply_exposure_controls():
    """Push current exposure/gain/noise settings to the camera."""
    ctrl = {"NoiseReductionMode": noise_mode}
    if auto_exposure:
        ctrl["AeEnable"] = True
    else:
        ctrl["AeEnable"]      = False
        ctrl["ExposureTime"]  = exposure_us
        ctrl["AnalogueGain"]  = analogue_gain
    picam2.set_controls(ctrl)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

configure_camera()
picam2.start()
time.sleep(2)


# ---------------------------------------------------------------------------
# MJPEG stream generator
# ---------------------------------------------------------------------------

def generate_frames():
    """
    Yield MJPEG frames. The camera's actual frame rate is controlled by
    FrameDurationLimits set in configure_camera(). The tiny sleep here just
    prevents busy-looping between capture_file calls.
    """
    while True:
        buf = io.BytesIO()
        picam2.capture_file(buf, format="jpeg")
        frame = buf.getvalue()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )
        time.sleep(0.005)


# ---------------------------------------------------------------------------
# Routes — stream
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/update_settings', methods=['POST'])
def update_settings():
    global current_resolution, current_fps

    data            = request.json
    res_name        = data.get('resolution', '1080p')
    fps             = int(data.get('framerate', 30))
    current_resolution = RESOLUTIONS.get(res_name, (1920, 1080))
    current_fps     = fps

    picam2.stop()
    configure_camera()
    picam2.start()
    time.sleep(1)

    return jsonify({
        'resolution': f"{current_resolution[0]}x{current_resolution[1]}",
        'framerate':  current_fps,
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


@app.route('/set_exposure', methods=['POST'])
def set_exposure():
    """
    Toggle auto/manual exposure, set exposure time and analogue gain.
    Exposure time is in microseconds. Analogue gain is 1.0–16.0.
    Noise reduction mode: 0=off, 1=fast, 2=high quality.
    """
    global auto_exposure, exposure_us, analogue_gain, noise_mode

    data = request.json
    if 'auto' in data:
        auto_exposure = bool(data['auto'])
    if 'exposure_us' in data:
        exposure_us = int(data['exposure_us'])
    if 'gain' in data:
        analogue_gain = float(data['gain'])
    if 'noise_mode' in data:
        noise_mode = int(data['noise_mode'])

    _apply_exposure_controls()

    return jsonify({
        'auto':        auto_exposure,
        'exposure_us': exposure_us,
        'gain':        analogue_gain,
        'noise_mode':  noise_mode,
    })


# ---------------------------------------------------------------------------
# Routes — captures
# ---------------------------------------------------------------------------

@app.route('/capture', methods=['POST'])
def capture():
    from datetime import datetime
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"capture_{timestamp}.jpg"
        filepath  = os.path.join(CAPTURE_DIR, filename)

        # Build still config with current rotation so orientation matches stream.
        # Recreated each time so it always reflects the latest rotation value.
        still_config = picam2.create_still_configuration(
            main={"size": (3280, 2464)},
            transform=make_transform(rotation),
        )
        picam2.switch_mode_and_capture_file(still_config, filepath)

        return jsonify({
            'success':    True,
            'filename':   filename,
            'path':       filepath,
            'resolution': '3280x2464',
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/captures')
def gallery():
    images = sorted(
        [f for f in os.listdir(CAPTURE_DIR)
         if f.lower().endswith(('.jpg', '.jpeg', '.png'))],
        reverse=True,
    )
    return render_template('gallery.html', images=images, capture_dir=CAPTURE_DIR)


@app.route('/captures/<filename>', methods=['GET'])
def serve_capture(filename):
    return send_from_directory(CAPTURE_DIR, filename)


@app.route('/captures/<filename>', methods=['DELETE'])
def delete_capture(filename):
    try:
        filepath = os.path.join(CAPTURE_DIR, filename)
        if not os.path.isfile(filepath):
            return jsonify({'success': False, 'error': 'File not found'})
        os.remove(filepath)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    try:
        print("Starting Pi Camera v2 stream server...")
        print("Stream:   http://<your-pi-ip>:5000")
        print("Gallery:  http://<your-pi-ip>:5000/captures")
        print("Press Ctrl+C to stop")
        app.run(host='0.0.0.0', port=5000, threaded=True, debug=False)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        picam2.stop()
        picam2.close()
