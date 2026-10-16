"""HeadSwap Studio — Desktop edition (Tkinter).

Same full-head swap engine as the web app (`face_swap.py`), wrapped in a
native desktop GUI: pick a source photo + target video, tune sliders, watch
progress, and play/open the result. No server or browser needed.

Run:
    pip install -r requirements.txt   # from repo root, then:
    python desktop/faceswap_desktop.py
"""
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from face_swap import process_video  # noqa: E402
