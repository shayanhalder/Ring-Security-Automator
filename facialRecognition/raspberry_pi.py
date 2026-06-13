# Raspberry Pi 5 - use ZeroMQ to send jpeg frames to MAC via LAN
import zmq
import cv2
from picamera2 import Picamera2

camera = Picamera2()
camera.start()

context = zmq.Context()
socket = context.socket(zmq.REP)  # reply socket
socket.bind("tcp://*:5555")

while True:
    socket.recv()  # wait for macbooks request 
    
    frame = camera.capture_array()
    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    socket.send(jpeg.tobytes())  # send latest frame immediately