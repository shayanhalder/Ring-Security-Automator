import cv2
import picamera2
from picamera2 import Picamera2
import numpy as np
import time
import security_api
import sys
import time
sys.path = [p for p in sys.path if 'dist-packages' not in p]

from setup import setup_yunet, setup_buffalo, setup_encodings, setup_camera
from state_helpers import is_home, is_away, handle_admin_exits, arm_security_condition, disarm_security_condition
from insightface.app import FaceAnalysis
from enum import Enum
from setup import SecurityStatus

yunet = setup_yunet()
buffalo = setup_buffalo()
embeddings, names = setup_encodings()
#cap = setup_camera()
cap = Picamera2()
# camera_config = picamera2.create_still_configuration(main={"size": (640, 480)}, lores={"size": (640, 480)}, display="lores", raw={"size": (640, 480)}, controls={"FrameRate": 30}, buffer_count=4, format="RGB888")
camera_config = cap.create_preview_configuration(
    # main={"size": (1280, 720), "format": "RGB888"}
    main={"size": (640, 360), "format": "RGB888"}
)
cap.configure(camera_config)
cap.start()


# frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
# frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
# frame_w, frame_h = 1280, 720
frame_w, frame_h = 640, 360

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

frames = 0
t0 = time.perf_counter()


while True:
    frame = cap.capture_array()
    if frame is None:
        print("No frame captured")
        continue

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
        
        if face_crop.size == 0:
            continue
        # Get buffalo embedding
        results = buffalo.get(face_crop)
        if len(results) == 0:
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
        print(label, " detected")
   #     cv2.rectangle(frame, (x, y), (x + w_box, y + h_box), color, 2)
  #      cv2.putText(frame, f"{label} ({similarity:.2f})", (x, y - 10),
   #                 cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

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
    # if arm_security_condition(admin_states, security_status, RIGHT_THRESHOLD, LEFT_THRESHOLD):
    #     security_api.arm_security_away()
    # elif disarm_security_condition(admin_states, security_status, RIGHT_THRESHOLD, LEFT_THRESHOLD):
    #     security_api.disarm_security()
    frames += 1
    if frames % 100 == 0:
        fps = frames / (time.perf_counter() - t0)
        print("FPS: ", fps)
        
    #cv2.imshow("Frame", frame)
    #if cv2.waitKey(1) == 27:  # ESC to quit
     #   break
cap.stop()
#cap.release()
cv2.destroyAllWindows()
