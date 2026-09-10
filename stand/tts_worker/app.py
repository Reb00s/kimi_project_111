"""tts-worker: очередь озвучки текста через openedai-speech (XTTS v2).

FastAPI + фоновый поток:
- POST /jobs          — поставить текст в очередь -> {"job_id": ...}
- GET  /jobs/{job_id} — статус / прогресс / ссылка на файл
- GET  /files/{job_id}.mp3 — готовый mp3
"""
import json
import os
import subprocess
import tempfile
import threading
import time
import urllib.request
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

SPEECH_URL = os.environ.get("SPEECH_URL", "http://speech:8000")
LAN_BASE_URL = os.environ.get("LAN_BASE_URL", "http://localhost:8001")
FILES_DIR = Path(os.environ.get("FILES_DIR", "/data/files"))
FILE_TTL_SEC = 24 * 3600  # хранить готовые файлы и задачи 24 часа

MAX_CHARS = 1200   # длина фрагмента; XTTS уверенно озвучивает такой объём
MODEL = "tts-1-hd"  # XTTS v2 (русский). НЕ 'tts-1' — это piper без русского.

app = FastAPI(title="tts-worker")

_lock = threading.Lock()
_jobs: dict[str, dict] = {}  # job_id -> {"status", "progress", "url", "error"}


class JobRequest(BaseModel):
    text: str
    voice: str = "alloy"


def split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) + 1 <= max_chars:
            current = f"{current}\n{p}" if current else p
        else:
            if current:
                chunks.append(current)
            # абзац сам длиннее лимита — режем на предложения
            while len(p) > max_chars:
                cut = p.rfind(". ", 0, max_chars)
                cut = cut + 1 if cut > max_chars // 2 else max_chars
                chunks.append(p[:cut].strip())
                p = p[cut:].strip()
            current = p
    if current:
        chunks.append(current)
    return chunks


def synth_chunk(voice: str, text: str, out_file: Path) -> None:
    payload = json.dumps({"model": MODEL, "voice": voice, "input": text}).encode()
    req = urllib.request.Request(
        f"{SPEECH_URL}/v1/audio/speech",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        out_file.write_bytes(resp.read())


def process_job(job_id: str, text: str, voice: str) -> None:
    try:
        chunks = split_text(text)
        if not chunks:
            raise ValueError("после нарезки не осталось текста")

        def update(done: int) -> None:
            with _lock:
                _jobs[job_id]["progress"] = {"done": done, "total": len(chunks)}
                _jobs[job_id]["status"] = "processing"

        out_file = FILES_DIR / f"{job_id}.mp3"
        with tempfile.TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            list_file = tmpdir / "concat.txt"
            with list_file.open("w") as lf:
                for i, chunk in enumerate(chunks):
                    part = tmpdir / f"part_{i:04d}.mp3"
                    synth_chunk(voice, chunk, part)
                    lf.write(f"file '{part}'\n")
                    update(i + 1)

            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                 "-i", str(list_file), "-c", "copy", str(out_file)],
                check=True,
            )

        with _lock:
            _jobs[job_id]["status"] = "done"
            _jobs[job_id]["url"] = f"/files/{job_id}.mp3"
            _jobs[job_id]["finished_at"] = time.time()
    except Exception as exc:  # noqa: BLE001 — любую ошибку отдаём в статусе задачи
        with _lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["error"] = str(exc)
            _jobs[job_id]["finished_at"] = time.time()


def worker_loop() -> None:
    while True:
        with _lock:
            job = next(
                (j for j in _jobs.values() if j["status"] == "queued"),
                None,
            )
        if job is None:
            time.sleep(0.5)
            continue
        process_job(job["id"], job["text"], job["voice"])


def cleanup_old_files() -> None:
    """При старте удалить файлы и задачи старше 24 часов."""
    now = time.time()
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    for f in FILES_DIR.glob("*.mp3"):
        if now - f.stat().st_mtime > FILE_TTL_SEC:
            f.unlink(missing_ok=True)
    with _lock:
        stale = [
            jid for jid, j in _jobs.items()
            if j.get("finished_at") and now - j["finished_at"] > FILE_TTL_SEC
        ]
        for jid in stale:
            del _jobs[jid]


@app.on_event("startup")
def on_startup() -> None:
    cleanup_old_files()
    threading.Thread(target=worker_loop, daemon=True).start()


@app.post("/jobs")
def create_job(req: JobRequest) -> dict:
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "text": req.text,
            "voice": req.voice or "alloy",
            "status": "queued",
            "progress": None,
            "url": None,
            "error": None,
            "finished_at": None,
        }
    return {"job_id": job_id}


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return {
            "status": job["status"],
            "progress": job["progress"],
            "url": job["url"],
            "error": job["error"],
        }


@app.get("/files/{job_id}.mp3")
def get_file(job_id: str) -> FileResponse:
    path = FILES_DIR / f"{job_id}.mp3"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path, media_type="audio/mpeg", filename=f"{job_id}.mp3")
