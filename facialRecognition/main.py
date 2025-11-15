import cv2
import numpy as np
import time
import security_api
from setup import setup_yunet, setup_buffalo, setup_encodings, setup_camera
from state_helpers import is_home, is_away, handle_admin_exits, arm_security_condition, disarm_security_condition
from insightface.app import FaceAnalysis
from enum import Enum
from setup import SecurityStatus

yunet = setup_yunet()
buffalo = setup_buffalo()
embeddings, names = setup_encodings()
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print("Could not open camera")
    exit(1)
    
print("Camera opened successfully")

frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

LEFT_THRESHOLD = frame_w * 0.4
RIGHT_THRESHOLD = frame_w * 0.6

security_status = SecurityStatus.DISARMED
# try:
#     security_status: SecurityStatus = SecurityStatus(security_api.get_security_status())
# except ValueError:
#     print("Invalid security status")
#     exit(1)

admin_states = {
    'shayan': {
        'last_x': 0,
        'currently_in_frame': True,
        'logged_exit': False
    },
    'sohini': {
        'last_x': 2000,
        'currently_in_frame': False,
        'logged_exit': True
    },
    'sudeshna': {
        'last_x': 2000,
        'currently_in_frame': False,
        'logged_exit': True
    },
    'pallab': {
        'last_x': 2000,
        'currently_in_frame': False,
        'logged_exit': True
    },
}

while True:
    ret, frame = cap.read() # ret is True if frame is read successfully, False otherwise
    if not ret:
        break
    # print('frame: ')
    # print(frame)
    h, w = frame.shape[:2]
    yunet.setInputSize((w, h))
    _, faces = yunet.detect(frame)

    if faces is None:
        faces = []
    
    identified_faces = []
    
    for det in faces:
        x, y, w_box, h_box = det[:4].astype(int)
        cx = x + w_box / 2

        pad = int(0.3 * w_box)
        x1 = max(0, x - pad)
        y1 = max(0, y - pad)
        
        x2 = min(frame.shape[1], x + w_box + pad)
        y2 = min(frame.shape[0], y + h_box + pad)
        
        face_crop = frame[y1:y2, x1:x2]
        # face_crop = frame[y:y + h_box, x:x + w_box]
        # print(f"Face crop size: {face_crop.size}")
        if face_crop.size == 0:
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) == 27:  # ESC to quit
                break
            continue
        # Get buffalo embedding
        results = buffalo.get(face_crop)
        if len(results) == 0:
            cv2.imshow("Frame", frame)
            if cv2.waitKey(1) == 27:  # ESC to quit
                break
            continue

        emb = results[0].embedding
        # Compare with known embeddings
        sims = np.dot(embeddings, emb) / (np.linalg.norm(embeddings, axis=1) * np.linalg.norm(emb))
        idx = np.argmax(sims)
        best_match = names[idx]
        similarity = sims[idx]
        
        # print(f"Best match: {best_match}, Similarity: {similarity}")

        label = best_match if similarity > 0.4 else "Unknown"
        identified_faces.append(label)
        color = (0, 255, 0) if label != "Unknown" else (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), color, 2)
        cv2.putText(frame, f"{label} ({similarity:.2f})", (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if label == "Unknown": 
            continue
            
        admin_states[label]['last_x'] = cx
        admin_states[label]['currently_in_frame'] = True
        if admin_states[label]['logged_exit']:
            admin_states[label]['logged_exit'] = False
        
    for admin in admin_states.keys():
        if admin not in identified_faces:
            admin_states[admin]['currently_in_frame'] = False
            
    handle_admin_exits(admin_states, LEFT_THRESHOLD, RIGHT_THRESHOLD)
    if arm_security_condition(admin_states, security_status, RIGHT_THRESHOLD, LEFT_THRESHOLD):
        security_api.arm_security_away()
    elif disarm_security_condition(admin_states, security_status, RIGHT_THRESHOLD, LEFT_THRESHOLD):
        security_api.disarm_security()
        
    cv2.imshow("Frame", frame)
    if cv2.waitKey(1) == 27:  # ESC to quit
        break

cap.release()
cv2.destroyAllWindows()
