"""Download + build the demo media (run once after cloning).

Fetches a random portrait and a stock clip, then trims the clip to a light
150-frame demo video that the in-app "Load demo files" button uses:

    python demo/get_demo_media.py

Output: demo/source.jpg, demo/target.mp4 -> copied to static/demo/.
Pre-rendered swap: run a swap once via the web UI (saved to outputs/).
"""
import os
import random
import shutil
import urllib.request

import cv2

BASE = os.path.dirname(os.path.abspath(__file__))
STATIC_DEMO = os.path.join(os.path.dirname(BASE), "static", "demo")

PORTRAITS = [
    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=512&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=512&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=512&q=80&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=512&q=80&auto=format&fit=crop",
]
CLIP_URL = "https://videos.pexels.com/video-files/3209828/3209828-uhd_3840_2160_25fps.mp4"
FRAMES, WIDTH = 150, 960


def main():
    os.makedirs(BASE, exist_ok=True)
    os.makedirs(STATIC_DEMO, exist_ok=True)
    random.seed()
    src_url = random.choice(PORTRAITS)
    print("source:", src_url)
    urllib.request.urlretrieve(src_url, os.path.join(BASE, "source.jpg"))
    tmp = os.path.join(BASE, "_clip_full.mp4")
    print("clip:", CLIP_URL)
    req = urllib.request.Request(CLIP_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
        total = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total > 60_000_000:
                break
    cap = cv2.VideoCapture(tmp)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    scale = WIDTH / max(w, h)
    nw, nh = int(w * scale), int(h * scale)
    out = os.path.join(BASE, "target.mp4")
    vw = cv2.VideoWriter(out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (nw, nh))
    kept = 0
    while kept < FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        vw.write(cv2.resize(frame, (nw, nh)))
        kept += 1
    cap.release()
    vw.release()
    os.remove(tmp)
    print(f"kept {kept} frames -> {out}")
    for name in ("source.jpg", "target.mp4"):
        shutil.copy(os.path.join(BASE, name), os.path.join(STATIC_DEMO, name))
    print("copied to", STATIC_DEMO)
    print("Done. Start the app (python app.py) and click 'Load demo files & swap'.")


if __name__ == "__main__":
    main()
