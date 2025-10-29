# Camera Streamer

A simple Python script to stream your webcam over HTTP. Particularly useful for accessing a Windows webcam from WSL2.

## What it does

Streams your webcam video feed over your local network using Flask and OpenCV. You can access the stream from any browser on your network, including WSL2 environments.

## Requirements

- Python 3.x
- OpenCV (`cv2`)
- Flask

## Installation
```bash
pip install opencv-python flask
```

## Usage

1. Run the script:
```bash
python cameraStreamer.py
```

2. Access the stream:
   - **Local browser**: http://localhost:5000
   - **Network devices**: http://YOUR_IP:5000
   - **Direct video feed**: http://YOUR_IP:5000/video_feed

The script will display the URLs when it starts.

## Firewall Note

Make sure Windows Firewall allows connections on port 5000, or you won't be able to access the stream from other devices/WSL2.

## Use Case

This is especially helpful when you need to access a Windows webcam from WSL2, as WSL2 doesn't have direct access to Windows hardware. Just run this script in Windows and access the stream from your WSL2 environment.

## License

MIT
