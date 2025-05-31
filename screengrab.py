# import cv2
import os, signal
import utils as hgu

# it needs to get pulled out even further
# v4l2 = '/dev/video0'

# prepare camera config 
cam_cfg = hgu.get_config("Xperia Z2 Tablet - Open Camera")

ret = hgu.start_camera(**cam_cfg)
print (ret)
if input() == 'q':
    os.kill(ret, signal.SIGSTOP)


# cam = cv2.VideoCapture(v4l2)
# if not cam.isOpened():
#     print("cam bad")
#     exit()

# cam.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
# cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# try:
#     while True:
#         ret, frame = cam.read()
#         if not ret:
#             print("Error: Could not read frame.")
#             break
#         cv2.imshow('Frame', frame)
# except KeyboardInterrupt:
#     print("interrupted")
# finally:
#     cam.release()
#     cv2.destroyAllWindows()
