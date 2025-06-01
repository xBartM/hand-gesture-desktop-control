# interaction/mouse_control.py
import math # For distance calculation
from pynput.mouse import Controller as MouseController, Button
from typing import List, Any # For type hinting hand_landmarks

from utils import system_utils
from config import app_settings

class MouseManager:
    """Encapsulates state related to mouse control."""
    def __init__(self):
        self.mouse_controller: MouseController | None = None
        self.screen_width: int | None = None
        self.screen_height: int | None = None
        self.last_target_x: float | None = None
        self.last_target_y: float | None = None
        self.is_first_move: bool = True
        self.is_left_button_pinched: bool = False

        # For adaptive smoothing
        self.prev_raw_landmark_x: float | None = None
        self.prev_raw_landmark_y: float | None = None


    def initialize(self) -> bool:
        """Initializes mouse controller and screen dimensions.
        
        Returns:
            True if initialization (or disabling) was successful, False otherwise.
        """
        if not app_settings.ENABLE_MOUSE_CONTROL:
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
            self.is_left_button_pinched = False
            self.prev_raw_landmark_x = None # Initialize for adaptive smoothing
            self.prev_raw_landmark_y = None
            return True

        except Exception as e:
            print(f"Error initializing mouse controller or getting screen resolution: {e}")
            print("Mouse control will be disabled.")
            self.mouse_controller = None
            return False # Indicate failure

    def cleanup(self):
        """Releases any held mouse buttons during cleanup."""
        if self.mouse_controller and self.is_left_button_pinched:
            try:
                self.mouse_controller.release(Button.left)
                self.is_left_button_pinched = False
                print("MouseManager cleanup: Released left mouse button held by pinch.")
            except Exception as e:
                print(f"Error releasing mouse button during cleanup: {e}")


def _handle_mouse_movement(
    hand_landmarks: List[Any], # List of NormalizedLandmark for one hand
    mouse_manager: MouseManager
):
    """Handles mouse pointer movement based on a control landmark with adaptive smoothing."""
    if not (0 <= app_settings.MOUSE_CONTROL_LANDMARK_INDEX < len(hand_landmarks)):
        print(f"Warning: MOUSE_CONTROL_LANDMARK_INDEX ({app_settings.MOUSE_CONTROL_LANDMARK_INDEX}) "
              f"is out of range for detected landmarks ({len(hand_landmarks)}).")
        return

    control_landmark = hand_landmarks[app_settings.MOUSE_CONTROL_LANDMARK_INDEX]
    current_raw_landmark_x = control_landmark.x
    current_raw_landmark_y = control_landmark.y

    current_smoothing_factor = app_settings.DEFAULT_SMOOTHING_FACTOR

    if app_settings.ENABLE_ADAPTIVE_SMOOTHING:
        if mouse_manager.prev_raw_landmark_x is not None and \
           mouse_manager.prev_raw_landmark_y is not None:
            
            delta_x = current_raw_landmark_x - mouse_manager.prev_raw_landmark_x
            delta_y = current_raw_landmark_y - mouse_manager.prev_raw_landmark_y
            # Velocity proxy: Euclidean distance in normalized landmark space
            velocity_proxy = math.sqrt(delta_x**2 + delta_y**2)

            low_thresh = app_settings.ADAPTIVE_SMOOTHING_VELOCITY_LOW_THRESHOLD
            high_thresh = app_settings.ADAPTIVE_SMOOTHING_VELOCITY_HIGH_THRESHOLD
            min_factor = app_settings.ADAPTIVE_SMOOTHING_MIN_FACTOR
            max_factor = app_settings.ADAPTIVE_SMOOTHING_MAX_FACTOR

            if high_thresh <= low_thresh: # Invalid configuration, fallback
                # print("Warning: Adaptive smoothing high_thresh <= low_thresh. Using max_factor.")
                current_smoothing_factor = max_factor
            elif velocity_proxy <= low_thresh:
                current_smoothing_factor = min_factor
            elif velocity_proxy >= high_thresh:
                current_smoothing_factor = max_factor
            else:
                # Linear interpolation between min_factor and max_factor
                ratio = (velocity_proxy - low_thresh) / (high_thresh - low_thresh)
                current_smoothing_factor = min_factor + ratio * (max_factor - min_factor)
                # Clamp to ensure it's within [min_factor, max_factor] bounds
                current_smoothing_factor = min(max(current_smoothing_factor, min_factor), max_factor)
        # If prev_raw_landmark is None (e.g., first frame after detection or hand reappearance),
        # current_smoothing_factor remains app_settings.DEFAULT_SMOOTHING_FACTOR for this frame.
    
    # Update previous raw landmark positions for the next frame's velocity calculation
    mouse_manager.prev_raw_landmark_x = current_raw_landmark_x
    mouse_manager.prev_raw_landmark_y = current_raw_landmark_y

    # Normalize landmark coordinates within the defined margins
    active_width_ratio = 1.0 - app_settings.MARGIN_LEFT - app_settings.MARGIN_RIGHT
    active_height_ratio = 1.0 - app_settings.MARGIN_TOP - app_settings.MARGIN_BOTTOM

    if active_width_ratio <= 0 or active_height_ratio <= 0:
        print("Error: Margins are too large, active area is zero or negative. Adjust MARGIN values in app_settings.py.")
        return

    norm_x = min(max((control_landmark.x - app_settings.MARGIN_LEFT) / active_width_ratio, 0.0), 1.0)
    norm_y = min(max((control_landmark.y - app_settings.MARGIN_TOP) / active_height_ratio, 0.0), 1.0)
    
    raw_screen_x = norm_x * mouse_manager.screen_width
    raw_screen_y = norm_y * mouse_manager.screen_height

    if mouse_manager.is_first_move or mouse_manager.last_target_x is None:
        target_x = raw_screen_x
        target_y = raw_screen_y
        mouse_manager.is_first_move = False
    else:
        target_x = (current_smoothing_factor * raw_screen_x +
                    (1 - current_smoothing_factor) * mouse_manager.last_target_x)
        target_y = (current_smoothing_factor * raw_screen_y +
                    (1 - current_smoothing_factor) * mouse_manager.last_target_y)
    
    mouse_manager.last_target_x = target_x
    mouse_manager.last_target_y = target_y

    final_x = max(0, min(int(target_x), mouse_manager.screen_width - 1))
    final_y = max(0, min(int(target_y), mouse_manager.screen_height - 1))
    
    try:
        mouse_manager.mouse_controller.position = (final_x, final_y)
    except Exception as e:
        print(f"Error setting mouse position: {e}")


def _handle_pinch_click(
    hand_landmarks: List[Any], # List of NormalizedLandmark for one hand
    mouse_manager: MouseManager
):
    """Handles pinch gesture for left mouse button click."""
    if not app_settings.ENABLE_PINCH_CLICK:
        return

    # Ensure landmark indices are valid
    required_indices = [app_settings.THUMB_TIP_INDEX, app_settings.INDEX_FINGER_TIP_INDEX]
    if not all(0 <= idx < len(hand_landmarks) for idx in required_indices):
        print(f"Warning: Pinch click landmark indices are out of range for detected landmarks ({len(hand_landmarks)}).")
        return

    thumb_tip = hand_landmarks[app_settings.THUMB_TIP_INDEX]
    index_finger_tip = hand_landmarks[app_settings.INDEX_FINGER_TIP_INDEX]

    # Calculate 2D distance between thumb tip and index finger tip using normalized coordinates
    delta_x = thumb_tip.x - index_finger_tip.x
    delta_y = thumb_tip.y - index_finger_tip.y
    # Consider adding z-coordinate if needed:
    # delta_z = thumb_tip.z - index_finger_tip.z
    # distance = math.sqrt(delta_x**2 + delta_y**2 + delta_z**2)
    distance = math.sqrt(delta_x**2 + delta_y**2)

    is_pinching_currently = distance < app_settings.PINCH_CLICK_DISTANCE_THRESHOLD

    if is_pinching_currently and not mouse_manager.is_left_button_pinched:
        try:
            mouse_manager.mouse_controller.press(Button.left)
            mouse_manager.is_left_button_pinched = True
            # print("Pinch detected - Left mouse button PRESSED.") # Optional: for debugging
        except Exception as e:
            print(f"Error pressing left mouse button due to pinch: {e}")
    elif not is_pinching_currently and mouse_manager.is_left_button_pinched:
        try:
            mouse_manager.mouse_controller.release(Button.left)
            mouse_manager.is_left_button_pinched = False
            # print("Pinch released - Left mouse button RELEASED.") # Optional: for debugging
        except Exception as e:
            print(f"Error releasing left mouse button after pinch: {e}")


def process_hand_for_mouse_control(
    hand_landmarks_list: List[Any], # List of mediapipe.framework.formats.landmark_pb2.NormalizedLandmark
    mouse_manager: MouseManager
):
    """Processes hand landmarks to control the mouse pointer and handle clicks.

    Args:
        hand_landmarks_list: A list of hand landmarks objects from MediaPipe.
                             Expected to be result.hand_landmarks. Each element is a list
                             of landmarks for one detected hand.
        mouse_manager: An instance of MouseManager containing mouse state and controller.
    """
    if not (app_settings.ENABLE_MOUSE_CONTROL and mouse_manager.mouse_controller and
            mouse_manager.screen_width and mouse_manager.screen_height):
        return # Mouse control not active or not initialized

    if hand_landmarks_list:
        # Assuming num_hands=1 in landmarker options (set in hand_tracker.py),
        # so take the first hand detected.
        # hand_landmarks is a list of NormalizedLandmark objects for the first detected hand.
        hand_landmarks_for_first_hand = hand_landmarks_list[0] 
        
        # Handle mouse movement
        _handle_mouse_movement(hand_landmarks_for_first_hand, mouse_manager)
        
        # Handle pinch click
        _handle_pinch_click(hand_landmarks_for_first_hand, mouse_manager)
    else:
        # No hands detected, reset previous landmark state for adaptive smoothing
        mouse_manager.prev_raw_landmark_x = None
        mouse_manager.prev_raw_landmark_y = None
        # Optionally, could also set mouse_manager.is_first_move = True
        # if we want the cursor to snap on re-detection without smoothing for the first frame.
        # Current behavior: if hand lost and reappears, first smoothed move will use DEFAULT_SMOOTHING_FACTOR.