# Server-Client Architecture for Ring Security Automator

This setup offloads the heavy model processing from the Raspberry Pi 5 to a home server laptop via LAN.

## Architecture

- **Raspberry Pi 5** (Client): Captures frames with camera and sends to server via HTTP POST
- **Home Server** (Server): Runs YOLO, YuNet, and Buffalo_l models, maintains state, processes frames

## Setup Instructions

### On the Home Server Laptop:

1. Install dependencies:
```bash
pip install flask opencv-python numpy ultralytics insightface
```

2. Make sure the models are available:
   - Copy `yolo11n_ncnn_model/` directory to the server
   - Copy `models/` directory (with YuNet ONNX files) to the server
   - Copy `face_encodings.npy` to the server
   - Copy `setup.py` and `security_api.py` to the server

3. Find your server's local IP address:
```bash
# On Linux/Mac:
hostname -I
# or
ifconfig

# On Windows:
ipconfig
```

4. Start the Flask server:
```bash
python server.py
```

The server will run on `http://0.0.0.0:5000` (accessible from any device on your LAN)

### On the Raspberry Pi 5:

1. Install client dependencies:
```bash
pip install opencv-python numpy picamera2 requests
```

2. Edit `tripwire_client.py` and change the `SERVER_URL` to your server's IP:
```python
SERVER_URL = "http://192.168.1.100:5000"  # Change to your actual server IP
```

3. Run the client:
```bash
# Normal mode (no visualization)
python tripwire_client.py

# Debug mode (shows bounding boxes and info)
python tripwire_client.py -d
```

## API Endpoints

### POST /process_frame
Processes a frame from the camera.

**Request:**
```json
{
  "frame": "base64_encoded_jpeg",
  "timestamp": 1234567890.123
}
```

**Response:**
```json
{
  "success": true,
  "timestamp": 1234567890.123,
  "detections": [
    {
      "track_id": 1,
      "bbox": [100, 50, 300, 400]
    }
  ],
  "face_recognition": [
    {
      "track_id": 1,
      "label": "John",
      "similarity": 0.87,
      "match_found": true
    }
  ],
  "people_in_house": 1,
  "security_status": "disarmed",
  "tracker_count": 1
}
```

### GET /status
Get current system status without processing a frame.

**Response:**
```json
{
  "people_in_house": 1,
  "security_status": "disarmed",
  "tracker_count": 1,
  "trackers": {
    "1": {
      "exited": false,
      "last_bottom_y": 300,
      "last_left_x": 150
    }
  }
}
```

### POST /reset
Reset server state (useful for debugging).

**Response:**
```json
{
  "success": true,
  "message": "State reset successfully"
}
```

## Performance Considerations

1. **Network Latency**: Processing over LAN adds ~10-50ms latency depending on network quality
2. **Bandwidth**: Each 640x360 JPEG frame is ~20-40KB, so at 10 FPS = ~400KB/s
3. **Server CPU**: Ensure server has decent CPU/GPU for model inference
4. **Frame Rate**: Client can capture faster than server processes - consider throttling if needed

## Troubleshooting

1. **Connection errors**: 
   - Check firewall settings on server
   - Ensure both devices are on same network
   - Verify SERVER_URL is correct

2. **Slow processing**:
   - Reduce frame resolution in client
   - Lower JPEG quality (line 36 in tripwire_client.py)
   - Add frame skipping logic

3. **Out of sync state**:
   - Use POST /reset endpoint to clear server state
   - Restart both client and server

## Security Notes

- This setup uses unencrypted HTTP - only use on trusted LAN
- For production, consider adding authentication tokens
- Consider using HTTPS for encrypted communication
