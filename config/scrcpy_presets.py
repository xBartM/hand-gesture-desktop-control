def get_scrcpy_preset(cfg_name):
    """
    Get predefined scrcpy configurations for specific devices.

    Args:
        cfg_name (str): Name of the configuration preset.

    Returns:
        dict: A dictionary containing scrcpy arguments.

    Raises:
        ValueError: If an unknown cfg_name is provided.
    """
    cfg = {}
    if cfg_name == 'Xiaomi Mi 9t - Open Camera':
        cfg["video-codec"] = "h264"
        cfg["video-encoder"] = "OMX.qcom.video.encoder.avc"
        cfg["crop"] = "1080:1080:0:600"
    elif cfg_name == 'Xperia Z2 Tablet - Open Camera':
        cfg["video-codec"] = "h264"
        cfg["video-encoder"] = "OMX.qcom.video.encoder.avc"
        cfg["crop"] = "1080:1080:420:0"
        cfg["max-fps"] = "10" 
    else:
        raise ValueError(f"Unknown cfg_name: {cfg_name}")

    return cfg