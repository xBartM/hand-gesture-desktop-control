import mediapipe as mp

# Re-export for convenience in main.py type hints
HandLandmarkerResult = mp.tasks.vision.HandLandmarkerResult
MpImage = mp.Image # Re-export for convenience
MpImageFormat = mp.ImageFormat # Re-export for convenience

def create_hand_landmarker(model_path: str, result_callback_fn):
    """
    Creates and configures a MediaPipe HandLandmarker for live stream mode.

    Args:
        model_path (str): Path to the hand_landmarker.task model file.
        result_callback_fn (callable): The function to call with detection results.
                                       It should accept (HandLandmarkerResult, mp.Image, int).

    Returns:
        mp.tasks.vision.HandLandmarker: An instance of the HandLandmarker.
    """
    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=VisionRunningMode.LIVE_STREAM,
        result_callback=result_callback_fn
    )
    return HandLandmarker.create_from_options(options)