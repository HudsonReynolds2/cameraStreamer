# cameraStreamer.py
# Runs in Windows, helps with getting a webcam to WSL etc.
import cv2
import socket
from flask import Flask, Response

app = Flask(__name__)
camera = cv2.VideoCapture(0)  # 0 = first webcam

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to find local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def gen_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue
        # encode as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<html><body><h1>Live Camera</h1><img src='/video_feed'></body></html>"

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"🔗 Starting camera server...")
    print(f"📷 Local access: http://localhost:5000")
    print(f"🌐 Network access: http://{local_ip}:5000")
    print(f"📡 For WSL2, try: http://{local_ip}:5000/video_feed")
    print(f"⚠️  Make sure Windows Firewall allows port 5000")
    
    app.run(host='0.0.0.0', port=5000)
