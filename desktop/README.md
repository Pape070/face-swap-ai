# HeadSwap Studio — Desktop edition

Native Tkinter GUI around the same `face_swap.py` engine as the web app.
No server or browser needed.

## Run from source

```bash
pip install -r ../requirements.txt
python faceswap_desktop.py
```

First run downloads the YuNet face model (~300 KB) into `../models/`.

## Headless mode (no display needed)

```bash
python faceswap_desktop.py --version
python faceswap_desktop.py --cli photo.jpg video.mp4 out.mp4
```

## Standalone executable

Prebuilt binaries for Linux, Windows and macOS are attached to every
`desktop-exe` CI run (Actions → Artifacts: `HeadSwapStudio-<os>`).

Build locally:

```bash
pip install -r ../requirements.txt pyinstaller
pyinstaller --noconfirm desktop/HeadSwapStudio.spec
# → dist/HeadSwapStudio  (single file, YuNet model bundled inside)
```

The frozen app finds its model in this order: bundled `models/` → folder
next to the executable → `~/.headswap_studio/models/` (auto-download).

Only swap faces you have consent to use.
