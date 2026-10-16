"""Full-head swap engine.

Two modes:
1. InsightFace inswapper (high quality, inner-face) if installed + model present.
2. OpenCV full-head paste (default, no heavy deps) — detects the head
   (face box expanded to include forehead/hair/chin), color-matches the
   source head to each target frame, and blends with seamlessClone +
   feathered elliptical mask. This literally swaps the full head, not
   just the inner face.
"""
import cv2
import numpy as np
import os
import sys
import threading
import urllib.request

YUNET_URLS = [
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"


def _model_search_paths():
    """Locations to look for the YuNet model, in priority order.

    Frozen (PyInstaller) builds bundle the model under sys._MEIPASS; the
    per-user data dir is the writable fallback for auto-download.
    """
    paths = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        paths.append(os.path.join(sys._MEIPASS, "models", YUNET_FILENAME))
        exe_dir = os.path.dirname(sys.executable)
        paths.append(os.path.join(exe_dir, "models", YUNET_FILENAME))
    paths.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "models", YUNET_FILENAME))
    paths.append(os.path.join(os.path.expanduser("~"), ".headswap_studio",
                               "models", YUNET_FILENAME))
    return paths


YUNET_PATH = _model_search_paths()[-2]  # default: alongside the source tree
_detector = None
_detector_input = None
_detector_lock = threading.Lock()


def _ensure_yunet():
    for candidate in _model_search_paths():
        if os.path.exists(candidate) and os.path.getsize(candidate) > 100000:
            return candidate
    dest = _model_search_paths()[-1]  # writable per-user dir
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last_err = None
    for url in YUNET_URLS:
        try:
            print(f"Downloading YuNet face model...", flush=True)
            urllib.request.urlretrieve(url, dest)
            if os.path.getsize(dest) > 100000:
                print("YuNet model ready.", flush=True)
                return dest
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not download face detection model: {last_err}")
