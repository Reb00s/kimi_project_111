#!/usr/bin/env python3
"""Конвертер текста в аудиофайл через TTS-сервис стенда (openedai-speech / XTTS v2).

Использование:
  python3 scripts/tts_txt2mp3.py input.txt output.mp3 [--voice alloy] [--url http://localhost:8000]

Логика: текст режется на фрагменты ~MAX_CHARS на границах абзацев, каждый фрагмент
озвучивается (модель tts-1-hd = XTTS v2), куски склеиваются ffmpeg в один mp3.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

MAX_CHARS = 1200          # длина фрагмента; XTTS уверенно озвучивает такой объём
MODEL = "tts-1-hd"        # XTTS v2 (русский). НЕ 'tts-1' — это piper без русского.


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


def synth_chunk(url: str, voice: str, text: str, out_file: Path) -> None:
    payload = json.dumps({"model": MODEL, "voice": voice, "input": text}).encode()
    req = urllib.request.Request(
        f"{url}/v1/audio/speech",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        out_file.write_bytes(resp.read())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", type=Path, help="текстовый файл (utf-8)")
    ap.add_argument("output", type=Path, help="куда сохранить mp3")
    ap.add_argument("--voice", default="alloy")
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()

    text = args.input.read_text(encoding="utf-8")
    chunks = split_text(text)
    print(f"Фрагментов: {len(chunks)}")

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        list_file = tmpdir / "concat.txt"
        with list_file.open("w") as lf:
            for i, chunk in enumerate(chunks):
                part = tmpdir / f"part_{i:04d}.mp3"
                print(f"[{i+1}/{len(chunks)}] {len(chunk)} симв...", flush=True)
                synth_chunk(args.url, args.voice, chunk, part)
                lf.write(f"file '{part}'\n")

        print("Склейка ffmpeg...")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c", "copy", str(args.output)],
            check=True,
        )

    size_mb = args.output.stat().st_size / 1024 / 1024
    print(f"Готово: {args.output} ({size_mb:.1f} МБ)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
