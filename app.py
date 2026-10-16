import os, uuid, threading, time
from flask import Flask, request, jsonify, send_from_directory, send_file

from face_swap import process_video

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE, "uploads")
OUTPUT_DIR = os.path.join(BASE, "outputs")
STATIC_DIR = os.path.join(BASE, "static")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
jobs = {}
jobs_lock = threading.Lock()


def set_job(jid, **kw):
    with jobs_lock:
        jobs[jid].update(kw)


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/swap", methods=["POST"])
def swap():
    if "source" not in request.files or "target" not in request.files:
        return jsonify({"error": "Upload both a source image and a target video."}), 400
    src = request.files["source"]
    tgt = request.files["target"]
    if src.filename == "" or tgt.filename == "":
        return jsonify({"error": "Empty file name."}), 400

    jid = uuid.uuid4().hex[:12]
    src_path = os.path.join(UPLOAD_DIR, f"{jid}_source_{src.filename}")
    tgt_path = os.path.join(UPLOAD_DIR, f"{jid}_target_{tgt.filename}")
    out_path = os.path.join(OUTPUT_DIR, f"{jid}_swapped.mp4")
    src.save(src_path); tgt.save(tgt_path)

    try:
        top = float(request.form.get("scalp", 0.85))
        side = float(request.form.get("side", 0.30))
        blend = float(request.form.get("blend", 0.92))
    except ValueError:
        top, side, blend = 0.85, 0.30, 0.92
    top = min(1.4, max(0.2, top)); side = min(0.8, max(0.0, side)); blend = min(1.0, max(0.3, blend))

    with jobs_lock:
        jobs[jid] = {"status": "queued", "progress": 0, "total": 1,
                     "faces": 0, "error": None, "result": None, "engine": None,
                     "created": time.time()}

    def run():
        set_job(jid, status="processing")
        def cb(done, total, faces):
            set_job(jid, progress=done, total=max(1, total), faces=faces)
        try:
            info = process_video(src_path, tgt_path, out_path, progress_cb=cb,
                                 top=top, side=side, blend=blend)
            set_job(jid, status="done", progress=info["frames"], total=max(1, info["frames"]),
                    faces=info["faces_found"], result=f"{jid}_swapped.mp4", engine=info["engine"])
        except Exception as e:
            set_job(jid, status="error", error=str(e))

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"job_id": jid})


@app.route("/api/progress/<jid>")
def progress(jid):
    with jobs_lock:
        job = jobs.get(jid)
    if not job:
        return jsonify({"error": "Unknown job"}), 404
    pct = round(100 * job["progress"] / max(1, job["total"]), 1)
    return jsonify({"status": job["status"], "progress": job["progress"],
                    "total": job["total"], "percent": pct, "faces": job["faces"],
                    "error": job["error"], "result": job["result"], "engine": job["engine"]})


@app.route("/api/result/<jid>")
def result(jid):
    with jobs_lock:
        job = jobs.get(jid)
    if not job or not job.get("result"):
        return jsonify({"error": "Result not ready"}), 404
    return send_from_directory(OUTPUT_DIR, job["result"], mimetype="video/mp4",
                               as_attachment=False, download_name="face-swap.mp4")


@app.route("/api/download/<jid>")
def download(jid):
    with jobs_lock:
        job = jobs.get(jid)
    if not job or not job.get("result"):
        return jsonify({"error": "Result not ready"}), 404
    return send_from_directory(OUTPUT_DIR, job["result"], mimetype="video/mp4",
                               as_attachment=True, download_name="face-swap.mp4")


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, threaded=True)
