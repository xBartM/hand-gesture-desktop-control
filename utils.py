import os
import subprocess
import signal

def start_camera(feed_type='scrcpy', v4l2_device='/dev/video0', max_size=480, video_playback=False):
    """
    Start streaming selected feed_type to selected v4l2 device.

    Args:
        feed_type (str, optional): select which feed to start
            'scrcpy' (default): use scrcpy utility to get feed from an android device
        v4l2_device (str, optional): choose v4l2-sink device. Defaults to '/dev/video0'
        max_size (int, optional): sets the feed resolution so it's <=max_size. Defaults to 480.
        video_playback (bool, optional): if True show scrcpy video output, otherwise don't

    Returns:
        int: PID of the subprocess created

    Raises:
        ValueError: If an unknown feed_type is provided
    """

    SCR_X, SCR_Y = get_screen_resolution()
    """int, int: x and y component of the screen"""

    match feed_type:
        case 'scrcpy':
            print(f"Using v4l2loopback device: {v4l2_device}")
            try:
                # create scrcpy command as needed
                # for now video-codec and encoder are my device specific
                scrcpy_command = [
                    "scrcpy",
                    "--video-codec=h264",
                    "--video-encoder=OMX.qcom.video.encoder.avc",
                    "--capture-orientation=0",  # make it a parameter
                    "--crop=1080:1080:0:600",   # make it a parameter
                    f"--max-size={max_size}",
                    f"--v4l2-sink={v4l2_device}",
                    # "--no-playback",         # Don't show scrcpy's playback
                ]
                if not video_playback:
                    scrcpy_command.append("--no-playback") 
                print(f"Running command: {' '.join(scrcpy_command)}")
                # Run scrcpy in the background or manage its process as needed
                process = subprocess.Popen(scrcpy_command)
                # print(f"scrcpy started with PID: {process.pid}")
                # You might want to wait for it or manage it:
                # process.wait()
            except FileNotFoundError:
                print("Error: scrcpy command not found. Is it installed and in your PATH?")
            except Exception as e:
                print(f"Error starting scrcpy: {e}")
        case _:
            raise ValueError(f"Unknown feed_type: {feed_type}")

    return process.pid


def get_screen_resolution():
    """
    Get the resolution of the screen using xdpyinfo utility.

    Returns:
        int, int: x and y components of screen resolution
    """
    output = os.popen("xdpyinfo | grep dimensions | awk '{print $2}'").read()
    screen_x, screen_y = output.strip().split('x')
    return screen_x, screen_y

# ret = start_camera()
# print (ret)
# if input() == 'q':
#     os.kill(ret, signal.SIGSTOP)