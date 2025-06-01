from typing import Dict

_SCRCPY_PRESETS: Dict[str, Dict[str, str]] = {
    'Xiaomi Mi 9t - Open Camera': {
        "video-codec": "h264",
        "video-encoder": "OMX.qcom.video.encoder.avc",
        "crop": "1080:1080:0:600"
    },
    'Xperia Z2 Tablet - Open Camera': {
        "video-codec": "h264",
        "video-encoder": "OMX.qcom.video.encoder.avc",
        "crop": "1080:1080:420:0",
        "max-fps": "30"
    }
    # Add more presets here
}

def get_scrcpy_preset(cfg_name: str) -> Dict[str, str]:
    """Gets predefined scrcpy configurations for specific devices.

    Args:
        cfg_name: Name of the configuration preset.

    Returns:
        A dictionary containing scrcpy arguments. A copy of the preset is
        returned to prevent modification of the original preset.

    Raises:
        ValueError: If an unknown cfg_name is provided.
    """
    if cfg_name in _SCRCPY_PRESETS:
        return _SCRCPY_PRESETS[cfg_name].copy()
    else:
        raise ValueError(f"Unknown scrcpy preset name: {cfg_name}")