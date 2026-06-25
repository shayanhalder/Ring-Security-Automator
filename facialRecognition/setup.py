import cv2
import numpy as np
from insightface.app import FaceAnalysis
from enum import Enum
from ultralytics import YOLO

class TrackerInfo:
    def __init__(self):
        self.exited = False
        self.last_bottom_y = float('-inf')
        self.last_left_x = float('-inf')

class AuthorizedMembers(Enum):
    SHAYAN = "SHAYAN"
    SOHINI = "SOHINI"
    SUDESHNA = "SUDESHNA"
    PALLAB = "PALLAB"

class SecurityStatus(Enum):
    ARMED_AWAY = "armed_away"
    ARMED_HOME = "armed_home"
    DISARMED = "disarmed"

def setup_yolo():
    optimized_model = YOLO("yolo11n_ncnn_model")
    return optimized_model

def setup_yunet():
    yunet = cv2.FaceDetectorYN.create( # detects faces in the frame
        model="models/face_detection_yunet_2023mar_int8bq.onnx",
        config="",
        input_size=(200, 200),
        score_threshold=0.6,
        nms_threshold=0.3,
        top_k=500,
        backend_id=cv2.dnn.DNN_BACKEND_OPENCV,
        target_id=cv2.dnn.DNN_TARGET_CPU
    )
    
    return yunet
    
def setup_buffalo():
    buffalo = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider']) # identifies faces in the frame
    buffalo.prepare(ctx_id=0, det_size=(640, 640))
    
    return buffalo
    
def setup_encodings():
    encodings = np.load("face_encodings.npy", allow_pickle=True).item()
    names = list(encodings.keys())
    embeddings = np.array(list(encodings.values()))
    
    return embeddings, names
    
def setup_camera():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    if not cap.isOpened():
        print("Could not open camera")
        exit(1)
        
    print("Camera opened successfully")
    
    return cap
    
