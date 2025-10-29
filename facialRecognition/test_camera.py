import cv2

cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
print("Opened:", cap.isOpened())

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

for i in range(10):
    ret, frame = cap.read()
    print(f"Frame {i}: ret={ret}, shape={None if not ret else frame.shape}")
    if ret:
        cv2.imshow("Frame", frame)
        cv2.waitKey(1)

cap.release()
cv2.destroyAllWindows()
