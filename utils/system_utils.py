import os

def get_screen_resolution():
    """
    Get the resolution of the screen using xdpyinfo utility (Linux specific).

    Returns:
        tuple[int, int]: x and y components of screen resolution, or (None, None) if error.
    """
    try:
        output = os.popen("xdpyinfo | grep dimensions | awk '{print $2}'").read()
        screen_x_str, screen_y_str = output.strip().split('x')
        return int(screen_x_str), int(screen_y_str)
    except Exception as e:
        print(f"Could not get screen resolution using xdpyinfo: {e}")
        return None, None
