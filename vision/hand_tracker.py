from typing import Callable

import mediapipe as mp

# Type aliases for MediaPipe components, re-exported for convenience.
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
MpImage = mp.Image
MpImageFormat = mp.ImageFormat

# Define a more specific callable type for the result callback function
ResultCallbackType = Callable[[HandLandmarkerResult, MpImage, int], None]


def create_hand_landmarker(
    model_path: str,
    result_callback_fn: ResultCallbackType
) -> mp.tasks.vision.HandLandmarker:
    """Creates and configures a MediaPipe HandLandmarker for live stream mode.

    Args:
        model_path: Path to the hand_landmarker.task model file.
        result_callback_fn: The function to call with detection results.
            It should accept three arguments:
            - result: mediapipe.tasks.vision.HandLandmarkerResult
            - output_image: mediapipe.Image (the input image passed to detect_async)
            - timestamp_ms: int (the timestamp passed to detect_async)

    Returns:
        A mediapipe.tasks.vision.HandLandmarker instance.
    
    Raises:
        RuntimeError: If the hand landmarker cannot be created from options
                      (e.g., model file not found, invalid options). This is
                      typically raised by MediaPipe's `create_from_options`.
    """
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.LIVE_STREAM,
        num_hands=1,  # Assuming control with one hand for simplicity
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        result_callback=result_callback_fn
    )
    return HandLandmarker.create_from_options(options)