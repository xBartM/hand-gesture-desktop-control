import cv2
import time
from queue import Queue
import mediapipe as mp # Import mediapipe
from pynput.mouse import Controller as MouseController # For mouse control

# Project-specific imports
from camera import scrcpy_manager
from config import scrcpy_presets
from vision import hand_tracker
from vision import drawing
from vision.hand_tracker import HandLandmarkerResult, MpImage, MpImageFormat
from utils import system_utils # For getting screen resolution

# --- Configuration ---
V4L2_DEVICE = "/dev/video0"
SCRCPY_MAX_SIZE = 240
MODEL_ASSET_PATH = '{your_path_to}/hand_landmarker.task' # UPDATE THIS
SCRCPY_CONFIG_PRESET_NAME = "Xperia Z2 Tablet - Open Camera"

# --- Mouse Control Configuration ---
ENABLE_MOUSE_CONTROL = True  # Set to False to disable mouse control
MOUSE_CONTROL_LANDMARK = mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP # Landmark 9
SMOOTHING_FACTOR = 0.3  # Lower value = more smoothing (e.g., 0.1 to 0.5)

# --- Global Variables ---
annotated_frame_buffer = Queue()
mouse_controller = None
screen_width, screen_height = None, None
last_target_x, last_target_y = None, None
is_first_mouse_move = True


# --- MediaPipe Result Callback ---
def mediapipe_result_callback(result: HandLandmarkerResult, output_image: MpImage, timestamp_ms: int):
    """
    Callback function for MediaPipe HandLandmarker.
    Processes results, annotates images, and puts them in a queue for display.
    """
    global last_target_x, last_target_y, is_first_mouse_move, mouse_controller, screen_width, screen_height

    annotated_bgr_image = None # Default to None

    # Check if any hand landmarks were detected
    if result.hand_landmarks:
        # The output_image is the one provided by MediaPipe, containing the frame data
        # Convert mp.Image to NumPy array
        rgb_image = output_image.numpy_view()
        annotated_rgb_image = drawing.draw_landmarks_on_image(rgb_image, result)
        annotated_bgr_image = cv2.cvtColor(annotated_rgb_image, cv2.COLOR_RGB2BGR)
        
        if ENABLE_MOUSE_CONTROL and mouse_controller and screen_width and screen_height:
            # Use the first detected hand
            hand_landmarks = result.hand_landmarks[0]
            
            # Get the specific landmark for mouse control
            control_landmark = hand_landmarks[MOUSE_CONTROL_LANDMARK]

            # --- Absolute Mouse Positioning with Smoothing ---
            # Map landmark coordinates (0.0-1.0) to screen coordinates
            # MediaPipe's Y is 0 at top, 1 at bottom. Screen Y is also 0 at top, so direct mapping is fine.
            # MediaPipe's X is 0 at left, 1 at right. Screen X is also 0 at left.
            # If your camera view is mirrored, you might need to invert X: (1.0 - control_landmark.x)
            raw_x = control_landmark.x * screen_width
            raw_y = control_landmark.y * screen_height

            if is_first_mouse_move:
                target_x = raw_x
                target_y = raw_y
                is_first_mouse_move = False
            else:
                target_x = SMOOTHING_FACTOR * raw_x + (1 - SMOOTHING_FACTOR) * last_target_x
                target_y = SMOOTHING_FACTOR * raw_y + (1 - SMOOTHING_FACTOR) * last_target_y
            
            # Update last target for next frame's smoothing
            last_target_x = target_x
            last_target_y = target_y

            # Clamp values to screen boundaries and convert to int
            final_x = max(0, min(int(target_x), screen_width - 1))
            final_y = max(0, min(int(target_y), screen_height - 1))
            
            try:
                mouse_controller.position = (final_x, final_y)
            except Exception as e:
                print(f"Error setting mouse position: {e}") # Handle pynput errors if any

    # Put annotated image (or original if no annotation) into the queue
    if annotated_bgr_image is not None:
        annotated_frame_buffer.put(annotated_bgr_image)
    elif output_image: # If no landmarks, but we have an image, put its BGR version
        # This case might not be hit often if callback only fires on detection,
        # but good for robustness if behavior changes.
        # For now, assuming callback implies output_image is the frame with (potential) detections.
        # If there are no detections, draw_landmarks_on_image returns a copy of rgb_image.
        # So annotated_bgr_image should always be set if output_image exists.
        pass


def main():
    global mouse_controller, screen_width, screen_height, last_target_x, last_target_y, is_first_mouse_move

    scrcpy_process = None
    cam = None

    if ENABLE_MOUSE_CONTROL:
        try:
            mouse_controller = MouseController()
            screen_width, screen_height = system_utils.get_screen_resolution()
            if not screen_width or not screen_height:
                print("Warning: Could not get screen resolution. Mouse control will be disabled.")
                mouse_controller = None # Disable if no screen info
            else:
                print(f"Screen resolution: {screen_width}x{screen_height}. Mouse control enabled.")
                # Initialize last_target_x/y to the center of the screen to avoid None issues
                # or let is_first_mouse_move handle it.
                last_target_x = screen_width / 2
                last_target_y = screen_height / 2
                is_first_mouse_move = True

        except Exception as e:
            print(f"Error initializing mouse controller or getting screen resolution: {e}")
            print("Mouse control will be disabled.")
            mouse_controller = None

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
            video_playback=False,
            **scrcpy_custom_args
        )
        if scrcpy_process is None:
            print("Failed to start scrcpy. Exiting.")
            return
        
        print("Waiting for scrcpy and v4l2 device to initialize...")
        time.sleep(3) 

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
                    annotated_frame = annotated_frame_buffer.get_nowait()
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