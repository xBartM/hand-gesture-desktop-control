# config/app_settings.py
import mediapipe as mp

# --- Scrcpy and Camera Configuration ---
V4L2_DEVICE = "/dev/video0"  # Virtual camera device for scrcpy output
SCRCPY_MAX_SIZE = 240        # Max resolution (height or width) for scrcpy feed
SCRCPY_CONFIG_PRESET_NAME = "Xperia Z2 Tablet - Open Camera" # Preset for scrcpy settings

# --- MediaPipe Model Configuration ---
MODEL_ASSET_PATH = '{your_path_to}/hand_landmarker.task'

# --- Mouse Control Configuration ---
ENABLE_MOUSE_CONTROL = True
# Landmark from mp.solutions.hands.HandLandmark used for cursor control
MOUSE_CONTROL_LANDMARK_INDEX = mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP.value
# Smoothing factor for mouse movement.
# If smoothing factor = 0.7, it means 70% of current raw, 30% of last.
# Lower values provide more smoothing but also more lag.
SMOOTHING_FACTOR = 0.7

# Margins define the active area of the camera feed for mouse control.
# Values are percentages of the frame (0.0 to 1.0).
# e.g., MARGIN_LEFT = 0.1 means 10% of the left side is ignored.
MARGIN_LEFT = 0.3
MARGIN_RIGHT = 0.1
MARGIN_TOP = 0.3
MARGIN_BOTTOM = 0.15