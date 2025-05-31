import cv2
import mediapipe as mp
import os, signal
import time
import utils as hgu

# it needs to get pulled out even further
v4l2 = "/dev/video0"
max_size = 240
timestamp_ns0 = time.time_ns()
frame_timestamp_ns = time.time_ns()

# prepare camera
cam_pid = hgu.start_camera( v4l2_device=v4l2, 
                            max_size=max_size, 
                            **hgu.get_config("Xperia Z2 Tablet - Open Camera"))


# connect to the camera
cam = cv2.VideoCapture(v4l2)
if not cam.isOpened():
    print("cam bad")
    exit()
cam.set(cv2.CAP_PROP_FRAME_WIDTH, max_size)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, max_size)


# prepare the hand landmarker task
BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
VisionRunningMode = mp.tasks.vision.RunningMode

# Create a hand landmarker instance with the live stream mode:
def print_result(result: HandLandmarkerResult, output_image: mp.Image, timestamp_ms: int):
    # print('hand landmarker result: {}'.format(result))
    print(timestamp_ms)
    for res in result.hand_landmarks:
        for nlm in res:
            print(nlm)

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path='{your_path_to}/hand_landmarker.task'),
    running_mode=VisionRunningMode.LIVE_STREAM,
    result_callback=print_result)
with HandLandmarker.create_from_options(options) as landmarker:
# The landmarker is initialized. Use it here.

    try:
        while True:
            cam_status, frame = cam.read()
            if not cam_status:
                print("Error: Could not read frame.")
                break
            frame_timestamp_ns = time.time_ns() - timestamp_ns0
            # cv2.imshow('frame', frame)

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            landmarker.detect_async(mp_image, int(frame_timestamp_ns/1000))

            if cv2.waitKey(1) == ord('q'):
                break
    except KeyboardInterrupt:
        print("interrupted")
    finally:
        os.kill(cam_pid, signal.SIGTERM)
        cam.release()
        cv2.destroyAllWindows()

