#!/bin/bash
# Installation script for Pi Camera streaming dependencies

echo "Installing required packages for Pi Camera v3 streaming..."

# Update package list
sudo apt-get update

# Install Flask for web server
pip3 install flask --break-system-packages

# picamera2 should already be installed on Raspberry Pi OS
# If not, install it:
# sudo apt-get install -y python3-picamera2

echo ""
echo "Installation complete!"
echo ""
echo "To run the camera stream:"
echo "1. Make the script executable: chmod +x camera_stream.py"
echo "2. Run it: python3 camera_stream.py"
echo "3. Find your Pi's IP address: hostname -I"
echo "4. Open your browser to: http://<pi-ip-address>:5000"
echo ""
