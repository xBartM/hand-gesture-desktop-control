# Standard library imports
import queue
import time
import traceback # For more detailed error logging if needed
import subprocess
import os # For checking model path

# Third-party imports
import cv2
# mediapipe is imported indirectly via other project modules or app_settings

# Project-specific imports
from camera import scrcpy_manager
from config import scrcpy_presets
from config import app_settings # Import new application settings
from interaction import mouse_control # Import new mouse control module
from vision import drawing
from vision import hand_tracker # Imports HandLandmarkerResult, MpImage, MpImageFormat

# --- Global State ---
# Queue for passing annotated frames from MediaPipe callback to main thread.
_annotated_frame_buffer = queue.Queue(maxsize=2)

# Initialize Mouse Manager
_mouse_manager_instance = mouse_control.MouseManager()


def _mediapipe_result_callback(
    result: hand_tracker.HandLandmarkerResult,
    output_image: hand_tracker.MpImage,
    timestamp_ms: int  # pylint: disable=unused-argument
):
    """Callback for MediaPipe HandLandmarker results.

    Processes detection results, annotates images, and handles mouse control.
    This function is called by MediaPipe in a separate thread.

    Args:
        result: The hand landmarker detection result.
        output_image: The MediaPipe image object (RGB) containing the frame data.
        timestamp_ms: The timestamp of the frame when detection was run.
    """
    # output_image.numpy_view() provides an RGB NumPy array
    annotated_rgb_image = drawing.draw_landmarks_on_image(
        output_image.numpy_view(), result
    )
    # Convert to BGR for OpenCV display
    annotated_bgr_image = cv2.cvtColor(annotated_rgb_image, cv2.COLOR_RGB2BGR)

    try:
        _annotated_frame_buffer.put_nowait(annotated_bgr_image)
    except queue.Full:
        # This is expected if the main loop is slower than the callback.
        pass

    # --- Mouse Control Logic (delegated) ---
    mouse_control.process_hand_for_mouse_control(
        result.hand_landmarks, # This is a list of lists of landmarks
        _mouse_manager_instance
    )


def _initialize_camera_feed() -> tuple[cv2.VideoCapture | None, subprocess.Popen | None]:
    """Starts scrcpy and connects to the V4L2 device.

    Returns:
        A tuple (cam, scrcpy_process). Both are None if initialization fails.
    """
    print(f"Requesting scrcpy config preset: {app_settings.SCRCPY_CONFIG_PRESET_NAME}")
    try:
        scrcpy_custom_args = scrcpy_presets.get_scrcpy_preset(app_settings.SCRCPY_CONFIG_PRESET_NAME)
        print(f"Using scrcpy arguments: {scrcpy_custom_args}")
    except ValueError as e:
        print(f"Warning: Error getting scrcpy preset '{app_settings.SCRCPY_CONFIG_PRESET_NAME}': {e}.")
        print("Using default scrcpy settings (no custom args).")
        scrcpy_custom_args = {} # Ensure it's a dict
    
    scrcpy_process = scrcpy_manager.start_scrcpy_feed(
        v4l2_device=app_settings.V4L2_DEVICE,
        max_size=app_settings.SCRCPY_MAX_SIZE,
        video_playback=False,  # No separate scrcpy window shown by scrcpy itself
        **scrcpy_custom_args
    )
    if scrcpy_process is None:
        print("Failed to start scrcpy. Exiting.")
        return None, None
    
    print("Waiting for scrcpy and v4l2 device to initialize (3 seconds)...")
    time.sleep(3)

    cam = cv2.VideoCapture(app_settings.V4L2_DEVICE)
    if not cam.isOpened():
        print(f"Error: Cannot open V4L2 device: {app_settings.V4L2_DEVICE}")
        print("Make sure scrcpy is running and the v4l2loopback device is correctly set up.")
        scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        return None, None
    
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera {app_settings.V4L2_DEVICE} opened with resolution: {width}x{height}")
    if width == 0 or height == 0:
        print("Error: Camera resolution is 0x0. Check scrcpy and v4l2loopback device.")
        cam.release()
        scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        return None, None
        
    return cam, scrcpy_process


def main_loop(
    cam: cv2.VideoCapture,
    landmarker: hand_tracker.mp.tasks.vision.HandLandmarker # type: ignore
):
    """Runs the main frame processing and display loop.

    Args:
        cam: Initialized OpenCV VideoCapture object.
        landmarker: Initialized MediaPipe HandLandmarker object.
    """
    timestamp_ns0 = time.monotonic_ns() # Base for frame timestamps

    while True:
        cam_status, bgr_frame = cam.read()
        if not cam_status:
            print("Error: Could not read frame from camera. scrcpy might have stopped.")
            break
        
        current_time_ns = time.monotonic_ns()
        frame_timestamp_ms = (current_time_ns - timestamp_ns0) // 1_000_000

        # Display the original camera feed
        cv2.imshow('Original Camera Feed', bgr_frame)

        # Display the annotated frame from the callback if available
        try:
            annotated_frame = _annotated_frame_buffer.get_nowait()
            cv2.imshow('Annotated Hand Landmarks', annotated_frame)
        except queue.Empty:
            pass # No new annotated frame, continue

        # Process keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("Quit key (q) pressed. Exiting loop.")
            break
        
        # Convert frame from BGR (OpenCV) to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        
        # Create MediaPipe Image object
        mp_image = hand_tracker.MpImage(
            image_format=hand_tracker.MpImageFormat.SRGB, data=rgb_frame
        )
        
        # Perform asynchronous hand detection
        landmarker.detect_async(mp_image, frame_timestamp_ms)


def run_application():
    """Main function to set up and run the hand gesture desktop control application."""
    
    if not _mouse_manager_instance.initialize():
        # Initialization of mouse failed, but we might still want to run without mouse control
        # if app_settings.ENABLE_MOUSE_CONTROL was true.
        if app_settings.ENABLE_MOUSE_CONTROL: # Only print error if it was meant to be enabled
             print("Mouse control could not be initialized. Proceeding without it if possible.")
    
    cam = None
    scrcpy_process = None

    try:
        cam, scrcpy_process = _initialize_camera_feed()
        if not cam or not scrcpy_process:
            print("Camera feed initialization failed. Exiting.")
            return

        # MediaPipe HandLandmarker setup
        # The 'with' statement ensures landmarker.close() is called.
        with hand_tracker.create_hand_landmarker(
            app_settings.MODEL_ASSET_PATH, _mediapipe_result_callback
        ) as landmarker:
            if landmarker is None: # create_hand_landmarker might raise but could also return None on some errors
                print("Failed to create MediaPipe HandLandmarker. Exiting.")
                # Ensure this case aligns with how create_hand_landmarker signals failure
                return
            print("MediaPipe HandLandmarker initialized.")
            main_loop(cam, landmarker)

    except FileNotFoundError: # Specifically for model asset path in create_hand_landmarker
        print(f"Error: Model asset file not found at '{app_settings.MODEL_ASSET_PATH}'. "
              "Please ensure the path is correct and the file exists in app_settings.py.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user (Ctrl+C).")
    except Exception as e:  # pylint: disable=broad-except
        print(f"An unexpected error occurred in the application: {e}")
        print("Traceback:")
        traceback.print_exc() # Provides more detailed error info
    finally:
        print("Cleaning up resources...")
        if _mouse_manager_instance: # _mouse_manager_instance is globally defined
            _mouse_manager_instance.cleanup() # Call cleanup for mouse manager
        if cam:
            cam.release()
            print("Camera released.")
        if scrcpy_process:
            scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        cv2.destroyAllWindows()
        print("OpenCV windows destroyed.")
        print("Cleanup complete. Exiting.")


if __name__ == '__main__':
    if not os.path.exists(app_settings.MODEL_ASSET_PATH):
        print(f"CRITICAL ERROR: MediaPipe model file not found at '{app_settings.MODEL_ASSET_PATH}'.")
        print("Please update MODEL_ASSET_PATH in config/app_settings.py.")
    else:
        run_application()