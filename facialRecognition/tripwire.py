import cv2
from picamera2 import Picamera2
import numpy as np
import time
from setup import setup_yolo, setup_yunet, setup_buffalo, setup_encodings, setup_camera
from state_helpers import is_home, is_away, handle_admin_exits, arm_security_condition, disarm_security_condition
from security_api import disarm_security, arm_security_away, arm_security_home
from setup import SecurityStatus
from collections import defaultdict
import sys

yolo = setup_yolo()
face_detector = setup_yunet()
face_identifier = setup_buffalo()
embeddings, names = setup_encodings()
cap = Picamera2()
frame_w, frame_h = 640, 360
camera_config = cap.create_preview_configuration(
    main={"size": (frame_w, frame_h), "format": "RGB888"}
)
cap.configure(camera_config)
cap.start()

security_status = SecurityStatus.DISARMED

class TrackerInfo:
    exited = False
    last_bottom_y = float('-inf')
    last_left_x = float('-inf')

tracker_ids = defaultdict(TrackerInfo)
    # id: {
        # 'exited': boolean,
        # 'last_bottom_y': int
        # 'last_left_x': int
    # }

people_in_house = 0
TRIPWIRE_Y = 0.6 * frame_h
frames = 0
t0 = time.perf_counter()

debug_mode = True if len(sys.argv) >= 1 and sys.argv[0] == "-d" else False

def handle_tripwire_events(track_id, x, y):
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

while True:
    frame = cap.capture_array()
    if frame is None:
        print("No frame captured")
        continue

    results = yolo.track(frame, tracker="bytetrack.yaml", persist=True, classes=[0], verbose=False) # class 0 is 'person'
    detected_people = results[0] # first element of the list contains all detections for current frame

    boxes = detected_people.boxes
    if boxes is None or boxes.id is None:
        print("no people detected")
        # arm security if no one is home
        if people_in_house == 0 and security_status == SecurityStatus.DISARMED:
            success = True
            if success:
                security_status = SecurityStatus.ARMED_AWAY
        continue
    
    box_ids = boxes.id.int().tolist()
    
    # process each detected person and update their tracker info
    for box, track_id in zip(boxes.xyxy, box_ids):
        x1, y1, x2, y2 = map(int, box)
        
        handle_tripwire_events(track_id, x1, y2)
        
        # crop to the person
        person_crop = frame[y1:y2, x1:x2]
        
        cv2.imshow("person", person_crop) if debug_mode else None
        # detect face ONLY inside the person crop
        face_detector.setInputSize((person_crop.shape[1], person_crop.shape[0]))
        _, faces = face_detector.detect(person_crop)

        if faces is None:
            continue
        
        for det in faces: # face detected for current person
            x, y, w_box, h_box = det[:4].astype(int)
            cx = x + w_box / 2

            xpad = int(0.4 * w_box)
            ypad = int(0.4 * h_box)
            x1 = max(0, x - xpad)
            y1 = max(0, y - xpad)
            
            x2 = min(person_crop.shape[1], x + w_box + xpad)
            y2 = min(person_crop.shape[0], y + h_box + ypad)
            face_crop = person_crop[y1:y2, x1:x2]
            
            color = (0, 255, 0)
                        
            # get buffalo embedding
            results = face_identifier.get(face_crop)
            if len(results) == 0:
                continue
            
            emb = results[0].embedding
            # identify the face by comparing with trained embeddings
            sims = np.dot(embeddings, emb) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(emb))
            idx = np.argmax(sims)
            best_match = names[idx]
            similarity = sims[idx]
            
            print(f"Best match: {best_match}, Similarity: {similarity}")
            match_found = similarity > 0.4

            label = best_match if similarity > 0.4 else "Unknown"
            color = (0, 255, 0) if label != "Unknown" else (0, 0, 255)
            print(label, " detected")

            if match_found and security_status == SecurityStatus.ARMED_AWAY:
                # disarm security since authrorized person detected
                success = True
                if success:
                    security_status = SecurityStatus.DISARMED
                
            
            cv2.imshow("face", face_crop) if debug_mode else None
            cv2.putText(face_crop, f"{label} ({similarity:.2f})", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2) if debug_mode else None

            if label == "Unknown": 
                continue
    
    cv2.imshow("Frame", frame) if debug_mode else None
    if cv2.waitKey(1) == 27:  # ESC to quit
       break
    frames += 1
    if frames % 20 == 0:
        fps = frames / (time.perf_counter() - t0)
        t0 = time.perf_counter()
        print("FPS: ", fps)
        

        
cap.stop()
cap.release()
cv2.destroyAllWindows()
