import cv2

# it needs to get pulled out even further
v4l2 = '/dev/video0'

cam = cv2.VideoCapture(v4l2)
if not cam.isOpened():
    print("cam bad")
    exit()

cam.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

try:
    while True:
        ret, frame = cam.read()
        if not ret:
            print("Error: Could not read frame.")
            break
        cv2.imshow('Frame', frame)
except KeyboardInterrupt:
    print("interrupted")
finally:
    cam.release()
    cv2.destroyAllWindows()
