# Raspberry Pi 5 - use ZeroMQ to send jpeg frames to MAC via LAN
import zmq
import cv2
from picamera2 import Picamera2
from constants import FRAME_WIDTH, FRAME_HEIGHT

# Camera Module 3 Wide (IMX708): 4608x2592 still, 2304x1296 max video


camera = Picamera2()
config = camera.create_video_configuration(
    main={"size": (FRAME_WIDTH, FRAME_HEIGHT), "format": "RGB888"}
)
camera.configure(config)
camera.start()
print(f"Camera streaming at {FRAME_WIDTH}x{FRAME_HEIGHT}")

context = zmq.Context()
socket = context.socket(zmq.REP)  # reply socket
socket.bind("tcp://*:5555")

while True:
    socket.recv()  # wait for macbooks request 
    
    frame = camera.capture_array()
    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    _, jpeg = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
    socket.send(jpeg.tobytes())  # send latest frame immediately