# Hand Gesture Desktop Control

Control your desktop mouse using hand gestures via your Android phone's camera (streamed with `scrcpy`) and MediaPipe. Features mouse movement (controlled by middle finger MCP by default) and pinch-to-click (Left Mouse Button).

## Prerequisites
*   Linux (due to `v4l2loopback` for camera feed and `xdpyinfo` for screen resolution).
*   Android device with USB debugging enabled.
*   `scrcpy` installed and accessible in your PATH.
*   `v4l2loopback-dkms`:
    ```bash
    sudo apt update
    sudo apt install v4l2loopback-dkms
    ```
*   Python 3.x (3.8+ recommended).
*   MediaPipe `hand_landmarker.task` model file. Download from [MediaPipe Models](https://developers.google.com/mediapipe/solutions/vision/hand_landmarker#models).

## Setup
1.  **Load v4l2loopback module:**
    ```bash
    sudo modprobe v4l2loopback video_nr=10 card_label="ScrcpyV4L2Loopback" exclusive_caps=1
    ```
    (This attempts to create `/dev/video10`. Adjust `video_nr` if needed. Check with `ls /dev/video*`). The device path must match `V4L2_DEVICE` in settings.

2.  **Create and activate a Python virtual environment (recommended):**
    ```bash
    python3 -m venv .venv --prompt hand-desktop
    source .venv/bin/activate
    ```

3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the application:**
    *   Open `config/app_settings.py`.
    *   Update `MODEL_ASSET_PATH` to the absolute path of your downloaded `hand_landmarker.task` file.
    *   Verify `V4L2_DEVICE` matches the device created by `modprobe` (e.g., `/dev/video10`).
    *   (Optional) Adjust `SCRCPY_CONFIG_PRESET_NAME` if you have specific scrcpy settings for your device (defined in `config/scrcpy_presets.py`), or other mouse control parameters.

## Running
1.  Connect your Android device via USB. Ensure USB debugging is authorized.
2.  (If using venv) Activate the virtual environment: `source .venv/bin/activate`
3.  Run the application:
    ```bash
    python main.py
    ```
    The script will attempt to start `scrcpy`, streaming your phone's screen to the V4L2 virtual camera. Two OpenCV windows will appear: 'Original Camera Feed' and 'Annotated Hand Landmarks'.

4.  **Control:**
    *   Position your hand in the camera view.
    *   Move your hand to control the mouse cursor.
    *   Pinch your thumb tip and index finger tip together for a Left Mouse Button click.
    *   Press 'q' in either OpenCV window to quit.

## Troubleshooting
*   **"Error: Cannot open V4L2 device"**:
    *   Ensure `modprobe v4l2loopback` was successful and the device path in `app_settings.py` is correct.
    *   Verify `scrcpy` can connect to your phone independently (`scrcpy --v4l2-sink=/dev/videoN --no-playback`).
    *   Check permissions for `/dev/videoN`.
*   **"CRITICAL ERROR: MediaPipe model file not found"**: Double-check `MODEL_ASSET_PATH` in `config/app_settings.py`.
*   **No scrcpy window / No camera feed**: Check terminal output from `python main.py` for `scrcpy` errors. Ensure your phone is connected and authorized.

## Acknowledgements
This project was mostly vibe-coded — still fun though :)
