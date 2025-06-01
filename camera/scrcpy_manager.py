import subprocess
import signal # Though not directly used if Popen object handles signals

def start_scrcpy_feed(feed_type='scrcpy', v4l2_device='/dev/video0', max_size=480, video_playback=False, **kwargs):
    """
    Start streaming selected feed_type to selected v4l2 device.
    Currently only supports 'scrcpy'.

    Args:
        feed_type (str, optional): select which feed to start. Defaults to 'scrcpy'.
        v4l2_device (str, optional): choose v4l2-sink device. Defaults to '/dev/video0'.
        max_size (int, optional): sets the feed resolution so it's <=max_size. Defaults to 480.
        video_playback (bool, optional): if True show scrcpy video output, otherwise don't.
        **kwargs: device config for scrcpy.
            "video-codec" (str, optional): e.g., "h264".
            "video-encoder" (str, optional): e.g., "MX.qcom.video.encoder.avc".
            "capture-orientation" (int, optional): e.g., 90.
            "crop" (str, optional): e.g., "1080:1080:0:600".

    Returns:
        subprocess.Popen: The Popen object for the started scrcpy process.

    Raises:
        ValueError: If an unknown feed_type is provided.
        FileNotFoundError: If scrcpy command is not found.
    """
    process = None
    if feed_type == 'scrcpy':
        print(f"Using v4l2loopback device: {v4l2_device}")
        try:
            scrcpy_command = [
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
            # Depending on desired behavior, you might want to raise e or return None
    else:
        raise ValueError(f"Unknown feed_type: {feed_type}")

    return process


def stop_scrcpy_feed(process: subprocess.Popen):
    """
    Stops the scrcpy process.

    Args:
        process (subprocess.Popen): The Popen object for the scrcpy process.
    """
    if process and process.poll() is None:  # Check if process is running
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
    elif process and process.poll() is not None:
        print("scrcpy feed was already stopped.")
    else:
        print("No scrcpy process object provided or process is None.")