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
import threading
import urllib.request

YUNET_URLS = [
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
YUNET_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "face_detection_yunet_2023mar.onnx")
_detector = None
_detector_input = None
_detector_lock = threading.Lock()


def _ensure_yunet():
    if os.path.exists(YUNET_PATH) and os.path.getsize(YUNET_PATH) > 100000:
        return YUNET_PATH
    os.makedirs(os.path.dirname(YUNET_PATH), exist_ok=True)
    last_err = None
    for url in YUNET_URLS:
        try:
            print(f"Downloading YuNet face model...", flush=True)
            urllib.request.urlretrieve(url, YUNET_PATH)
            if os.path.getsize(YUNET_PATH) > 100000:
                print("YuNet model ready.", flush=True)
                return YUNET_PATH
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Could not download face detection model: {last_err}")


def _get_detector(w, h):
    global _detector, _detector_input
    model = _ensure_yunet()
    if _detector is None:
        _detector = cv2.FaceDetectorYN_create(model, "", (w, h), score_threshold=0.6)
        _detector_input = (w, h)
    if _detector_input != (w, h):
        _detector.setInputSize((w, h))
        _detector_input = (w, h)
    return _detector


def detect_faces_bgr(img_bgr):
    h, w = img_bgr.shape[:2]
    try:
        with _detector_lock:  # YuNet detector is not thread-safe (Flask serves threaded)
            det = _get_detector(w, h)
            _, faces = det.detect(img_bgr)
        if faces is None:
            return np.array([])
        out = []
        for f in faces:
            x, y, ww, hh = (int(f[0]), int(f[1]), int(f[2]), int(f[3]))
            if ww < 20 or hh < 20:
                continue
            out.append((x, y, ww, hh))
        return np.array(out)
    except RuntimeError:
        raise
    except Exception:
        return np.array([])


def largest_box(boxes):
    if len(boxes) == 0:
        return None
    areas = [(w * h, (x, y, w, h)) for (x, y, w, h) in boxes]
    areas.sort(reverse=True)
    return areas[0][1]


def expand_to_head(box, img_w, img_h, top=0.85, side=0.30, bottom=0.20):
    """Expand a face box to a full-head box (hair + forehead + jaw)."""
    x, y, w, h = box
    cx = x + w / 2
    new_w = w * (1 + side * 2)
    new_h = h * (1 + top + bottom)
    new_x = cx - new_w / 2
    new_y = y - h * top
    new_x = max(0, int(new_x))
    new_y = max(0, int(new_y))
    new_w = min(img_w - new_x, int(new_w))
    new_h = min(img_h - new_y, int(new_h))
    if new_w <= 10 or new_h <= 10:
        return (x, y, w, h)
    return (new_x, new_y, new_w, new_h)


def head_ellipse_mask(w, h, feather=21, head_expansion=1.0):
    """Feathered elliptical mask shaped like a head (taller than wide)."""
    mask = np.zeros((h, w), dtype=np.uint8)
    cx, cy = w // 2, int(h * 0.46)
    ax, ay = int(w * 0.46 * head_expansion), int(h * 0.48 * head_expansion)
    cv2.ellipse(mask, (cx, cy), (ax, ay), 0, 0, 360, 255, -1)
    cv2.ellipse(mask, (cx, int(h * 0.62)), (int(ax * 0.82), int(ay * 0.62)), 0, 0, 360, 255, -1)
    if feather > 0:
        k = feather | 1
        mask = cv2.GaussianBlur(mask, (k, k), 0)
    return mask


def color_match_lab(source_bgr, target_bgr):
    """Match source mean/std to target in LAB for lighting consistency."""
    try:
        src_lab = cv2.cvtColor(source_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        tgt_lab = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        out = np.zeros_like(src_lab)
        for i in range(3):
            s_mean, s_std = src_lab[:, :, i].mean(), src_lab[:, :, i].std()
            t_mean, t_std = tgt_lab[:, :, i].mean(), tgt_lab[:, :, i].std()
            if s_std < 1e-3:
                out[:, :, i] = src_lab[:, :, i]
            else:
                out[:, :, i] = (src_lab[:, :, i] - s_mean) * (t_std / (s_std + 1e-6)) + t_mean
        out = np.clip(out, 0, 255).astype(np.uint8)
        return cv2.cvtColor(out, cv2.COLOR_LAB2BGR)
    except Exception:
        return source_bgr


def extract_source_head(source_bgr, top=0.85, side=0.30, bottom=0.20):
    h, w = source_bgr.shape[:2]
    faces = detect_faces_bgr(source_bgr)
    if len(faces) == 0:
        raise ValueError("No face found in source image. Try a clear front-facing photo.")
    box = largest_box(faces)
    hx, hy, hw, hh = expand_to_head(box, w, h, top, side, bottom)
    head = source_bgr[hy:hy + hh, hx:hx + hw].copy()
    mask = head_ellipse_mask(hw, hh)
    return head, mask, (hx, hy, hw, hh)


def swap_head_onto_frame(frame_bgr, src_head_bgr, src_mask, target_head_box, blend=0.92):
    tx, ty, tw, th = target_head_box
    fh, fw = frame_bgr.shape[:2]
    if tw <= 10 or th <= 10:
        return frame_bgr
    resized = cv2.resize(src_head_bgr, (tw, th), interpolation=cv2.INTER_LINEAR)
    mask_resized = cv2.resize(src_mask, (tw, th), interpolation=cv2.INTER_LINEAR)
    target_region = frame_bgr[ty:ty + th, tx:tx + tw]
    if target_region.shape[:2] != resized.shape[:2]:
        return frame_bgr
    matched = color_match_lab(resized, target_region)
    _, binary = cv2.threshold(mask_resized, 10, 255, cv2.THRESH_BINARY)
    if cv2.countNonZero(binary) < 100:
        return frame_bgr
    center = (tx + tw // 2, ty + th // 2)
    try:
        cloned = cv2.seamlessClone(matched, frame_bgr, binary, center, cv2.NORMAL_CLONE)
        m_full = np.zeros((fh, fw), dtype=np.float32)
        m_full[ty:ty + th, tx:tx + tw] = mask_resized.astype(np.float32) / 255.0
        m_full = cv2.GaussianBlur(m_full, (21, 21), 0)
        alpha = (m_full * blend)[..., None]
        out = (cloned.astype(np.float32) * alpha + frame_bgr.astype(np.float32) * (1 - alpha))
        return np.clip(out, 0, 255).astype(np.uint8)
    except cv2.error:
        alpha = (mask_resized.astype(np.float32) / 255.0 * blend)[..., None]
        roi = frame_bgr[ty:ty + th, tx:tx + tw].astype(np.float32)
        blended = matched.astype(np.float32) * alpha + roi * (1 - alpha)
        out = frame_bgr.copy()
        out[ty:ty + th, tx:tx + tw] = np.clip(blended, 0, 255).astype(np.uint8)
        return out


def try_insightface_swapper():
    """Return swapper objects if insightface + model are available, else None."""
    try:
        import insightface
        from insightface.app import FaceAnalysis
        model_paths = [
            os.path.expanduser("~/.insightface/models/inswapper_128.onnx"),
            "models/inswapper_128.onnx",
            "/tmp/inswapper_128.onnx",
        ]
        model = next((p for p in model_paths if os.path.exists(p)), None)
        if model is None:
            return None
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        swapper = insightface.model_zoo.get_model(model, providers=["CPUExecutionProvider"])
        return app, swapper
    except Exception:
        return None


def process_video(source_image_path, target_video_path, output_path,
                  progress_cb=None, top=0.85, side=0.30, bottom=0.20, blend=0.92,
                  max_frames=None, max_dim=720):
    """Swap full head from source image onto every face in target video."""
    src = cv2.imread(source_image_path, cv2.IMREAD_COLOR)
    if src is None:
        raise ValueError("Could not read source image.")
    sh, sw = src.shape[:2]
    scale = min(1.0, 800 / max(sh, sw))
    if scale < 1.0:
        src = cv2.resize(src, (int(sw * scale), int(sh * scale)))

    ai = try_insightface_swapper()
    if ai is not None:
        return _process_with_insightface(ai, src, target_video_path, output_path, progress_cb, max_frames, max_dim)

    src_head, src_mask, _ = extract_source_head(src, top, side, bottom)

    cap = cv2.VideoCapture(target_video_path)
    if not cap.isOpened():
        raise ValueError("Could not open target video.")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    ow = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    oh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vscale = min(1.0, max_dim / max(ow, oh)) if max(ow, oh) > 0 else 1.0
    nw, nh = max(2, int(ow * vscale)), max(2, int(oh * vscale))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (nw, nh))
    if not writer.isOpened():
        raise RuntimeError("Could not open video writer (mp4v).")

    idx, done = 0, 0
    faces_found = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if max_frames and idx >= max_frames:
            break
        if vscale < 1.0:
            frame = cv2.resize(frame, (nw, nh))
        faces = detect_faces_bgr(frame)
        if len(faces) > 0:
            box = largest_box(faces)
            fh, fw = frame.shape[:2]
            head_box = expand_to_head(box, fw, fh, top, side, bottom)
            frame = swap_head_onto_frame(frame, src_head, src_mask, head_box, blend)
            faces_found += 1
        writer.write(frame)
        idx += 1
        done += 1
        if progress_cb:
            progress_cb(done, total if total > 0 else done + 1, faces_found)
    cap.release()
    writer.release()
    if idx == 0:
        raise ValueError("Target video has no readable frames.")
    return {"frames": idx, "faces_found": faces_found, "engine": "opencv-full-head"}


def _process_with_insightface(ai, src, target_video_path, output_path, progress_cb, max_frames, max_dim):
    app, swapper = ai
    src_faces = app.get(src)
    if not src_faces:
        raise ValueError("No face found in source image.")
    src_face = max(src_faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    cap = cv2.VideoCapture(target_video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    ow = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); oh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vscale = min(1.0, max_dim / max(ow, oh)) if max(ow, oh) > 0 else 1.0
    nw, nh = max(2, int(ow * vscale)), max(2, int(oh * vscale))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    writer = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (nw, nh))
    idx = faces_found = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if max_frames and idx >= max_frames:
            break
        if vscale < 1.0:
            frame = cv2.resize(frame, (nw, nh))
        faces = app.get(frame)
        if faces:
            target = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            frame = swapper.get(frame, target, src_face, paste_back=True)
            faces_found += 1
        writer.write(frame)
        idx += 1
        if progress_cb:
            progress_cb(idx, total if total > 0 else idx + 1, faces_found)
    cap.release(); writer.release()
    return {"frames": idx, "faces_found": faces_found, "engine": "insightface-inswapper"}
