import subprocess
from typing import Optional, List, Dict, Any

def start_scrcpy_feed(
    feed_type: str = 'scrcpy',
    v4l2_device: str = '/dev/video0',
    max_size: int = 480,
    video_playback: bool = False,
    **kwargs: Any
) -> Optional[subprocess.Popen]:
    """Starts streaming selected feed_type to selected v4l2 device.

    Currently only supports 'scrcpy'.

    Args:
        feed_type: Select which feed to start. Defaults to 'scrcpy'.
        v4l2_device: Choose v4l2-sink device. Defaults to '/dev/video0'.
        max_size: Sets the feed resolution so it's <=max_size. Defaults to 480.
        video_playback: If True, show scrcpy video output; otherwise, don't.
        **kwargs: Additional device configuration for scrcpy. Examples:
            "video-codec" (str): e.g., "h264".
            "video-encoder" (str): e.g., "MX.qcom.video.encoder.avc".
            "capture-orientation" (int): e.g., 90.
            "crop" (str): e.g., "1080:1080:0:600".

    Returns:
        A subprocess.Popen object for the started scrcpy process, or None
        if an error occurred during startup (other than FileNotFoundError).

    Raises:
        ValueError: If an unknown feed_type is provided.
        FileNotFoundError: If scrcpy command is not found.
    """
    process = None
    if feed_type == 'scrcpy':
        print(f"Using v4l2loopback device: {v4l2_device}")
        try:
            scrcpy_command: List[str] = [
                "scrcpy",
                f"--max-size={max_size}",
                f"--v4l2-sink={v4l2_device}",
            ]
            for arg_name, arg_value in kwargs.items():
                scrcpy_command.append(f"--{arg_name}={arg_value}")
            if not video_playback:
                scrcpy_command.append("--no-playback")
            
            print(f"Running command: {' '.join(scrcpy_command)}")
            process = subprocess.Popen(scrcpy_command)
        except FileNotFoundError:
            print("Error: scrcpy command not found. Is it installed and in your PATH?")
            raise
        except Exception as e:
            print(f"Error starting scrcpy: {e}")
            return None
    else:
        raise ValueError(f"Unknown feed_type: {feed_type}")

    return process


def stop_scrcpy_feed(process: Optional[subprocess.Popen]):
    """Stops the scrcpy process.

    Args:
        process: The Popen object for the scrcpy process, or None.
    """
    if process is None:
        print("No scrcpy process object provided to stop.")
        return

    if process.poll() is None:  # Check if process is running
        print("Stopping scrcpy feed...")
        process.terminate()  # Send SIGTERM
        try:
            process.wait(timeout=5)  # Wait for graceful termination
            print("scrcpy feed stopped gracefully.")
        except subprocess.TimeoutExpired:
            print("scrcpy feed did not terminate gracefully, killing...")
            process.kill()  # Send SIGKILL
            process.wait() # Ensure it's killed
            print("scrcpy feed killed.")
    else:
        print(f"scrcpy feed was already stopped (return code: {process.returncode}).")