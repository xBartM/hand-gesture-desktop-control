import os
import subprocess
import signal

def start_camera(feed_type='scrcpy', v4l2_device='/dev/video0', max_size=480, video_playback=False, **kwargs):
    """
    Start streaming selected feed_type to selected v4l2 device.

    Args:
        feed_type (str, optional): select which feed to start
            'scrcpy' (default): use scrcpy utility to get feed from an android device
        v4l2_device (str, optional): choose v4l2-sink device. Defaults to '/dev/video0'
        max_size (int, optional): sets the feed resolution so it's <=max_size. Defaults to 480.
        video_playback (bool, optional): if True show scrcpy video output, otherwise don't
        **kwargs: device config.
            For scrcpy:
                "video-codec" (str, optional): which video codec to use (ex. "h264"). 
                    Defaults to None (choice made by scrcpy)
                "video-encoder" (str, optional): which video encoder to use 
                    (ex. "MX.qcom.video.encoder.avc"). 
                    Defaults to None (choice made by scrcpy)
                "capture-orientation" (int, optional): rotate output by this 
                    much (ex. 90). Defaults to 0.
                "crop" (str, optional): record only part of the screen, 
                    format "xsize:ysize:xoffset:yoffset" (ex. "1080:1080:0:600"). 
                    Defaults to None (fullscreen)

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
                # Run scrcpy in the background or manage its process as needed
                process = subprocess.Popen(scrcpy_command)
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

def get_config(cfg_name):
    cfg = {}
    match cfg_name:
        case 'Xiaomi Mi 9t - Open Camera':
            cfg["video-codec"]      = "h264"
            cfg["video-encoder"]    = "OMX.qcom.video.encoder.avc"
            cfg["crop"]             = "1080:1080:0:600"          
        case 'Xperia Z2 Tablet - Open Camera':
            cfg["video-codec"]      = "h264"
            cfg["video-encoder"]    = "OMX.qcom.video.encoder.avc"
            # cfg["crop"]             = "1080:1080:0:600"          
        case _:
            raise ValueError(f"Unknown cfg_name: {cfg_name}")

    return cfg

# ret = start_camera()
# print (ret)
# if input() == 'q':
    # os.kill(ret, signal.SIGSTOP)