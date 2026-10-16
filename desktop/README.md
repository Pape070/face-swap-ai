# HeadSwap Studio — Desktop edition

Native Tkinter GUI around the same `face_swap.py` engine as the web app.
No server or browser needed.

## Run from source

```bash
pip install -r ../requirements.txt
python faceswap_desktop.py
```

First run downloads the YuNet face model (~300 KB) into `../models/`.

## Build a standalone executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name HeadSwapStudio \
  --add-data "../models:models" faceswap_desktop.py
# dist/HeadSwapStudio  (add the models/ folder next to it if excluded)
```

Only swap faces you have consent to use.
