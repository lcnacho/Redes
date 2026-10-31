#!/usr/bin/env python3
"""Control de calidad de un render antes de entregarlo.

Uso:
  python3 scripts/qa.py salida/final_A.mp4 [--edl _work/variante_A/edl.json]

Revisa formato, duración, volumen (LUFS), cuadros negros y congelados no buscados, y arma
una hoja de contacto (qa_final_A.jpg) con cuadros del hook y del resto para que Claude la mire.
Escribe qa_final_A.json al lado del video. Sale con código 1 si algo falla.
"""
import argparse
import json
import os
import re
import subprocess


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--edl")
    ap.add_argument("--escuchar", action="store_true",
                    help="transcribe el render para revisar que los cortes no dejen sílabas sueltas")
    args = ap.parse_args()
    v = args.video
    base = os.path.splitext(v)[0].replace("final_", "qa_final_")
    problems, info = [], {}

    pr = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                         "stream=codec_type,codec_name,width,height,r_frame_rate,bit_rate:format=duration,bit_rate",
                         "-of", "json", v]).stdout)
    vs = next(s for s in pr["streams"] if s["codec_type"] == "video")
    aus = [s for s in pr["streams"] if s["codec_type"] == "audio"]
    dur = float(pr["format"]["duration"])
    info.update(width=vs["width"], height=vs["height"], fps=vs["r_frame_rate"], vcodec=vs["codec_name"],
                duration=round(dur, 2), mbps=round(int(pr["format"].get("bit_rate", 0)) / 1e6, 1))
    if (vs["width"], vs["height"]) != (1080, 1920):
        problems.append(f"resolución {vs['width']}x{vs['height']}, se esperaba 1080x1920")
    if vs["codec_name"] != "h264" or not aus or aus[0]["codec_name"] != "aac":
        problems.append("códecs: se esperaba H.264 + AAC")
    if vs["r_frame_rate"] not in ("30/1", "30000/1001"):
        problems.append(f"fps {vs['r_frame_rate']}")
    if not 8 <= dur <= 90:
        problems.append(f"duración {dur:.1f} s fuera de rango para un short")

    ebu = run(["ffmpeg", "-nostats", "-i", v, "-filter_complex", "ebur128=peak=true", "-f", "null", "-"]).stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", ebu)
    if m:
        lufs = float(m[-1])
        info["lufs"] = lufs
        if not -17 <= lufs <= -11:
            problems.append(f"volumen {lufs} LUFS (objetivo -14)")

    bd = run(["ffmpeg", "-nostats", "-i", v, "-vf", "blackdetect=d=0.25:pix_th=0.08", "-an", "-f", "null", "-"]).stderr
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)
    fz = run(["ffmpeg", "-nostats", "-i", v, "-vf", "freezedetect=n=0.002:d=1.5", "-an", "-f", "null", "-"]).stderr
    freezes = re.findall(r"freeze_start: ([\d.]+)", fz)
    intended = []
    if args.edl:
        edl = json.load(open(args.edl))
        intended = [s["out_start"] for s in edl["segments"] if s["kind"] == "freeze"]
        info["hook_end"] = edl.get("hook_end")
        info["estilo"] = edl.get("estilo")
    info["black"] = blacks
    info["freezes"] = freezes
    for s, e in blacks:
        if info.get("estilo") == "pantalla-negra" and float(s) < 0.1 and float(e) <= (info.get("hook_end") or 0) + 0.3:
            continue  # el fondo negro del hook es buscado
        problems.append(f"cuadros negros {s}-{e} s (revisar: ¿es el estilo pantalla negra?)")
    for s in freezes:
        if not any(abs(float(s) - t) < 0.5 for t in intended):
            problems.append(f"imagen congelada desde {s} s")

    # hoja de contacto: 4 cuadros del hook y 8 repartidos
    times = [0.15, 0.8, 1.6, 2.6] + [3 + i * (dur - 3.5) / 7 for i in range(8)]
    tiles = []
    for i, t in enumerate(times):
        p = f"{base}_{i:02d}.jpg"
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1",
             "-vf", "scale=270:480,drawtext=text='%.1fs':x=8:y=8:fontsize=22:fontcolor=yellow:box=1:boxcolor=black@0.6" % t,
             p])
        tiles.append(p)
    inputs = sum([["-i", p] for p in tiles], [])
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex",
         "".join(f"[{i}]" for i in range(len(tiles))) + f"xstack=inputs={len(tiles)}:grid=6x2", f"{base}.jpg"])
    for p in tiles:
        os.remove(p)
    info["contact_sheet"] = f"{base}.jpg"

    # lo que realmente se escucha: se transcribe el render para compararlo con el plan
    if args.escuchar:
        tmp = f"{base}_words.json"
        r = run(["python3", os.path.join(os.path.dirname(__file__), "transcribe.py"), v, "-o", tmp])
        if r.returncode == 0:
            info["se_escucha"] = " ".join(w["text"] for w in json.load(open(tmp))["words"])
            os.remove(tmp)

    info["problems"] = problems
    json.dump(info, open(f"{base}.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(info, indent=1, ensure_ascii=False))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
