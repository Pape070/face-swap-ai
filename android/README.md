# HeadSwap Studio — Android edition

Native Kotlin shell (WebView + file-chooser wiring) around the HeadSwap web
app. Heavy video processing stays on the server; the phone provides the
camera-roll picker, upload UI, progress and result playback.

## 1 · Start the server (on your computer or a host)

```bash
pip install -r ../requirements.txt
python ../app.py   # listens on http://0.0.0.0:3000
```

## 2 · Point the app at it

On first launch the app asks for the server URL:
- Same Wi-Fi phone → PC: `http://<PC-LAN-IP>:3000` (e.g. `http://192.168.1.5:3000`)
- Emulator → host PC: `http://10.0.2.2:3000` (default)

## 3 · Build the APK

```bash
cd android
gradle :app:assembleDebug
# app/build/outputs/apk/debug/app-debug.apk
```

Or push to GitHub — `.github/workflows/android.yml` builds the debug APK on
every push (see the Actions tab for the artifact).

Only swap faces you have consent to use.
