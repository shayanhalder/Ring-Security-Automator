from flask import Flask, request, jsonify
import cv2
import numpy as np
import zmq
import time
from setup import setup_yolo, setup_yunet, setup_buffalo, setup_encodings, TrackerInfo, SecurityStatus
from security_api import disarm_security, arm_security_away, arm_security_home
from collections import defaultdict

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

tracker_ids = defaultdict(TrackerInfo)
people_in_house = 0
security_status = SecurityStatus.DISARMED
frame_w, frame_h = 640, 360
TRIPWIRE_Y = 0.6 * frame_h

def handle_tripwire_events(track_id, x, y):
    """Handle entry/exit detection based on tripwire crossing"""
    global people_in_house, security_status
    
    has_exited = y < TRIPWIRE_Y

    if not tracker_ids[track_id].exited and has_exited:
        people_in_house -= 1
        print(f"Person exited. People in house: {people_in_house}")
    elif tracker_ids[track_id].exited and not has_exited:
        people_in_house += 1
        print(f"Person entered. People in house: {people_in_house}")

    tracker_ids[track_id].last_bottom_y = y
    tracker_ids[track_id].last_left_x = x
    tracker_ids[track_id].exited = has_exited


def main():
    """
    Request and process a frame sent from the Raspberry Pi.
    Expects JSON with:
    - 'frame': base64-encoded image
    - 'timestamp': frame timestamp
    """
    global people_in_house, security_status
    
    try:
        socket.send(b"frame")  # request latest frame
        jpeg_bytes = socket.recv()  
        frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        if frame is None:
            return jsonify({'error': 'Failed to decode frame'}), 400

        # YOLO tracking to detect people and their bounding boxes
        results = yolo.track(frame, tracker="bytetrack.yaml", persist=True, classes=[0], verbose=False)
        detected_people = results[0]
        
        boxes = detected_people.boxes
        detections = []
        face_recognition_results = []
        face_boxes = []
        
        if boxes is None or boxes.id is None:
            print("No people detected")
            # Arm security if no one is home
            if people_in_house == 0 and security_status == SecurityStatus.DISARMED:
                print("Server: Arming security - house empty")
                # success = arm_security_away()
                success = True
                if success:
                    security_status = SecurityStatus.ARMED_AWAY
        else:
            box_ids = boxes.id.int().tolist()
            
            # Process each detected person
            for box, track_id in zip(boxes.xyxy, box_ids):
                x1, y1, x2, y2 = map(int, box)
                
                # Handle tripwire events
                handle_tripwire_events(track_id, x1, y2)
                
                detections.append({
                    'track_id': int(track_id),
                    'bbox': [int(x1), int(y1), int(x2), int(y2)]
                })
                
                # Crop to the person
                person_crop = frame[y1:y2, x1:x2]
                
                if person_crop.size == 0:
                    continue
                
                # Detect face in person crop with yunet
                face_detector.setInputSize((person_crop.shape[1], person_crop.shape[0]))
                _, faces = face_detector.detect(person_crop)
                
                if faces is None:
                    continue
                
                # Process each detected face
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
                    
                    print(f"Server: Identified {label} (similarity: {similarity:.2f})")
                    
                    face_recognition_results.append({
                        'track_id': int(track_id),
                        'label': label,
                        'similarity': similarity,
                        'match_found': match_found
                    })
                    
                    # Handle security disarming
                    if match_found and security_status == SecurityStatus.ARMED_AWAY:
                        print("Server: Disarming security - authorized person detected")
                        # success = disarm_security()
                        success = True
                        if success:
                            security_status = SecurityStatus.DISARMED
        
        display = frame.copy()
        for fx1, fy1, fx2, fy2, label in face_boxes:
            cv2.rectangle(display, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
            cv2.putText(display, label, (fx1, max(fy1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.imshow("Frame", display)
        cv2.waitKey(1)
        
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# @app.route('/status', methods=['GET'])
# def get_status():
#     """Get current system status"""
#     return jsonify({
#         'people_in_house': people_in_house,
#         'security_status': security_status.value,
#         'tracker_count': len(tracker_ids),
#         'trackers': {
#             str(tid): {
#                 'exited': info.exited,
#                 'last_bottom_y': info.last_bottom_y,
#                 'last_left_x': info.last_left_x
#             } for tid, info in tracker_ids.items()
#         }
#     })

# @app.route('/reset', methods=['POST'])
# def reset_state():
#     """Reset server state (useful for debugging)"""
#     global people_in_house, security_status, tracker_ids
    
#     people_in_house = 0
#     security_status = SecurityStatus.DISARMED
#     tracker_ids.clear()
    
#     return jsonify({
#         'success': True,
#         'message': 'State reset successfully'
#     })

if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    while True:
        main()
