# Standard library imports
import queue
import time
import traceback # For more detailed error logging if needed
import subprocess

# Third-party imports
import cv2
import mediapipe as mp
from pynput.mouse import Controller as MouseController

# Project-specific imports
from camera import scrcpy_manager
from config import scrcpy_presets
from utils import system_utils
from vision import drawing
from vision import hand_tracker # Imports HandLandmarkerResult, MpImage, MpImageFormat

# --- Configuration Constants ---
V4L2_DEVICE = "/dev/video0"  # Virtual camera device for scrcpy output
SCRCPY_MAX_SIZE = 240        # Max resolution (height or width) for scrcpy feed
MODEL_ASSET_PATH = '{your_path_to}/hand_landmarker.task' 
SCRCPY_CONFIG_PRESET_NAME = "Xperia Z2 Tablet - Open Camera" # Preset for scrcpy settings

# --- Mouse Control Configuration ---
ENABLE_MOUSE_CONTROL = True
# Landmark from mp.solutions.hands.HandLandmark used for cursor control
MOUSE_CONTROL_LANDMARK_INDEX = mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP.value
# Smoothing factor for mouse movement (0.0: no smoothing, 1.0: no movement).
# Lower values provide more smoothing but also more lag.
SMOOTHING_FACTOR = 0.7 # Adjusted from 0.5 for potentially less smoothing, more responsiveness.

# Margins define the active area of the camera feed for mouse control.
# Values are percentages of the frame (0.0 to 1.0).
# e.g., MARGIN_LEFT = 0.1 means 10% of the left side is ignored.
MARGIN_LEFT = 0.3
MARGIN_RIGHT = 0.1
MARGIN_TOP = 0.3
MARGIN_BOTTOM = 0.15

# --- Global State ---
# Queue for passing annotated frames from MediaPipe callback to main thread.
# maxsize=1 means older frames are dropped if the main thread is slow,
# preventing buildup and processing stale frames.
_annotated_frame_buffer = queue.Queue(maxsize=2)


class _MouseControlState:
    """Encapsulates state related to mouse control."""
    def __init__(self):
        self.mouse_controller: MouseController | None = None
        self.screen_width: int | None = None
        self.screen_height: int | None = None
        self.last_target_x: float | None = None
        self.last_target_y: float | None = None
        self.is_first_move: bool = True

    def initialize(self) -> bool:
        """Initializes mouse controller and screen dimensions.
        
        Returns:
            True if initialization (or disabling) was successful, False otherwise.
        """
        if not ENABLE_MOUSE_CONTROL:
            print("Mouse control is disabled by configuration.")
            return True # Successful in the sense that it's correctly disabled

        try:
            self.mouse_controller = MouseController()
            self.screen_width, self.screen_height = system_utils.get_screen_resolution()
            
            if not self.screen_width or not self.screen_height:
                print("Warning: Could not get screen resolution. Disabling mouse control.")
                self.mouse_controller = None # Ensure it's None
                return False # Indicate failure to enable mouse control fully
            
            print(f"Screen resolution: {self.screen_width}x{self.screen_height}. Mouse control enabled.")
            # Initialize last target to screen center for smoother start.
            self.last_target_x = self.screen_width / 2
            self.last_target_y = self.screen_height / 2
            self.is_first_move = True
            return True

        except Exception as e:  # pylint: disable=broad-except
            print(f"Error initializing mouse controller or getting screen resolution: {e}")
            print("Mouse control will be disabled.")
            self.mouse_controller = None
            return False # Indicate failure


_mouse_control_manager = _MouseControlState()


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
        # print("Debug: Annotated frame buffer full, dropping frame.")
        pass

    # --- Mouse Control Logic ---
    if not (ENABLE_MOUSE_CONTROL and _mouse_control_manager.mouse_controller and
            _mouse_control_manager.screen_width and _mouse_control_manager.screen_height):
        return # Mouse control not active or not initialized

    if result.hand_landmarks:
        # Assuming num_hands=1 in landmarker options, so take the first hand
        hand_landmarks = result.hand_landmarks[0]
        
        if not (0 <= MOUSE_CONTROL_LANDMARK_INDEX < len(hand_landmarks)):
            print(f"Warning: MOUSE_CONTROL_LANDMARK_INDEX ({MOUSE_CONTROL_LANDMARK_INDEX}) "
                  f"is out of range for detected landmarks ({len(hand_landmarks)}).")
            return

        control_landmark = hand_landmarks[MOUSE_CONTROL_LANDMARK_INDEX]

        # Normalize landmark coordinates within the defined margins
        active_width_ratio = 1.0 - MARGIN_LEFT - MARGIN_RIGHT
        active_height_ratio = 1.0 - MARGIN_TOP - MARGIN_BOTTOM

        if active_width_ratio <= 0 or active_height_ratio <= 0:
            print("Error: Margins are too large, active area is zero or negative. Adjust MARGIN values.")
            return

        # Calculate normalized X, Y within the active area. Clamp to [0, 1] to handle landmarks outside margins.
        norm_x = min(max((control_landmark.x - MARGIN_LEFT) / active_width_ratio, 0.0), 1.0)
        norm_y = min(max((control_landmark.y - MARGIN_TOP) / active_height_ratio, 0.0), 1.0)
        
        # Map to screen coordinates. Invert X if camera is mirrored (not handled here).
        raw_screen_x = norm_x * _mouse_control_manager.screen_width
        raw_screen_y = norm_y * _mouse_control_manager.screen_height

        if _mouse_control_manager.is_first_move or _mouse_control_manager.last_target_x is None:
            target_x = raw_screen_x
            target_y = raw_screen_y
            _mouse_control_manager.is_first_move = False
        else:
            # Apply smoothing: new_pos = (1-factor)*current_pos + factor*last_pos
            # Note: Original formula was SMOOTHING_FACTOR * raw + (1-SMOOTHING_FACTOR) * last
            # A common interpretation is: alpha * new + (1-alpha) * old
            # If SMOOTHING_FACTOR is closer to 1, it means less smoothing (more responsive).
            # If SMOOTHING_FACTOR is closer to 0, it means more smoothing (smoother but lags).
            # Let's make SMOOTHING_FACTOR intuitive: higher = smoother.
            # So, effective_alpha = (1 - SMOOTHING_FACTOR)
            # target_x = effective_alpha * raw_screen_x + (1 - effective_alpha) * _mouse_control_manager.last_target_x
            # This is equivalent to:
            # target_x = (1 - SMOOTHING_FACTOR) * raw_screen_x + SMOOTHING_FACTOR * _mouse_control_manager.last_target_x
            # Let's stick to the user's original formulation intent:
            # target_x = SMOOTHING_FACTOR * raw_screen_x + (1 - SMOOTHING_FACTOR) * _mouse_control_manager.last_target_x
            # If smoothing factor = 0.7, it means 70% of current raw, 30% of last.
            # For more smoothing, this factor should be smaller. Let's clarify comment for SMOOTHING_FACTOR.
            target_x = (SMOOTHING_FACTOR * raw_screen_x +
                        (1 - SMOOTHING_FACTOR) * _mouse_control_manager.last_target_x)
            target_y = (SMOOTHING_FACTOR * raw_screen_y +
                        (1 - SMOOTHING_FACTOR) * _mouse_control_manager.last_target_y)
        
        _mouse_control_manager.last_target_x = target_x
        _mouse_control_manager.last_target_y = target_y

        final_x = max(0, min(int(target_x), _mouse_control_manager.screen_width - 1))
        final_y = max(0, min(int(target_y), _mouse_control_manager.screen_height - 1))
        
        try:
            _mouse_control_manager.mouse_controller.position = (final_x, final_y)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error setting mouse position: {e}")
            # Potentially disable mouse control if errors persist
            # _mouse_control_manager.mouse_controller = None 


def _initialize_camera_feed() -> tuple[cv2.VideoCapture | None, subprocess.Popen | None]:
    """Starts scrcpy and connects to the V4L2 device.

    Returns:
        A tuple (cam, scrcpy_process). Both are None if initialization fails.
    """
    print(f"Requesting scrcpy config preset: {SCRCPY_CONFIG_PRESET_NAME}")
    try:
        scrcpy_custom_args = scrcpy_presets.get_scrcpy_preset(SCRCPY_CONFIG_PRESET_NAME)
        print(f"Using scrcpy arguments: {scrcpy_custom_args}")
    except ValueError as e:
        print(f"Warning: Error getting scrcpy preset '{SCRCPY_CONFIG_PRESET_NAME}': {e}.")
        print("Using default scrcpy settings (no custom args).")
        scrcpy_custom_args = {} # Ensure it's a dict
    
    scrcpy_process = scrcpy_manager.start_scrcpy_feed(
        v4l2_device=V4L2_DEVICE,
        max_size=SCRCPY_MAX_SIZE,
        video_playback=False,  # No separate scrcpy window shown by scrcpy itself
        **scrcpy_custom_args
    )
    if scrcpy_process is None:
        print("Failed to start scrcpy. Exiting.")
        return None, None
    
    print("Waiting for scrcpy and v4l2 device to initialize (3 seconds)...")
    time.sleep(3)

    cam = cv2.VideoCapture(V4L2_DEVICE)
    if not cam.isOpened():
        print(f"Error: Cannot open V4L2 device: {V4L2_DEVICE}")
        print("Make sure scrcpy is running and the v4l2loopback device is correctly set up.")
        scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        return None, None
    
    width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Camera {V4L2_DEVICE} opened with resolution: {width}x{height}")
    if width == 0 or height == 0:
        print("Error: Camera resolution is 0x0. Check scrcpy and v4l2loopback device.")
        cam.release()
        scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
        return None, None
        
    return cam, scrcpy_process


def main_loop(
    cam: cv2.VideoCapture,
    landmarker: hand_tracker.mp.tasks.vision.HandLandmarker
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
            # Check if scrcpy process terminated
            # (This check is illustrative; scrcpy_process is not in this scope)
            # if scrcpy_process and scrcpy_process.poll() is not None:
            # print(f"scrcpy process exited with code: {scrcpy_process.returncode}")
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
    
    if not _mouse_control_manager.initialize():
        # Initialization of mouse failed, but we might still want to run without mouse control
        # if ENABLE_MOUSE_CONTROL was true. If it was false, this is fine.
        if ENABLE_MOUSE_CONTROL: # Only print error if it was meant to be enabled
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
            MODEL_ASSET_PATH, _mediapipe_result_callback
        ) as landmarker:
            print("MediaPipe HandLandmarker initialized.")
            main_loop(cam, landmarker)

    except FileNotFoundError:
        print(f"Error: Model asset file not found at '{MODEL_ASSET_PATH}'. "
              "Please ensure the path is correct and the file exists.")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user (Ctrl+C).")
    except Exception as e:  # pylint: disable=broad-except
        print(f"An unexpected error occurred in the application: {e}")
        print("Traceback:")
        traceback.print_exc() # Provides more detailed error info
    finally:
        print("Cleaning up resources...")
        if cam:
            cam.release()
            print("Camera released.")
        if scrcpy_process:
            scrcpy_manager.stop_scrcpy_feed(scrcpy_process)
            # Note: stop_scrcpy_feed prints its own status messages.
        cv2.destroyAllWindows()
        print("OpenCV windows destroyed.")
        print("Cleanup complete. Exiting.")


if __name__ == '__main__':
    # Check for model path before starting anything complex
    import os
    if not os.path.exists(MODEL_ASSET_PATH):
        print(f"CRITICAL ERROR: MediaPipe model file not found at '{MODEL_ASSET_PATH}'.")
        print("Please update MODEL_ASSET_PATH in main.py.")
    else:
        run_application()