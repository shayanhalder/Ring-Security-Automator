import cv2
import numpy as np
import zmq
import time
import sys
import threading
import subprocess
import socket as stdlib_socket
from flask import Flask, Response, request
from setup import setup_yolo, setup_yunet, setup_buffalo, setup_encodings, TrackerInfo, SecurityStatus, AuthorizedMembers
from security_controller import SecurityController
from collections import defaultdict
from constants import TRIPWIRE_Y, FRAME_HEIGHT
from dotenv import load_dotenv
import os

load_dotenv()

NETWORK_ID = "192.168.68"
AUTHORIZED_IPS = [
    f"{NETWORK_ID}.{ip.strip()}"
    for ip in os.getenv("AUTHORIZED_IPS", "").split(",")
    if ip.strip()
]
STREAM_PORT = os.getenv("PORT")
if not STREAM_PORT:
    raise ValueError("PORT environment variable is not set")
STREAM_PORT = int(STREAM_PORT)
STREAM_MAX_WIDTH = 1152

latest_jpeg = None
frame_lock = threading.Lock()

app = Flask(__name__)

# initialize models
print("Loading computer vision models on server...")
yolo = setup_yolo()
face_detector = setup_yunet()
face_identifier = setup_buffalo()
embeddings, names = setup_encodings()
print("Models loaded successfully")

# initialize socket and zeromq
print("Initializing socket and zeromq...")
context = zmq.Context()
socket = context.socket(zmq.REQ)  # reply socket
socket.connect("tcp://raspberrypi.local:5555")

# server-side state

authorized_member_state = defaultdict(bool)

tracker_ids = defaultdict(TrackerInfo)
people_in_house = 0

if "-p" in sys.argv or "--people" in sys.argv:
    idx = sys.argv.index("-p") if "-p" in sys.argv else sys.argv.index("--people")
    try:
        names = sys.argv[idx + 1].split(" ")
    except IndexError:
        names = []
        
    print(f"Names: {names}")
    for name in names:
        if not name:
            continue

        name = name.upper()
        if name in AuthorizedMembers:
            authorized_member_state[AuthorizedMembers[name]] = True
        else:
            print(f"Warning: '{name}' is not an authorized member")

print(f"Authorized members: {authorized_member_state}")
test_mode = "-t" in sys.argv or "--test" in sys.argv # test mode True means we won't actually arm/disarm security
show_fps_mode = "-f" in sys.argv or "--fps" in sys.argv # show fps mode True means we will show the fps in the terminal
security_controller = SecurityController(test_mode=test_mode)

socket_delay_counter = 0

def get_lan_ip():
    s = stdlib_socket.socket(stdlib_socket.AF_INET, stdlib_socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "localhost"
    finally:
        s.close()

def update_stream_frame(frame):
    global latest_jpeg
    h, w = frame.shape[:2]
    if w > STREAM_MAX_WIDTH:
        scale = STREAM_MAX_WIDTH / w
        frame = cv2.resize(frame, (STREAM_MAX_WIDTH, int(h * scale)))
    ok, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if ok:
        with frame_lock:
            latest_jpeg = jpeg.tobytes()

def generate_mjpeg():
    while True:
        with frame_lock:
            frame = latest_jpeg
        if frame is None:
            time.sleep(0.05)
            continue
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )
        time.sleep(0.05)

@app.route('/')
def index():
    return (
        '<html><head><title>Face Recognition Stream</title></head>'
        '<body style="margin:0;background:#111;">'
        '<img src="/video_feed" style="width:100%;height:auto;">'
        '</body></html>'
    )

@app.route('/video_feed')
def video_feed():
    return Response(generate_mjpeg(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/arrived', methods=['POST'])
def arrived():
    name = request.json.get('name')
    device_id = request.json.get('device_id')
    if name not in AuthorizedMembers:
        return 'error: unauthorized member', 401
        
    if device_id != os.getenv(name.upper()):
        return 'error: unauthorized device', 401
    
    print(f"[{name}] Arrived")
    authorized_member_state[AuthorizedMembers[name]] = True
    return 200


@app.route('/left', methods=['POST'])
def left():
    name = request.json.get('name')
    device_id = request.json.get('device_id')
    if name not in AuthorizedMembers:
        return 'error: unauthorized member', 401
        
    if device_id != os.getenv(name.upper()):
        return 'error: unauthorized device', 401
    
    print(f"[{name}] Left")
    authorized_member_state[AuthorizedMembers[name]] = False
    return 200
    
def start_stream_server():
    lan_ip = get_lan_ip()
    print(f"Live stream available at http://{lan_ip}:{STREAM_PORT}")
    app.run(host='0.0.0.0', port=STREAM_PORT, debug=False, threaded=True, use_reloader=False)

def ping_ip(ip: str) -> bool:
    result = subprocess.run(
        ["ping", "-c", "1", "-W", "1", ip],
        capture_output=True,
    )
    return result.returncode == 0

def authorized_device_monitor():
    if not AUTHORIZED_IPS:
        print("[PING] No AUTHORIZED_IPS configured, skipping device monitor")
        return

    print(f"[PING] Monitoring authorized devices: {', '.join(AUTHORIZED_IPS)}")
    while True:
        any_online = any(ping_ip(ip) for ip in AUTHORIZED_IPS)

        if any_online:
            if security_controller.security_status != SecurityStatus.DISARMED:
                print("[ALERT] Disarming security")
                security_controller.disarm_security()
        elif security_controller.security_status == SecurityStatus.DISARMED:
            print("[Alert] Arming security")
            security_controller.arm_security_away()

        time.sleep(5)

def handle_tripwire_events(track_id, left_x, top_y, bottom_y):
    """Handle entry/exit detection based on virtual tripwire crossing"""
    global people_in_house, security_status
    
    # has_just_exited = y < TRIPWIRE_Y
    # print(f"Tracking ID: {track_id}, Y: {y}, FRAME_HEIGHT: {FRAME_HEIGHT}")
    # has_just_exited = y <= FRAME_HEIGHT
    has_just_exited = bottom_y <= TRIPWIRE_Y

    # initialize new track id info if this is the first time we've seen this track id
    if track_id not in tracker_ids:
        tracker_ids[track_id].last_bottom_y = bottom_y
        tracker_ids[track_id].last_left_x = left_x
        tracker_ids[track_id].exited = has_just_exited

        return

    if not tracker_ids[track_id].exited and has_just_exited:
        if people_in_house > 0:
            people_in_house -= 1
        print(f"[TRIPWIRE] PERSON EXITED. People in house: {people_in_house}")
    elif tracker_ids[track_id].exited and not has_just_exited:
        people_in_house += 1
        print(f"[TRIPWIRE] PERSON ENTERED. People in house: {people_in_house}")

    tracker_ids[track_id].last_bottom_y = bottom_y
    tracker_ids[track_id].last_left_x = left_x
    tracker_ids[track_id].exited = has_just_exited

def inference_pipeline(frame):
    # YOLO tracking to detect people and their bounding boxes
    results = yolo.track(frame, tracker="bytetrack.yaml", persist=True, classes=[0], verbose=False)
    detected_people = results[0]
    
    boxes = detected_people.boxes
    detections = []
    face_boxes = []
    
    if boxes is None or boxes.id is None:
        # arm security if no one is home
        if people_in_house == 0 and security_controller.get_security_status() == SecurityStatus.DISARMED:
            print("Server: Arming security - house empty")
            success = security_controller.arm_security_away()
    else:
        box_ids = boxes.id.int().tolist()
        
        # process each detected person
        for box, track_id in zip(boxes.xyxy, box_ids):
            x1, y1, x2, y2 = map(int, box)
            
            # handle virtual tripwire events
            handle_tripwire_events(track_id, x1, y1, y2)
            
            detections.append({
                'track_id': int(track_id),
                'bbox': [int(x1), int(y1), int(x2), int(y2)]
            })
            
            # crop to the person
            person_crop = frame[y1:y2, x1:x2]
            
            if person_crop.size == 0:
                continue
            
            # detect face in person crop with yunet
            face_detector.setInputSize((person_crop.shape[1], person_crop.shape[0]))
            _, faces = face_detector.detect(person_crop)
            
            if faces is None:
                continue
            
            # process each detected face
            for det in faces:
                x, y, w_box, h_box = det[:4].astype(int)
                fx1, fy1 = x1 + x, y1 + y
                fx2, fy2 = fx1 + w_box, fy1 + h_box
                
                # Add padding to face crop
                xpad = int(0.4 * w_box)
                ypad = int(0.4 * h_box)
                x1_face = max(0, x - xpad)
                y1_face = max(0, y - ypad)
                x2_face = min(person_crop.shape[1], x + w_box + xpad)
                y2_face = min(person_crop.shape[0], y + h_box + ypad)
                face_crop = person_crop[y1_face:y2_face, x1_face:x2_face]
                
                if face_crop.size == 0:
                    continue
                
                # Get Buffalo_l embedding
                face_results = face_identifier.get(face_crop)
                if len(face_results) == 0:
                    face_boxes.append((fx1, fy1, fx2, fy2, "Unknown"))
                    continue
                
                emb = face_results[0].embedding
                
                # Identify face by comparing with trained embeddings
                sims = np.dot(embeddings, emb) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(emb))
                idx = np.argmax(sims)
                best_match = names[idx]
                similarity = float(sims[idx])
                
                match_found = similarity > 0.4
                label = best_match if match_found else "Unknown"
                face_boxes.append((fx1, fy1, fx2, fy2, label))
                
                # print(f"Server: Identified {label} (similarity: {similarity:.2f})")
                
                # handle security disarming
                if match_found and security_controller.get_security_status() == SecurityStatus.ARMED_AWAY:
                    print("Server: Disarming security - authorized person detected")
                    success = security_controller.disarm_security()
    
    display = frame.copy()
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(display, f"Person {det['track_id']}", (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    for fx1, fy1, fx2, fy2, label in face_boxes:
        cv2.rectangle(display, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
        cv2.putText(display, label, (fx1, max(fy1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.line(display, (0, TRIPWIRE_Y), (display.shape[1], TRIPWIRE_Y), (0, 0, 255), 2)
    update_stream_frame(display)


def main():
    """
    Request and process a frame sent from the Raspberry Pi.
    Expects JSON with:
    - 'frame': base64-encoded image
    - 'timestamp': frame timestamp
    """
    global people_in_house, socket_delay_counter
    
    try:
        socket_delay_counter += 1
        socket_delay = time.perf_counter()
        socket.send(b"frame")  # request latest frame
        jpeg_bytes: bytes = socket.recv()
        socket_delay = time.perf_counter() - socket_delay
        print(f"Socket delay: {socket_delay:.2f} seconds") if socket_delay_counter % 100 == 0 else None

        frame: np.ndarray | None = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        frame: np.ndarray | None = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame is not None else None
   
        if frame is None:
            print("Failed to decode frame")
            return

        inference_pipeline(frame)
        
    except Exception as e:
        print(f"Server error: {e}")
        return


if __name__ == '__main__':
    threading.Thread(target=start_stream_server, daemon=True).start()
    threading.Thread(target=authorized_device_monitor, daemon=True).start()

    frames = 0
    t0 = time.perf_counter()

    while True:
        main()
        frames += 1

        elapsed = time.perf_counter() - t0
        if show_fps_mode and elapsed >= 10.0:
            fps = frames / elapsed
            print(f"Effective FPS: {fps:.2f}") if show_fps_mode else None
            frames = 0
            t0 = time.perf_counter()
