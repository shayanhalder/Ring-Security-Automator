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

ARM_DELAY = 10
arm_time = float('inf')

security_transitioning = False
security_transition_lock = threading.Lock()
spinner_angle = 0.0

STATUS_DISPLAY = {
    SecurityStatus.AWAY: "Armed away",
    SecurityStatus.DISARMED: "Disarmed",
    SecurityStatus.HOME: "Armed home",
    SecurityStatus.UNKNOWN: "Unknown",
}
COLOR_DISARMED = (255, 120, 0)   # blue on stream (drawn on RGB buffer, encoded as BGR)
COLOR_ARMED = (0, 0, 255)        # red on stream

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
        initial_home_people = sys.argv[idx + 1].split(" ")
    except IndexError:
        initial_home_people = []

    print(f"Names: {initial_home_people}")
    for name in initial_home_people:
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

def request_security_change(action, on_success=None):
    global security_transitioning

    def run():
        global security_transitioning
        try:
            success = action()
            if success:
                if on_success:
                    on_success()
            else:
                print("[ERROR] Security state change failed")
        finally:
            with security_transition_lock:
                security_transitioning = False

    with security_transition_lock:
        if security_transitioning:
            return False
        security_transitioning = True

    threading.Thread(target=run, daemon=True).start()
    return True

def draw_fuzzy_border(frame, color, thickness=14, blur_size=31):
    h, w = frame.shape[:2]
    border = np.zeros_like(frame)
    cv2.rectangle(border, (0, 0), (w - 1, h - 1), color, thickness)
    soft = cv2.GaussianBlur(border, (blur_size | 1, blur_size | 1), 0)
    cv2.addWeighted(frame, 1.0, soft, 0.65, 0, frame)

def draw_loading_spinner(frame, cx, cy, radius, angle_deg, color, thickness=2):
    cv2.ellipse(
        frame, (cx, cy), (radius, radius), angle_deg, 0, 270, color, thickness, cv2.LINE_AA
    )

def draw_security_overlay(display):
    global spinner_angle

    h, w = display.shape[:2]
    status = security_controller.get_security_status()
    is_disarmed = status == SecurityStatus.DISARMED
    color = COLOR_DISARMED if is_disarmed else COLOR_ARMED

    draw_fuzzy_border(display, color)

    status_text = STATUS_DISPLAY.get(status, "Unknown")
    label = f"Status: {status_text}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.7
    thickness = 2
    margin = 12
    (text_w, text_h), _ = cv2.getTextSize(label, font, scale, thickness)

    with security_transition_lock:
        transitioning = security_transitioning

    if transitioning:
        spinner_angle = (spinner_angle + 12) % 360
        spinner_radius = 10
        spinner_cx = w - margin - spinner_radius
        spinner_cy = margin + spinner_radius
        draw_loading_spinner(display, spinner_cx, spinner_cy, spinner_radius, spinner_angle, color)
        text_x = spinner_cx - spinner_radius - margin - text_w
        text_y = margin + text_h
    else:
        text_x = w - margin - text_w
        text_y = margin + text_h

    cv2.putText(display, label, (text_x, text_y), font, scale, color, thickness, cv2.LINE_AA)

def finalize_display(display):
    draw_security_overlay(display)
    update_stream_frame(display)

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

    if any(authorized_member_state.values()) and security_controller.get_security_status() == SecurityStatus.AWAY: # if no one is home when we arrive, disarm security
        print("[ALERT]: Disarming security")
        request_security_change(security_controller.disarm_security)

    return "ok", 200


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

    if not any(authorized_member_state.values()): # if no one is home, arm security
        global arm_time
        arm_time = time.time() + ARM_DELAY

    return "ok", 200
    
def start_stream_server():
    lan_ip = get_lan_ip()
    print(f"Live stream available at http://{lan_ip}:{STREAM_PORT}")
    app.run(host='0.0.0.0', port=STREAM_PORT, debug=False, threaded=True, use_reloader=False)


def inference_pipeline(frame):
    # YOLO tracking to detect people and their bounding boxes
    results = yolo.track(frame, tracker="bytetrack.yaml", persist=True, classes=[0], verbose=False)
    detected_people = results[0]
    
    boxes = detected_people.boxes
    detections = []
    face_boxes = []
    display = frame.copy()
    
    if boxes is None or boxes.id is None:
        finalize_display(display)
        return

    # if boxes is not None and boxes.id is not None:
    box_ids = boxes.id.int().tolist()
    
    # process each detected person
    for box, track_id in zip(boxes.xyxy, box_ids):
        x1, y1, x2, y2 = map(int, box)
        
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
            xpad = int(0.55 * w_box)
            ypad = int(0.55 * h_box)
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
            if match_found and security_controller.get_security_status() == SecurityStatus.AWAY:
                print("[ALERT]: Disarming security")

                def on_disarm_success():
                    print("[INFO] Security disarmed")
                    if label in AuthorizedMembers:
                        authorized_member_state[AuthorizedMembers[label]] = True

                request_security_change(security_controller.disarm_security, on_success=on_disarm_success)
    
    for fx1, fy1, fx2, fy2, label in face_boxes:
        cv2.rectangle(display, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
        cv2.putText(display, label, (fx1, max(fy1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


    finalize_display(display)


def main():
    """
    Request and process a frame sent from the Raspberry Pi.
    Expects JSON with:
    - 'frame': base64-encoded image
    - 'timestamp': frame timestamp
    """
    global people_in_house, socket_delay_counter, arm_time
    
    if time.time() >= arm_time:
        print("[ALERT]: Arming security")
        request_security_change(security_controller.arm_security_away)
        arm_time = float('inf')

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
