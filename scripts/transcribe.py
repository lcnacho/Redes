#!/usr/bin/env python3
"""Transcribe un video/audio y devuelve tiempos por palabra.

Uso:
  python3 scripts/transcribe.py camara.mp4 -o words.json
  python3 scripts/transcribe.py camara.mp4 -o words.json --engine whisper

Motores:
  parakeet  (default) NVIDIA Parakeet TDT 0.6B v3 via sherpa-onnx. 25 idiomas europeos
            (inglés y español incluidos), detecta el idioma solo.
            El modelo se baja de GitHub, así que funciona con red limitada.
            Conserva repeticiones ("you want you want"), útil para detectar tomas repetidas.
  whisper   faster-whisper large-v3-turbo con word_timestamps. Multilenguaje.
            Necesita acceso a huggingface.co (red "Full").

Salida (words.json):
  {"engine", "language", "duration", "words": [{"id","text","start","end"}]}
"""
import argparse
import json
import os
import subprocess
import sys

SR = 16000
MODELS_DIR = os.environ.get("EDICION_MODELS", os.path.expanduser("~/.cache/edicion/models"))
PARAKEET = os.path.join(MODELS_DIR, "sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8")
VAD = os.path.join(MODELS_DIR, "silero_vad.onnx")


def load_audio(path):
    import numpy as np
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
        capture_output=True, check=True).stdout
    return np.frombuffer(pcm, dtype=np.float32)


def media_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def speech_chunks(audio, max_len=20.0):
    """Segmentos de voz (silero VAD) de como máximo max_len segundos, en muestras."""
    import sherpa_onnx
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = VAD
    cfg.silero_vad.min_silence_duration = 0.25
    cfg.silero_vad.min_speech_duration = 0.15
    cfg.silero_vad.max_speech_duration = max_len
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    chunks = []
    w = cfg.silero_vad.window_size
    for i in range(0, len(audio), w):
        vad.accept_waveform(audio[i:i + w])
        while not vad.empty():
            chunks.append((vad.front.start, len(vad.front.samples)))
            vad.pop()
    vad.flush()
    while not vad.empty():
        chunks.append((vad.front.start, len(vad.front.samples)))
        vad.pop()
    return chunks


def tokens_to_words(tokens, starts, durs, offset):
    """Parakeet devuelve piezas BPE; una pieza que empieza con espacio abre palabra nueva.
    La puntuación se pega a la palabra anterior."""
    words = []
    for tok, st, du in zip(tokens, starts, durs):
        st, en = offset + st, offset + st + max(du, 0.04)
        piece = tok.strip()
        if not piece:
            continue
        new_word = tok.startswith(" ") or not words
        # un número pegado a una palabra ("como6") es una palabra nueva
        if not new_word and piece[0].isdigit() and words[-1]["text"][-1:].isalpha():
            new_word = True
        if not new_word or (piece and all(not c.isalnum() for c in piece) and words):
            words[-1]["text"] += piece
            words[-1]["end"] = max(words[-1]["end"], en)
        else:
            words.append({"text": piece, "start": st, "end": en})
    return words


def run_parakeet(path):
    import numpy as np
    import sherpa_onnx
    if not os.path.isdir(PARAKEET):
        sys.exit(f"Falta el modelo en {PARAKEET}. Corré scripts/setup.sh")
    audio = load_audio(path)
    rec = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=f"{PARAKEET}/encoder.int8.onnx", decoder=f"{PARAKEET}/decoder.int8.onnx",
        joiner=f"{PARAKEET}/joiner.int8.onnx", tokens=f"{PARAKEET}/tokens.txt",
        model_type="nemo_transducer", num_threads=os.cpu_count() or 4)
    words = []
    for start, n in speech_chunks(audio):
        # medio segundo de margen a cada lado para no comer bordes de palabras
        a = max(0, start - SR // 4)
        b = min(len(audio), start + n + SR // 4)
        s = rec.create_stream()
        s.accept_waveform(SR, np.ascontiguousarray(audio[a:b]))
        rec.decode_stream(s)
        r = s.result
        words += tokens_to_words(r.tokens, r.timestamps, r.durations, a / SR)
    return words, "auto"


def run_whisper(path, language):
    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3-turbo", device="cpu", compute_type="int8")
    segs, info = model.transcribe(path, language=language, word_timestamps=True,
                                  vad_filter=True, condition_on_previous_text=False)
    words = []
    for seg in segs:
        for w in seg.words or []:
            words.append({"text": w.word.strip(), "start": w.start, "end": w.end})
    return words, info.language


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--engine", choices=["parakeet", "whisper"], default="parakeet")
    ap.add_argument("--language", default=None, help="solo para whisper (default: detecta)")
    args = ap.parse_args()

    if args.engine == "parakeet":
        words, lang = run_parakeet(args.media)
    else:
        words, lang = run_whisper(args.media, args.language)

    dur = media_duration(args.media)
    out = []
    for i, w in enumerate(words):
        if w["start"] >= dur:
            continue
        out.append({"id": f"w{i}", "text": w["text"], "start": round(w["start"], 3),
                    "end": round(min(w["end"], dur), 3)})
    json.dump({"engine": args.engine, "language": lang, "duration": round(dur, 3), "words": out},
              open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(out)} palabras, {dur:.1f} s -> {args.out}")


if __name__ == "__main__":
    main()
