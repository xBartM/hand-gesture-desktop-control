# config/app_settings.py
import mediapipe as mp

# --- Scrcpy and Camera Configuration ---
V4L2_DEVICE = "/dev/video0"  # Virtual camera device for scrcpy output
SCRCPY_MAX_SIZE = 240        # Max resolution (height or width) for scrcpy feed
# SCRCPY_MAX_SIZE = 1080        # Max resolution (height or width) for scrcpy feed
SCRCPY_CONFIG_PRESET_NAME = "Xperia Z2 Tablet - Open Camera" # Preset for scrcpy settings

# --- MediaPipe Model Configuration ---
MODEL_ASSET_PATH = '{your_path_to}/hand_landmarker.task'

# --- Mouse Control Configuration ---
ENABLE_MOUSE_CONTROL = True
# Landmark from mp.solutions.hands.HandLandmark used for cursor control
MOUSE_CONTROL_LANDMARK_INDEX = mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP.value

# Margins define the active area of the camera feed for mouse control.
# Values are percentages of the frame (0.0 to 1.0).
# e.g., MARGIN_LEFT = 0.1 means 10% of the left side is ignored.
MARGIN_LEFT = 0.3
MARGIN_RIGHT = 0.1
MARGIN_TOP = 0.3
MARGIN_BOTTOM = 0.15

# --- Mouse Smoothing Configuration ---
# Default smoothing factor if adaptive smoothing is disabled.
# Higher value (closer to 1.0) = more responsive, less smooth.
# Lower value (closer to 0.0) = smoother, more lag.
DEFAULT_SMOOTHING_FACTOR = 0.7

ENABLE_ADAPTIVE_SMOOTHING = True # Set to False to use DEFAULT_SMOOTHING_FACTOR

# Settings for adaptive smoothing (if ENABLE_ADAPTIVE_SMOOTHING is True)
# Smoothing factor dynamically adjusts based on hand movement speed.
# Factor applied when hand is moving slowly (reduces jitter).
ADAPTIVE_SMOOTHING_MIN_FACTOR = 0.2
# Factor applied when hand is moving quickly (maintains responsiveness).
ADAPTIVE_SMOOTHING_MAX_FACTOR = 0.85

# Velocity thresholds (distance moved by the raw control landmark in normalized
# coordinates between frames).
# Below this velocity, MIN_FACTOR is used.
ADAPTIVE_SMOOTHING_VELOCITY_LOW_THRESHOLD = 0.003 # Threshold for very slow movement / jitter
# Above this velocity, MAX_FACTOR is used.
ADAPTIVE_SMOOTHING_VELOCITY_HIGH_THRESHOLD = 0.025 # Threshold for clear, intentional movement
# Between LOW and HIGH thresholds, the factor is linearly interpolated.
# Ensure ADAPTIVE_SMOOTHING_VELOCITY_LOW_THRESHOLD < ADAPTIVE_SMOOTHING_VELOCITY_HIGH_THRESHOLD.

# --- Pinch Click Configuration ---
ENABLE_PINCH_CLICK = True
# Landmark indices for pinch detection (MediaPipe HandLandmark enum)
THUMB_TIP_INDEX = mp.solutions.hands.HandLandmark.THUMB_TIP.value      # Index 4
INDEX_FINGER_TIP_INDEX = mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP.value # Index 8
# Distance threshold for pinch detection (in normalized coordinates).
# This value may need tuning based on camera setup and desired sensitivity.
# A smaller value requires fingers to be closer.
PINCH_CLICK_DISTANCE_THRESHOLD = 0.08