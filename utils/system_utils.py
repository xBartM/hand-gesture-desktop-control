import os
from typing import Tuple, Optional

def get_screen_resolution() -> Tuple[Optional[int], Optional[int]]:
    """Gets the resolution of the primary screen using xdpyinfo (Linux specific).

    Returns:
        A tuple containing (width, height) of the screen in pixels.
        Returns (None, None) if the resolution cannot be determined or if
        xdpyinfo is not available or fails.
    """
    try:
        output = os.popen("xdpyinfo | grep dimensions | awk '{print $2}'").read()
        screen_x_str, screen_y_str = output.strip().split('x')
        return int(screen_x_str), int(screen_y_str)
    except Exception as e:
        print(f"Could not get screen resolution using xdpyinfo: {e}")
        return None, None
