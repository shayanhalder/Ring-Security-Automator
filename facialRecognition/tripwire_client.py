import cv2
from picamera2 import Picamera2
import numpy as np
import time
import sys
import requests
import base64

# Configuration
SERVER_URL = "http://192.168.1.100:5000"  # Change to your server's IP address
PROCESS_ENDPOINT = f"{SERVER_URL}/process_frame"
STATUS_ENDPOINT = f"{SERVER_URL}/status"

# Camera setup
cap = Picamera2()
frame_w, frame_h = 640, 360
camera_config = cap.create_preview_configuration(
    main={"size": (frame_w, frame_h), "format": "RGB888"}
)
cap.configure(camera_config)
cap.start()

print("cli args: ", sys.argv)
debug_mode = True if len(sys.argv) >= 2 and sys.argv[1] == "-d" else False
print("Debug mode:", debug_mode)

frames = 0
t0 = time.perf_counter()
last_status_check = time.time()

print(f"Raspberry Pi client started. Connecting to server at {SERVER_URL}")

# Test server connection
try:
    response = requests.get(STATUS_ENDPOINT, timeout=2)
    if response.status_code == 200:
        print("Successfully connected to server")
        print(f"Server status: {response.json()}")
    else:
        print(f"Warning: Server returned status code {response.status_code}")
except Exception as e:
    print(f"Warning: Could not connect to server: {e}")
    print("Make sure the server is running and the SERVER_URL is correct")

while True:
    frame = cap.capture_array()
    if frame is None:
        print("No frame captured")
        continue
    
    # Convert RGB to BGR for OpenCV encoding
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    
    # Encode frame to JPEG for transmission
    _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    frame_b64 = base64.b64encode(buffer).decode('utf-8')
    
    # Send frame to server
    try:
        payload = {
            'frame': frame_b64,
            'timestamp': time.time()
        }
        
        response = requests.post(PROCESS_ENDPOINT, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            
            if debug_mode:
                # Display info from server
                print(f"Detections: {len(result['detections'])}")
                print(f"People in house: {result['people_in_house']}")
                print(f"Security status: {result['security_status']}")
                
                # Draw bounding boxes on frame
                for det in result['detections']:
                    x1, y1, x2, y2 = det['bbox']
                    track_id = det['track_id']
                    cv2.rectangle(frame_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame_bgr, f"ID: {track_id}", (x1, y1 - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Display face recognition results
                for face_result in result.get('face_recognition', []):
                    label = face_result['label']
                    similarity = face_result['similarity']
                    track_id = face_result['track_id']
                    print(f"Track {track_id}: {label} (similarity: {similarity:.2f})")
                
                cv2.imshow("Frame", frame_bgr)
        else:
            print(f"Server error: {response.status_code}")
            if debug_mode:
                print(response.text)
    
    except requests.exceptions.Timeout:
        print("Request timeout - server may be overloaded")
    except requests.exceptions.ConnectionError:
        print("Connection error - server may be down")
    except Exception as e:
        print(f"Error sending frame: {e}")
    
    # Periodically check server status
    if time.time() - last_status_check > 10:
        try:
            response = requests.get(STATUS_ENDPOINT, timeout=1)
            if response.status_code == 200:
                status = response.json()
                print(f"Server status - People: {status['people_in_house']}, Security: {status['security_status']}")
            last_status_check = time.time()
        except:
            pass
    
    if debug_mode and cv2.waitKey(1) == 27:  # ESC to quit
        print("ESC pressed, shutting down...")
        break
    
    frames += 1
    if frames % 20 == 0:
        fps = frames / (time.perf_counter() - t0)
        frames = 0
        t0 = time.perf_counter()
        print(f"Client FPS: {fps:.2f}")

# Cleanup
cap.stop()
if debug_mode:
    cv2.destroyAllWindows()
print("Client shutdown complete")
