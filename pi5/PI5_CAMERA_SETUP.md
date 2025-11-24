# Pi 5 Camera v3 (IMX708) Setup Guide

Quick reference for getting the Arducam IMX708 working on Raspberry Pi 5.

## Hardware Connection

1. **Use the CAM1 port** (the CSI connector near the microHDMI not the ethernet.
   - CAM0 port may be faulty on some Pi 5 boards
   - CAM1 is more reliable

2. **Ribbon cable orientation:**
   - Blue side faces toward USB/Ethernet ports
   - Silver contacts face the PCB board
   - Make sure cable is fully inserted before locking the connector

## Software Configuration

### 1. Edit config.txt

```bash
sudo nano /boot/firmware/config.txt
```

In the `[all]` section at the bottom, add:

```ini
[all]
camera_auto_detect=0
dtoverlay=imx708,cam1
```

**Important:** Use `cam1` not `cam0`!

### 2. Reboot

```bash
sudo reboot
```

### 3. Verify Detection

```bash
# Should list the IMX708 camera
rpicam-hello --list-cameras

# Quick test photo
rpicam-still -o test.jpg -t 2000

# Check dmesg (should NOT see error -5)
sudo dmesg | grep -i imx708
```

**Expected output:**
```
0 : imx708 [4608x2592] (/axi/pcie@1000120000/rp1/i2c@80000/imx708@1a)
```

### 4. Test Python

```bash
cd ~/Desktop/camera_server
python3 camera_stream.py
```

Access stream at: `http://<pi-ip>:5000`

## Troubleshooting

### "No cameras available"
- Check physical connection (cable fully inserted and locked)
- Verify you're using **CAM1 port**
- Confirm `dtoverlay=imx708,cam1` in config.txt
- Reboot after config changes

### "Error -5" or "probe failed"
- Wrong CSI port (try the other port)
- Ribbon cable backwards (flip at camera end)
- Damaged cable (try a new one)
- If using CAM0 and getting error -5, **switch to CAM1**

### Camera was working, now isn't
- Reseat ribbon cable at both ends
- Check dmesg: `sudo dmesg | grep -i imx708`
- Verify config.txt hasn't changed

## Quick Diagnostic Commands

```bash
# List cameras (use rpicam not libcamera on newer systems)
rpicam-hello --list-cameras

# Check config
grep -E "camera|imx708" /boot/firmware/config.txt

# Check kernel messages
sudo dmesg | grep -i imx708

# Test Python detection
python3 -c "from picamera2 import Picamera2; print('Cameras:', len(Picamera2.global_camera_info()))"
```

## Working Config Summary

```ini
# /boot/firmware/config.txt
[all]
camera_auto_detect=0
dtoverlay=imx708,cam1  # Use cam1, not cam0!
```

## Notes

- Pi 5 uses different I2C buses than Pi 4/3
- CAM0 = near USB-C power port (may be unreliable)
- CAM1 = near GPIO header (recommended)
- Commands changed from `libcamera-*` to `rpicam-*` on newer OS versions
- Always reboot after changing config.txt
