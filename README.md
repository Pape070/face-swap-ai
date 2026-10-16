# Face Swap AI — HeadSwap Studio

Swap a **full head** — face + forehead + hair + jaw — from a photo onto every
frame of a video. Three editions, one engine (`face_swap.py`):

| Edition | Folder | Run |
|---|---|---|
| 🌐 Web app | repo root (`app.py` + `static/`) | `pip install -r requirements.txt && python app.py` → http://localhost:3000 |
| 🖥 Desktop | `desktop/` | standalone `HeadSwapStudio` executable (CI artifacts) or `python desktop/faceswap_desktop.py` |
| 📱 Android | `android/` | Point the app at your server, build APK via CI |

## How it works

YuNet face detection (`cv2.FaceDetectorYN`, model auto-downloads on first run)
→ expand each face box into a full-head box (scalp/width sliders) → LAB
color-match the source head to each frame → `seamlessClone` + feathered head
mask. If InsightFace + `inswapper_128.onnx` is present, it auto-upgrades to
neural swapping.

## Web app API

- `GET /` — uploader UI (includes one-click demo)
- `POST /api/swap` — multipart `source` (image) + `target` (video), returns `job_id`
- `GET /api/progress/<job>` — `{status, percent, faces, engine, …}`
- `GET /api/result/<job>` / `GET /api/download/<job>` — swapped MP4

## Repo layout

```
app.py  face_swap.py  static/  demo/   # web edition + demo media
desktop/                               # Tkinter desktop edition
android/                               # Kotlin WebView Android edition
.github/workflows/android.yml          # CI: builds debug APK
.github/workflows/desktop.yml          # CI: builds desktop executables (Linux/Windows/macOS)
```

## Test report (latest)

- Engine units: detection, head-box expansion, mask, color-match, blank-image error — pass
- API: health, routes, demo assets, UI tokens — pass
- Live swap incl. 4-thread detection race check — pass
- Demo: 150 frames, faces swapped in 145 — see `demo/result.mp4`

## Ethics

Only swap faces you have consent to use. Don't create misleading videos of
real people. Check the Unsplash/Pexels licenses (`demo/SOURCES.txt`) before
publishing demo media.
