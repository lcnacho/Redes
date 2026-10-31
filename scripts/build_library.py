#!/usr/bin/env python3
"""Arma el kit inicial de la librería de recursos con lo que el entorno cloud puede conseguir solo.

Uso:
  python3 scripts/build_library.py ~/.cache/edicion/kit      # arma el kit en esa carpeta
  rclone copy ~/.cache/edicion/kit "gdrive:Edicion automatica/_Recursos"   # lo sube (o drive.sh)

Qué arma (todo con uso comercial permitido y sin atribución obligatoria):
  sonidos/         efectos sintetizados acá (propios, sin licencia de terceros)
  musica/          2 bases sintetizadas, PROVISORIAS hasta tener música de Pixabay u otra librería
  overlays/        grano y light leaks generados con ffmpeg (propios)
  luts/            3 LUT .cube generados (propios)
  iconos/          Lucide (ISC), desde npm
  fuentes/         Anton, Bebas Neue, Montserrat (OFL), desde npm (@fontsource)
  animaciones/     reproductor lottie-web (MIT); las animaciones .json se agregan a mano
  catalogo.json, licencias.md

Lo que NO puede bajar (sitios bloqueados en el entorno): Pixabay, Mixkit, Kenney, Freesound,
LottieFiles, YouTube. Esos se suben a mano a _Recursos/ (ver library/README.md).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

SR = 48000
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.cache/edicion/kit"))
HERE = os.path.dirname(os.path.abspath(__file__))
catalog = {"sonidos": [], "musica": [], "overlays": [], "luts": [], "iconos": [], "fuentes": [],
           "animaciones": []}
lic = []


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], axis=1) if x.ndim == 1 else x
    with tempfile.NamedTemporaryFile(suffix=".f32") as t:
        st.astype(np.float32).tofile(t.name)
        ff("-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", t.name, path)


# ------------------------------------------------------------------ sonidos

def sounds():
    d = os.path.join(OUT, "sonidos")
    os.makedirs(d, exist_ok=True)
    # los 6 básicos que usa build.py por nombre
    subprocess.run(["bash", os.path.join(HERE, "gen_sfx.sh"), d], check=True, capture_output=True)
    t = lambda dur: np.arange(int(SR * dur)) / SR
    rng = np.random.default_rng(7)

    def noise_sweep(dur, f0, f1, curve=1.0):
        """Ruido filtrado con un pasabanda que barre de f0 a f1 (whoosh)."""
        n = rng.standard_normal(int(SR * dur))
        spec = np.fft.rfft(n)
        out = np.zeros_like(n)
        frames = 24
        L = len(n) // frames
        for k in range(frames):
            seg = n[k * L:(k + 1) * L]
            f = f0 + (f1 - f0) * (k / frames) ** curve
            S = np.fft.rfft(seg)
            freqs = np.fft.rfftfreq(len(seg), 1 / SR)
            S *= np.exp(-((freqs - f) / (f * 0.6)) ** 2)
            out[k * L:(k + 1) * L] = np.fft.irfft(S, len(seg))
        del spec
        env = np.sin(np.pi * np.linspace(0, 1, len(out))) ** 1.5
        return out * env / (np.abs(out).max() + 1e-9) * 0.8

    extra = {
        "whoosh-02": (noise_sweep(0.35, 800, 6000), "transición rápida, brillante"),
        "whoosh-03": (noise_sweep(0.7, 2500, 300, 0.7), "transición lenta y grave (bajada)"),
        "pop-02": (0.8 * np.sin(2 * np.pi * (300 + 2500 * t(0.1)) * t(0.1)) * np.exp(-45 * t(0.1)), "pop grave para tarjetas"),
        "pop-03": (0.6 * np.sin(2 * np.pi * 1800 * t(0.06)) * np.exp(-70 * t(0.06)), "pop agudo corto"),
        "click-01": (np.r_[rng.standard_normal(90) * np.exp(-np.arange(90) / 12), np.zeros(800)] * 0.8, "click de interfaz"),
        "click-02": (0.7 * np.sin(2 * np.pi * 3200 * t(0.03)) * np.exp(-150 * t(0.03)), "click metálico"),
        "impacto-02": (0.9 * np.sin(2 * np.pi * 45 * t(1.6)) * np.exp(-2.5 * t(1.6))
                       + 0.35 * np.r_[rng.standard_normal(int(SR * 0.08)) * np.exp(-np.arange(int(SR * 0.08)) / 900),
                                      np.zeros(int(SR * 1.52))], "golpe grave con ataque (hooks, remates)"),
        "riser-02": (noise_sweep(2.0, 200, 8000, 2.0) * np.linspace(0.2, 1, int(SR * 2.0)), "riser de ruido, antes de un giro"),
        "ding": (0.5 * (np.sin(2 * np.pi * 1568 * t(0.9)) + 0.5 * np.sin(2 * np.pi * 2349 * t(0.9))) * np.exp(-5 * t(0.9)),
                 "acierto, dato correcto"),
        "error": (0.5 * np.sign(np.sin(2 * np.pi * 180 * t(0.35))) * np.exp(-6 * t(0.35)) * 0.6, "error, mito, 'falso'"),
    }
    # glitch: cortes de ruido y tonos al azar (determinista)
    g = np.zeros(int(SR * 0.4))
    for k in range(8):
        a = int(rng.integers(0, len(g) - 2000))
        L = int(rng.integers(400, 2000))
        g[a:a + L] += (rng.standard_normal(L) * 0.5 if k % 2 else 0.5 * np.sign(np.sin(2 * np.pi * rng.integers(200, 2000) * np.arange(L) / SR)))
    extra["glitch-01"] = (g, "glitch digital corto")

    # sonidos de transición (los usa build.py en las transiciones: whip, flash, zoom, glitch, light leak)
    extra["whip"] = (noise_sweep(0.22, 1500, 9000, 0.6) * 1.1, "transición whip (latigazo de cámara)")
    up = noise_sweep(0.6, 300, 7000, 1.6)
    extra["swoosh-up"] = (up * np.linspace(0.3, 1, len(up)), "zoom hacia adentro, subida")
    hit = np.r_[noise_sweep(0.3, 600, 5000), np.zeros(int(SR * 1.0))]
    hit[int(SR * 0.27):] += (0.9 * np.sin(2 * np.pi * 50 * t(1.03)) * np.exp(-3.5 * t(1.03)))[:len(hit) - int(SR * 0.27)]
    extra["hit-whoosh"] = (hit / np.abs(hit).max() * 0.9, "whoosh que remata en golpe (zoom-through, remate)")
    rum = rng.standard_normal(int(SR * 0.6))
    rum = np.convolve(rum, np.ones(400) / 400, mode="same") * 8 * np.exp(-5 * t(0.6))
    extra["rumble"] = (rum, "temblor grave para el shake de cámara")
    fl = rng.standard_normal(int(SR * 0.5))
    fl = np.diff(np.r_[0, fl]) * np.exp(-9 * t(0.5)) * 0.5 + 0.25 * np.sin(2 * np.pi * 2637 * t(0.5)) * np.exp(-7 * t(0.5))
    extra["flash"] = (fl, "destello (flash blanco, light leak)")
    g2 = np.zeros(int(SR * 0.25))
    for k in range(12):
        a = int(rng.integers(0, len(g2) - 600))
        L = int(rng.integers(150, 600))
        g2[a:a + L] = 0.6 * np.sign(np.sin(2 * np.pi * rng.integers(80, 4000) * np.arange(L) / SR))
    extra["glitch-02"] = (g2, "glitch para la transición glitch")
    for name, (x, use) in extra.items():
        write_wav(os.path.join(d, f"{name}.wav"), x)
    base = {"whoosh": "transición", "pop": "texto que aparece", "impacto": "golpe del hook",
            "riser": "antes de un giro", "tick": "ítem de lista", "scratch": "hook congelado"}
    for name, use in list(base.items()) + [(k, v[1]) for k, v in extra.items()]:
        p = f"sonidos/{name}.wav"
        dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                    os.path.join(OUT, p)], capture_output=True, text=True).stdout)
        catalog["sonidos"].append({"archivo": p, "nombre": name, "uso": use, "duracion": round(dur, 2),
                                   "licencia": "propio (sintetizado)"})
    lic.append("| sonidos/*.wav | Sintetizados con scripts/gen_sfx.sh y build_library.py | Propios, sin restricciones |")


# ------------------------------------------------------------------ música provisoria

def music():
    d = os.path.join(OUT, "musica")
    os.makedirs(d, exist_ok=True)
    rng = np.random.default_rng(3)

    def note(f, dur, kind="keys"):
        tt = np.arange(int(SR * dur)) / SR
        if kind == "keys":   # piano eléctrico simple: fundamental + armónicos con caída
            x = sum(a * np.sin(2 * np.pi * f * h * tt) for h, a in ((1, 1), (2, .35), (3, .12), (4, .06)))
            return x * np.exp(-2.2 * tt) * (1 - np.exp(-80 * tt))
        if kind == "bass":
            return (np.sin(2 * np.pi * f * tt) + .3 * np.sin(2 * np.pi * 2 * f * tt)) * np.exp(-1.5 * tt) * (1 - np.exp(-60 * tt))
        if kind == "pad":
            x = sum(np.sin(2 * np.pi * f * (1 + dt) * tt) for dt in (-0.004, 0, 0.004)) / 3
            env = np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)
            return x * env

    def kick():
        tt = np.arange(int(SR * .35)) / SR
        return np.sin(2 * np.pi * (45 + 90 * np.exp(-25 * tt)) * tt) * np.exp(-9 * tt)

    def hat(open_=False):
        L = int(SR * (.12 if open_ else .04))
        n = rng.standard_normal(L)
        n = np.diff(np.r_[0, n])  # agudos
        return n * np.exp(-np.arange(L) / (L / 4)) * .25

    hz = lambda m: 440 * 2 ** ((m - 69) / 12)

    def track(name, bpm, chords, bass_roots, bars, kind, use, energy):
        beat = 60 / bpm
        total = int(SR * beat * 4 * bars) + SR * 2
        mix = np.zeros(total)

        def add(x, at, gain=1.0):
            i = int(at * SR)
            mix[i:i + len(x)] += x[:len(mix) - i] * gain

        for b in range(bars):
            ch = chords[b % len(chords)]
            t0 = b * 4 * beat
            for m in ch:
                if kind == "lofi":
                    add(note(hz(m), 4 * beat, "keys"), t0, .18)
                    add(note(hz(m), 2 * beat, "keys"), t0 + 2.5 * beat, .1)
                else:
                    add(note(hz(m), 4 * beat + .8, "pad"), t0, .14)
            root = hz(bass_roots[b % len(bass_roots)])
            if kind == "lofi":
                add(note(root, 1.5 * beat, "bass"), t0, .45)
                add(note(root, 1.0 * beat, "bass"), t0 + 2.5 * beat, .35)
            else:
                for e in range(8):
                    add(note(root, .45 * beat, "bass"), t0 + e * beat / 2, .32)
            if b >= 2:  # la batería entra en el compás 3
                for q in range(4):
                    if kind == "lofi":
                        if q in (0, 2):
                            add(kick(), t0 + q * beat + (.02 if q == 2 else 0), .6)
                        if q in (1, 3):
                            add(rng.standard_normal(int(SR * .15)) * np.exp(-np.arange(int(SR * .15)) / 2500) * .18,
                                t0 + q * beat)
                        add(hat(), t0 + q * beat + .5 * beat + .015, 1)
                    else:
                        add(kick(), t0 + q * beat, .55)
                        add(hat(q % 2 == 1), t0 + q * beat + .5 * beat, 1)
        mix /= np.abs(mix).max() + 1e-9
        raw = os.path.join(d, name + ".wav")
        write_wav(raw, mix * .9)
        out = os.path.join(d, name + ".mp3")
        flt = "lowpass=f=7000,aecho=0.8:0.5:60|90:0.25|0.18,afade=t=in:d=1.5,afade=t=out:st=%.2f:d=2.5,loudnorm=I=-18:TP=-2" % (
            beat * 4 * bars - 0.5)
        ff("-i", raw, "-af", flt, "-t", f"{beat * 4 * bars + 2:.2f}", "-c:a", "libmp3lame", "-b:a", "192k", out)
        os.remove(raw)
        catalog["musica"].append({"archivo": f"musica/{name}.mp3", "bpm": bpm, "energia": energy, "uso": use,
                                  "duracion": round(beat * 4 * bars + 2, 1), "provisoria": True,
                                  "licencia": "propio (sintetizado)"})

    # La menor: Am7 - Fmaj7 - Cmaj7 - G6
    track("base-tranquila-provisoria", 84,
          [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 64]], [45, 41, 36, 43], 24,
          "lofi", "vlog, explicación tranquila", "baja")
    track("base-tension-provisoria", 100,
          [[57, 60, 64], [58, 62, 65], [57, 60, 64], [56, 59, 64]], [45, 46, 45, 44], 26,
          "pad", "mito, problema, giro", "media")
    lic.append("| musica/*-provisoria.mp3 | Sintetizadas con build_library.py | Propias. Reemplazar por música de librería (Pixabay Music) |")


# ------------------------------------------------------------------ overlays y luts

def overlays():
    d = os.path.join(OUT, "overlays")
    os.makedirs(d, exist_ok=True)
    # grano a 540x960 (se escala al usarlo): pesa poco y en un overlay al 20 % no se nota la diferencia
    ff("-f", "lavfi", "-i", "color=c=gray:s=540x960:r=30:d=4", "-vf", "noise=alls=40:allf=t+u,format=yuv420p",
       "-c:v", "libx264", "-crf", "28", "-preset", "slow", os.path.join(d, "grano-01.mp4"))
    # light leak: manchas cálidas que se mueven sobre negro (se usan en modo 'screen')
    for i, (c0, x0, y0) in enumerate([("0xFF7A18", 80, 150), ("0xFFC857", 460, 800)], 1):
        ff("-f", "lavfi", "-i", f"gradients=s=540x960:r=30:d=6:c0={c0}:c1=0x000000:c2=0x000000:c3=0x000000:"
           f"x0={x0}:y0={y0}:x1=540:y1=960:n=2:speed=0.015:type=radial",
           "-vf", "gblur=sigma=70,eq=saturation=1.5:brightness=0.06:contrast=1.2,scale=1080:1920,format=yuv420p", "-c:v", "libx264", "-crf", "24",
           os.path.join(d, f"light-leak-0{i}.mp4"))
    for name, use in (("grano-01", "textura de película (blend screen u overlay, 15–25 %)"),
                      ("light-leak-01", "destello cálido en transiciones (blend screen)"),
                      ("light-leak-02", "destello dorado en hooks (blend screen)")):
        catalog["overlays"].append({"archivo": f"overlays/{name}.mp4", "uso": use, "licencia": "propio (ffmpeg)"})
    lic.append("| overlays/*.mp4 | Generados con ffmpeg | Propios, sin restricciones |")

    d = os.path.join(OUT, "luts")
    os.makedirs(d, exist_ok=True)
    N = 17

    def lut(name, fn, use):
        lines = [f'TITLE "{name}"', f"LUT_3D_SIZE {N}"]
        for b in range(N):
            for g in range(N):
                for r in range(N):
                    rgb = np.clip(fn(np.array([r, g, b]) / (N - 1)), 0, 1)
                    lines.append(" ".join(f"{v:.5f}" for v in rgb))
        open(os.path.join(d, name + ".cube"), "w").write("\n".join(lines) + "\n")
        catalog["luts"].append({"archivo": f"luts/{name}.cube", "uso": use, "licencia": "propio"})

    s_curve = lambda x: x + 0.12 * np.sin(2 * np.pi * (x - 0.5)) * (x * (1 - x)) * 4
    lut("calido", lambda c: s_curve(c * np.array([1.06, 1.0, 0.92])), "tono cálido, atardecer")
    lut("teal-orange", lambda c: s_curve(np.array([c[0] * 1.08, c[1], c[2] * 0.9 + (1 - c.mean()) * 0.08])),
        "look cine: sombras frías, pieles cálidas")
    lut("bn-contraste", lambda c: np.repeat(s_curve(s_curve(np.array([c @ [0.3, 0.59, 0.11]]))), 3),
        "blanco y negro con contraste (hooks dramáticos)")
    lic.append("| luts/*.cube | Generados con build_library.py | Propios, sin restricciones |")


# ------------------------------------------------------------------ de GitHub y npm

ICONS = ["check", "x", "arrow-right", "arrow-down", "truck", "ship", "package", "factory", "dollar-sign",
         "triangle-alert", "trending-up", "trending-down", "globe", "shield-check", "search", "clock", "plane",
         "map-pin", "users", "lightbulb"]


def downloads():
    tmp = tempfile.mkdtemp()
    subprocess.run(["npm", "install", "--prefix", tmp, "--no-audit", "--no-fund", "--silent", "lucide-static@1.66.0",
                    "@fontsource/anton@5.3.0", "@fontsource/bebas-neue@5.3.0", "@fontsource/montserrat@5.3.0",
                    "lottie-web@5.13.0"], check=True)
    nm = os.path.join(tmp, "node_modules")
    d = os.path.join(OUT, "iconos")
    os.makedirs(d, exist_ok=True)
    for ic in ICONS:
        src = os.path.join(nm, "lucide-static", "icons", f"{ic}.svg")
        if os.path.isfile(src):
            shutil.copy(src, d)
            catalog["iconos"].append({"archivo": f"iconos/{ic}.svg", "licencia": "ISC"})
    lic.append("| iconos/*.svg | Lucide (npm lucide-static 1.66.0) | ISC |")

    d = os.path.join(OUT, "fuentes")
    os.makedirs(d, exist_ok=True)
    for pkg, files in (("anton", ["anton-latin-400-normal.woff2"]),
                       ("bebas-neue", ["bebas-neue-latin-400-normal.woff2"]),
                       ("montserrat", ["montserrat-latin-800-normal.woff2", "montserrat-latin-900-normal.woff2"])):
        for f in files:
            src = os.path.join(nm, "@fontsource", pkg, "files", f)
            if os.path.isfile(src):
                shutil.copy(src, d)
                catalog["fuentes"].append({"archivo": f"fuentes/{f}", "familia": pkg, "licencia": "OFL-1.1"})
    lic.append("| fuentes/*.woff2 | Google Fonts vía @fontsource (Anton, Bebas Neue, Montserrat) | OFL-1.1 |")

    d = os.path.join(OUT, "animaciones")
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(nm, "lottie-web", "build", "player", "lottie.min.js"), d)
    catalog["animaciones"].append({"archivo": "animaciones/lottie.min.js", "uso": "reproductor para animaciones .json",
                                   "licencia": "MIT"})
    lic.append("| animaciones/lottie.min.js | lottie-web 5.13.0 (npm) | MIT |")
    shutil.rmtree(tmp)


def main():
    os.makedirs(OUT, exist_ok=True)
    sounds()
    music()
    overlays()
    downloads()
    json.dump(catalog, open(os.path.join(OUT, "catalogo.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(OUT, "licencias.md"), "w").write(
        "# Licencias de la librería\n\nTodo lo de esta carpeta permite uso comercial sin atribución. "
        "Al agregar un archivo a mano, sumá una fila.\n\n| Archivos | Fuente | Licencia |\n| --- | --- | --- |\n"
        + "\n".join(lic) + "\n")
    print("kit en", OUT, {k: len(v) for k, v in catalog.items()})


if __name__ == "__main__":
    main()
