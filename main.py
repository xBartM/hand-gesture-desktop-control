import cv2
import time
from queue import Queue

# Project-specific imports
from camera import scrcpy_manager
from config import scrcpy_presets
from vision import hand_tracker
from vision import drawing
from vision.hand_tracker import HandLandmarkerResult, MpImage, MpImageFormat # For type hints and MediaPipe image object

# --- Configuration ---
V4L2_DEVICE = "/dev/video0"
SCRCPY_MAX_SIZE = 240
# IMPORTANT: Update this path to your actual model file location
MODEL_ASSET_PATH = '{your_path_to}/hand_landmarker.task'
SCRCPY_CONFIG_PRESET_NAME = "Xperia Z2 Tablet - Open Camera" # or "Xiaomi Mi 9t - Open Camera" or custom

# --- Global Variables for MediaPipe Callback and Display ---
# This queue will store annotated frames produced by the MediaPipe callback
annotated_frame_buffer = Queue()

# --- MediaPipe Result Callback ---
def mediapipe_result_callback(result: HandLandmarkerResult, output_image: MpImage, timestamp_ms: int):
    """
    Callback function for MediaPipe HandLandmarker.
    Processes results, annotates images, and puts them in a queue for display.
    """
    # print(f'Hand landmarker result at {timestamp_ms}ms: {result}') # For debugging

    # Check if any hand landmarks were detected
    if result.hand_landmarks:
        # The output_image is the one provided by MediaPipe, containing the frame data
        # Convert mp.Image to NumPy array
        rgb_image = output_image.numpy_view()

        # Draw landmarks on the image
        annotated_image = drawing.draw_landmarks_on_image(rgb_image, result)
        
        # Convert annotated image from RGB to BGR for OpenCV display
        bgr_annotated_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        
        # Put the annotated image into the queue
        annotated_frame_buffer.put(bgr_annotated_image)
    # else:
        # Optionally handle cases where no hands are detected
        # print(f"No hands detected at {timestamp_ms}ms")


def main():
    scrcpy_process = None
    cam = None

    try:
        # --- Prepare scrcpy Camera Feed ---
        print(f"Requesting scrcpy config preset: {SCRCPY_CONFIG_PRESET_NAME}")
        try:
            scrcpy_custom_args = scrcpy_presets.get_scrcpy_preset(SCRCPY_CONFIG_PRESET_NAME)
            print(f"Using scrcpy arguments: {scrcpy_custom_args}")
        except ValueError as e:
            print(f"Error getting scrcpy preset: {e}. Using default scrcpy settings.")
            scrcpy_custom_args = {}
        
        scrcpy_process = scrcpy_manager.start_scrcpy_feed(
            v4l2_device=V4L2_DEVICE,
            max_size=SCRCPY_MAX_SIZE,
            video_playback=False, # Set to True if you want to see scrcpy's own window
            **scrcpy_custom_args
        )
        if scrcpy_process is None:
            print("Failed to start scrcpy. Exiting.")
            return
        
        # Allow some time for scrcpy to initialize the v4l2 device
        print("Waiting for scrcpy and v4l2 device to initialize...")
        time.sleep(3) # Adjust as needed

        # --- Connect to the v4l2 Camera ---
        cam = cv2.VideoCapture(V4L2_DEVICE)
        if not cam.isOpened():
            print(f"Error: Cannot open V4L2 device: {V4L2_DEVICE}")
            print("Make sure scrcpy is running and the v4l2loopback device is correctly set up.")
            return

        # Set camera properties (optional, scrcpy might enforce its own settings)
        # cam.set(cv2.CAP_PROP_FRAME_WIDTH, SCRCPY_MAX_SIZE)
        # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, SCRCPY_MAX_SIZE)
        # Check actual resolution
        width = cam.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cam.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Camera {V4L2_DEVICE} opened with resolution: {int(width)}x{int(height)}")
        if width == 0 or height == 0:
            print("Error: Camera resolution is 0x0. Check scrcpy and v4l2loopback device.")
            return


        # --- Prepare MediaPipe Hand Landmarker ---
        # The 'with' statement ensures the landmarker is closed properly
        with hand_tracker.create_hand_landmarker(MODEL_ASSET_PATH, mediapipe_result_callback) as landmarker:
            print("MediaPipe HandLandmarker initialized.")
            
            timestamp_ns0 = time.time_ns() # Base timestamp for relative calculations

            # --- Main Loop ---
            while True:
                cam_status, frame = cam.read()
                if not cam_status:
                    print("Error: Could not read frame from camera. scrcpy might have stopped.")
                    if scrcpy_process and scrcpy_process.poll() is not None:
                        print(f"scrcpy process exited with code: {scrcpy_process.returncode}")
                    break
                
                # Calculate timestamp for MediaPipe (in milliseconds)
                current_time_ns = time.time_ns()
                frame_timestamp_ms = int((current_time_ns - timestamp_ns0) / 1_000_000)

                # Display the original frame
                cv2.imshow('Original Camera Feed', frame)

                # Display the annotated frame if available
                if not annotated_frame_buffer.empty():
                    annotated_frame = annotated_frame_buffer.get_nowait() # Use get_nowait to avoid blocking
                    cv2.imshow('Annotated Hand Landmarks', annotated_frame)

                # Process for keyboard input (e.g., 'q' to quit)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("Quit key pressed. Exiting loop.")
                    break

                # Convert frame from BGR (OpenCV default) to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Create MediaPipe Image object
                mp_image = MpImage(image_format=MpImageFormat.SRGB, data=rgb_frame)
                
                # Perform asynchronous hand detection
                landmarker.detect_async(mp_image, frame_timestamp_ms)

    except FileNotFoundError:
        print(f"Error: Model file not found at {MODEL_ASSET_PATH}. Please check the path.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user (Ctrl+C).")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Cleaning up resources...")
        if cam:
            cam.release()
            print("Camera released.")
        if scrcpy_process:
            scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        cv2.destroyAllWindows()
        print("OpenCV windows destroyed.")
        print("Cleanup complete. Exiting.")

if __name__ == '__main__':
    main()