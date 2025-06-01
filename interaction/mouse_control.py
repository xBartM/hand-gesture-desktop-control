# interaction/mouse_control.py
from pynput.mouse import Controller as MouseController
from typing import List, Any # For type hinting hand_landmarks

from utils import system_utils
from config import app_settings # To get MARGINS, SMOOTHING_FACTOR etc.
# mediapipe is imported by app_settings if needed for MOUSE_CONTROL_LANDMARK_INDEX,
# but not directly used here for type hinting landmark structure unless explicitly defined.

class MouseManager:
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
            return True

        except Exception as e:  # pylint: disable=broad-except
            print(f"Error initializing mouse controller or getting screen resolution: {e}")
            print("Mouse control will be disabled.")
            self.mouse_controller = None
            return False # Indicate failure


def process_hand_for_mouse_control(
    hand_landmarks_list: List[Any], # List of mediapipe.framework.formats.landmark_pb2.NormalizedLandmark
    mouse_manager: MouseManager
):
    """Processes hand landmarks to control the mouse pointer.

    Args:
        hand_landmarks_list: A list of hand landmarks objects from MediaPipe.
                             Expected to be result.hand_landmarks.
        mouse_manager: An instance of MouseManager containing mouse state and controller.
    """
    if not (app_settings.ENABLE_MOUSE_CONTROL and mouse_manager.mouse_controller and
            mouse_manager.screen_width and mouse_manager.screen_height):
        return # Mouse control not active or not initialized

    if hand_landmarks_list:
        # Assuming num_hands=1 in landmarker options (set in hand_tracker.py),
        # so take the first hand detected.
        hand_landmarks = hand_landmarks_list[0]
        
        if not (0 <= app_settings.MOUSE_CONTROL_LANDMARK_INDEX < len(hand_landmarks)):
            print(f"Warning: MOUSE_CONTROL_LANDMARK_INDEX ({app_settings.MOUSE_CONTROL_LANDMARK_INDEX}) "
                  f"is out of range for detected landmarks ({len(hand_landmarks)}).")
            return

        control_landmark = hand_landmarks[app_settings.MOUSE_CONTROL_LANDMARK_INDEX]

        # Normalize landmark coordinates within the defined margins
        active_width_ratio = 1.0 - app_settings.MARGIN_LEFT - app_settings.MARGIN_RIGHT
        active_height_ratio = 1.0 - app_settings.MARGIN_TOP - app_settings.MARGIN_BOTTOM

        if active_width_ratio <= 0 or active_height_ratio <= 0:
            print("Error: Margins are too large, active area is zero or negative. Adjust MARGIN values in app_settings.py.")
            return

        # Calculate normalized X, Y within the active area. Clamp to [0, 1] to handle landmarks outside margins.
        norm_x = min(max((control_landmark.x - app_settings.MARGIN_LEFT) / active_width_ratio, 0.0), 1.0)
        norm_y = min(max((control_landmark.y - app_settings.MARGIN_TOP) / active_height_ratio, 0.0), 1.0)
        
        # Map to screen coordinates.
        raw_screen_x = norm_x * mouse_manager.screen_width
        raw_screen_y = norm_y * mouse_manager.screen_height

        if mouse_manager.is_first_move or mouse_manager.last_target_x is None:
            target_x = raw_screen_x
            target_y = raw_screen_y
            mouse_manager.is_first_move = False
        else:
            # Apply smoothing: target_pos = smoothing_factor * current_raw_pos + (1 - smoothing_factor) * last_target_pos
            target_x = (app_settings.SMOOTHING_FACTOR * raw_screen_x +
                        (1 - app_settings.SMOOTHING_FACTOR) * mouse_manager.last_target_x)
            target_y = (app_settings.SMOOTHING_FACTOR * raw_screen_y +
                        (1 - app_settings.SMOOTHING_FACTOR) * mouse_manager.last_target_y)
        
        mouse_manager.last_target_x = target_x
        mouse_manager.last_target_y = target_y

        final_x = max(0, min(int(target_x), mouse_manager.screen_width - 1))
        final_y = max(0, min(int(target_y), mouse_manager.screen_height - 1))
        
        try:
            mouse_manager.mouse_controller.position = (final_x, final_y)
        except Exception as e:  # pylint: disable=broad-except
            print(f"Error setting mouse position: {e}")
            # Potentially disable mouse control if errors persist
            # mouse_manager.mouse_controller = None