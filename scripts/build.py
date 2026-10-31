#!/usr/bin/env python3
"""Arma un video editado a partir del plan de edición que escribe Claude.

Uso:
  python3 scripts/build.py <carpeta_video>                 # todas las variantes de hook
  python3 scripts/build.py <carpeta_video> --variant A     # una sola
  python3 scripts/build.py <carpeta_video> --no-render     # solo arma el proyecto (para revisar)

La carpeta del video tiene:
  camara.mp4            el bruto (o el que diga plan.fuente)
  plan.json             el plan de edición (ver rules/plan.md)
  _work/words.json      transcripción (scripts/transcribe.py)
  _work/analysis.json   cortes automáticos (scripts/analyze.py)
Escribe:
  _work/variante_X/     proyecto HyperFrames (index.html + assets) para revisar o re-renderizar
  salida/final_X.mp4    el video final de cada variante
  salida/notas.txt      qué hook, estilo y cortes se usaron
"""
import argparse
import html
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
W, H, FPS = 1080, 1920, 30
PRE, POST = 0.06, 0.10          # margen antes y después de cada tramo de voz (s)
MAX_GAP = 0.3                   # pausas más largas se cortan
SAFE_X, SAFE_W = 112, 856       # recuadro seguro central común a TikTok, Reels y Shorts
LIB_DIRS = [os.environ.get("EDICION_LIBRARY", ""), os.path.join(REPO, "library")]
HF_BIN = os.path.join(REPO, "node_modules", ".bin", "hyperframes")

# Tratamiento de imagen por estilo de hook (se aplica en ffmpeg, no con filtros CSS)
TREATMENT = {
    "bn-dramatico": "hue=s=0,eq=contrast=1.35:brightness=-0.02,noise=alls=16:allf=t+u",
}
# Alturas (px desde arriba) de cada texto. "medio" sirve cuando la cara ocupa la parte de arriba
# del cuadro (por ejemplo, video con cámara doble y la selfie en una esquina superior).
ZONAS = {
    "arriba": {"hook": 330, "hook2": 600, "negra": 760, "tarjeta": 300, "lista": 250, "numero": 420, "subs": 1110},
    "medio": {"hook": 860, "hook2": 1110, "negra": 860, "tarjeta": 860, "lista": 800, "numero": 820, "subs": 1190},
}
HOOK_SFX = {"bn-dramatico": "impacto", "numero-impactante": "impacto", "congelado": "scratch",
            "stop-doing": "whoosh", "pantalla-negra": "riser"}


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def esc(t):
    return html.escape(t, quote=True)


def clean_caption(t):
    return t.strip().rstrip(".,;:").replace(" ,", ",")


def find_lib(*rel_candidates):
    for base in LIB_DIRS:
        if not base:
            continue
        for rel in rel_candidates:
            p = os.path.join(base, rel)
            if os.path.isfile(p):
                return p
    return None


def find_sfx(name):
    exts = (".wav", ".mp3", ".ogg", ".m4a")
    return find_lib(*[f"sonidos/{name}{e}" for e in exts], *[f"sonidos-base/{name}{e}" for e in exts])


# ---------------------------------------------------------------- tramos

class Timeline:
    """Convierte rangos de palabras del bruto en tramos de corte y mapea tiempos al video final."""

    def __init__(self, words, cut_ids):
        self.words = words
        self.idx = {w["id"]: i for i, w in enumerate(words)}
        self.cut = set(cut_ids)

    def runs(self, rng, exclude=()):
        a, b = rng
        if a not in self.idx or b not in self.idx:
            sys.exit(f"Rango inválido en el plan: {rng}")
        runs, cur = [], []
        for w in self.words[self.idx[a]:self.idx[b] + 1]:
            if w["id"] in self.cut or w["id"] in exclude:
                if cur:
                    runs.append(cur)
                cur = []
                continue
            if cur and w["start"] - cur[-1]["end"] > MAX_GAP:
                runs.append(cur)
                cur = []
            cur.append(w)
        if cur:
            runs.append(cur)
        return runs

    def bounds(self, run, src_dur):
        i0, i1 = self.idx[run[0]["id"]], self.idx[run[-1]["id"]]
        s = run[0]["start"] - PRE
        e = run[-1]["end"] + POST
        if i0 > 0:
            s = max(s, self.words[i0 - 1]["end"] + 0.01)
        if i1 + 1 < len(self.words):
            e = min(e, self.words[i1 + 1]["start"] - 0.01)
        return max(0.0, s), min(src_dur, e)


def plan_segments(tl, plan, hook, src_dur):
    """Lista ordenada de tramos: [{src_start, src_end, words, kind, treatment}]."""
    segs = []
    hook_ids = set()
    if hook:
        if hook.get("estilo") == "congelado":
            first = tl.words[tl.idx[hook["rango"][0]]]
            segs.append({"kind": "freeze", "src_start": first["start"], "src_end": first["start"],
                         "dur": 1.0, "words": [], "treatment": None})
        for run in tl.runs(hook["rango"]):
            s, e = tl.bounds(run, src_dur)
            segs.append({"kind": "hook", "src_start": s, "src_end": e, "words": run,
                         "treatment": TREATMENT.get(hook.get("estilo"))})
            hook_ids.update(w["id"] for w in run)
    exclude = set() if plan.get("repetir_hook_en_cuerpo") else hook_ids
    for rng in plan["cuerpo"]:
        for run in tl.runs(rng, exclude=exclude):
            s, e = tl.bounds(run, src_dur)
            segs.append({"kind": "body", "src_start": s, "src_end": e, "words": run, "treatment": None})
    t = 0.0
    for sg in segs:
        sg["dur"] = sg["dur"] if sg["kind"] == "freeze" else sg["src_end"] - sg["src_start"]
        sg["out_start"] = t
        t += sg["dur"]
    return segs, t


# ---------------------------------------------------------------- corte con ffmpeg

def cut_aroll(src, segs, out_path, work):
    lines = []
    for i, sg in enumerate(segs):
        if sg["kind"] == "freeze":
            frames = round(sg["dur"] * FPS)
            lines.append(f"[0:v]trim=start={sg['src_start']:.3f}:duration=0.05,setpts=PTS-STARTPTS,"
                         f"fps={FPS},loop=loop={frames}:size=1:start=0,trim=end_frame={frames},"
                         f"setpts=N/{FPS}/TB,hue=s=0.2[pv{i}]")
            lines.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={sg['dur']:.3f}[a{i}]")
        else:
            tr = "," + sg["treatment"] if sg["treatment"] else ""
            lines.append(f"[0:v]trim=start={sg['src_start']:.3f}:end={sg['src_end']:.3f},setpts=PTS-STARTPTS,"
                         f"fps={FPS}{tr}[pv{i}]")
            d = sg["src_end"] - sg["src_start"]
            lines.append(f"[0:a]atrim=start={sg['src_start']:.3f}:end={sg['src_end']:.3f},asetpts=PTS-STARTPTS,"
                         f"aresample=48000,aformat=channel_layouts=stereo,"
                         f"afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.015):.3f}:d=0.015[a{i}]")
    # cada tramo pasa a 1080x1920 antes de unirlos, así concat recibe todo con el mismo formato
    norm = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,format=yuv420p"
    for i in range(len(segs)):
        lines.append(f"[pv{i}]{norm}[v{i}]")
    lines.append("".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[vc][ac]")
    lines.append("[ac]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[ao]")
    script = os.path.join(work, "cortes.ffgraph")
    open(script, "w").write(";\n".join(lines))
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex_script", script,
        "-map", "[vc]", "-map", "[ao]", "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-g", str(FPS), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path])


# ---------------------------------------------------------------- composición

def map_words(segs):
    out = []
    for sg in segs:
        for w in sg["words"]:
            t0 = sg["out_start"] + (w["start"] - sg["src_start"])
            t1 = sg["out_start"] + (w["end"] - sg["src_start"])
            out.append({**w, "o_start": max(sg["out_start"], t0), "o_end": min(sg["out_start"] + sg["dur"], t1),
                        "seg_kind": sg["kind"]})
    return out


def caption_groups(words, start_after, total, max_words=3, max_chars=20):
    groups, cur = [], []
    for i, w in enumerate(words):
        if w["o_start"] < start_after:
            continue
        txt = clean_caption(w["text"])
        if not txt:
            continue
        brk = cur and (len(cur) >= max_words or
                       len(" ".join(c["cap"] for c in cur) + " " + txt) > max_chars or
                       w["o_start"] - cur[-1]["o_end"] >= 0.15 or
                       w["seg_kind"] != cur[-1]["seg_kind"])   # nunca mezclar el final del hook con el cuerpo
        if brk:
            groups.append(cur)
            cur = []
        cur.append({**w, "cap": txt})
        if w["text"].rstrip()[-1:] in ".?!":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    out = []
    for i, g in enumerate(groups):
        s = max(g[0]["o_start"] - 0.05, start_after)
        nxt = groups[i + 1][0]["o_start"] - 0.05 if i + 1 < len(groups) else None
        e = min(g[-1]["o_end"] + 0.3, total)
        if nxt is not None:
            e = min(e, nxt)
        if out and s < out[-1]["end"]:
            s = out[-1]["end"]
        if e - s >= 0.12:
            out.append({"start": s, "end": e, "words": g})
    return out


def is_keyword(w, keywords):
    n = w["cap"].lower().strip("?!'\"")
    return any(ch.isdigit() for ch in n) or "$" in n or n in keywords


class Comp:
    def __init__(self):
        self.html, self.js, self.events, self.sfx = [], [], [], []
        self.n = 0

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"


def word_time(wmap, wid, default=None):
    for w in wmap:
        if w["id"] == wid:
            return w["o_start"]
    return default


def build_composition(plan, hook, segs, wmap, total, proj, style):
    c = Comp()
    accent = style.get("acento", "#FFD400")
    color = style.get("color", "#FFFFFF")
    keywords = {k.lower() for k in plan.get("palabras_clave", [])}
    hook_end = max((s["out_start"] + s["dur"] for s in segs if s["kind"] in ("hook", "freeze")), default=0.0)
    seams = [s["out_start"] for s in segs[1:]]
    estilo = (hook or {}).get("estilo", "titular")
    hook_text = (hook or {}).get("texto", "")
    Y = ZONAS[plan.get("zona_texto", "arriba")]

    # --- hook: tarjeta según estilo
    if hook:
        hid = c.uid("hook")
        dur = max(1.2, hook_end + 0.25)
        freeze_end = sum(sg["dur"] for sg in segs if sg["kind"] == "freeze")
        if estilo == "congelado":
            dur = freeze_end + 0.15   # el cartel acompaña solo el congelado; después hablan los subtítulos
        if estilo == "pantalla-negra":
            c.html.append(f'<div id="{hid}" class="clip" data-start="0" data-duration="{hook_end:.3f}" '
                          f'data-track-index="3" style="position:absolute;inset:0;z-index:20">'
                          f'<div style="position:absolute;inset:0;background:#000"></div></div>')
            hw = [w for w in wmap if w["seg_kind"] == "hook"]
            # con texto propio, sus palabras se reparten a lo largo del hook; si no, se usan las dichas
            if hook_text:
                tw = hook_text.split()
                hw = [{"text": t, "o_start": 0.05 + i * (hook_end - 0.4) / max(1, len(tw))} for i, t in enumerate(tw)]
            if not hw:
                sys.exit(f"Hook {hook.get('id')}: pantalla-negra necesita 'texto' o palabras en el rango")
            hw[0] = {**hw[0], "o_start": 0.0}   # el cuadro 0 nunca va vacío
            for i, w in enumerate(hw):
                end = hw[i + 1]["o_start"] if i + 1 < len(hw) else hook_end
                shown = " ".join(clean_caption(x["text"]) for x in hw[max(0, i - 4):i + 1])  # máx. 5 palabras
                wid = c.uid("bw")
                c.html.append(f'<div id="{wid}" class="clip" data-start="{w["o_start"]:.3f}" '
                              f'data-duration="{max(0.05, end - w["o_start"]):.3f}" data-track-index="4" '
                              f'style="position:absolute;inset:0;z-index:21">'
                              f'<div class="bw" style="position:absolute;left:{SAFE_X}px;width:{SAFE_W}px;top:{Y["negra"]}px;'
                              f'text-align:center;font:900 96px/1.08 Inter;color:#fff;text-transform:uppercase">'
                              f'{esc(shown)}</div></div>')
        else:
            big, small = hook_text, ""
            size = 96
            fill = color
            if estilo == "numero-impactante":
                parts = hook_text.split(" ", 1)
                big, small = parts[0], parts[1] if len(parts) > 1 else ""
                size, fill = 230, accent
            elif estilo == "stop-doing":
                fill = "#FF3B30"
            elif estilo == "bn-dramatico":
                size = 104
            inner = (f'<div class="hk" style="position:absolute;left:{SAFE_X}px;width:{SAFE_W}px;top:{Y["hook"]}px;'
                     f'text-align:center;font:900 {size}px/1.05 Inter;color:{fill};text-transform:uppercase;'
                     f'letter-spacing:-1px;text-shadow:0 6px 24px rgba(0,0,0,.65),0 2px 0 rgba(0,0,0,.9)">{esc(big)}')
            inner += '</div>'
            if estilo == "stop-doing":
                # copia tachada encima, revelada de izquierda a derecha con clip-path
                inner += (f'<div class="hks" style="position:absolute;left:{SAFE_X}px;width:{SAFE_W}px;top:{Y["hook"]}px;'
                          f'text-align:center;font:900 {size}px/1.05 Inter;color:transparent;text-transform:uppercase;'
                          f'letter-spacing:-1px;text-decoration:line-through;text-decoration-color:#fff;'
                          f'text-decoration-thickness:10px;clip-path:inset(0 100% 0 0)">{esc(big)}</div>')
            if small:
                inner += (f'<div class="hk2" style="position:absolute;left:{SAFE_X}px;width:{SAFE_W}px;top:{Y["hook2"]}px;'
                          f'text-align:center;font:900 64px/1.1 Inter;color:{color};text-transform:uppercase;'
                          f'text-shadow:0 4px 18px rgba(0,0,0,.7)">{esc(small)}</div>')
            c.html.append(f'<div id="{hid}" class="clip" data-start="0.1" data-duration="{dur - 0.1:.3f}" '
                          f'data-track-index="3" style="position:absolute;inset:0;z-index:20">{inner}</div>')
            if estilo == "numero-impactante":
                c.js.append(f'tl.from("#{hid} .hk", {{scale: 0.2, opacity: 0, duration: 0.35, ease: "back.out(2.2)"}}, 0.1);')
                c.js.append(f'tl.from("#{hid} .hk2", {{y: 30, opacity: 0, duration: 0.3, ease: "power2.out"}}, 0.45);')
            elif estilo == "stop-doing":
                c.js.append(f'tl.from("#{hid} .hk", {{scale: 1.25, opacity: 0, duration: 0.25, ease: "power3.out"}}, 0.1);')
                c.js.append(f'tl.to("#{hid} .hks", {{clipPath: "inset(0 0% 0 0)", duration: 0.35, ease: "power2.inOut"}}, 0.6);')
            else:
                c.js.append(f'tl.from("#{hid} .hk", {{y: 40, opacity: 0, duration: 0.3, ease: "power3.out"}}, 0.1);')
            c.js.append(f'tl.to("#{hid} .hk, #{hid} .hk2, #{hid} .hks", {{opacity: 0, duration: 0.15, ease: "power2.in"}}, {dur - 0.27:.3f});')
        c.events.append(0.0)
        if HOOK_SFX.get(estilo):
            c.sfx.append((0.05, HOOK_SFX[estilo], 0.9))
        if hook_end > 0 and seams:
            c.sfx.append((max(0, hook_end - 0.2), "whoosh", 0.55))

    # --- subtítulos palabra por palabra, en grupos de 2 a 3
    cap_from = (freeze_end if estilo == "congelado" else hook_end) if hook else 0.0
    for g in caption_groups(wmap, cap_from, total):
        gid = c.uid("cap")
        spans = []
        for w in g["words"]:
            col = accent if is_keyword(w, keywords) else color
            spans.append(f'<span style="color:{col}">{esc(w["cap"])}</span>')
        c.html.append(f'<div id="{gid}" class="clip" data-start="{g["start"]:.3f}" data-duration="{g["end"] - g["start"]:.3f}" '
                      f'data-track-index="2" style="position:absolute;inset:0;z-index:10">'
                      f'<div class="cl" style="position:absolute;left:{SAFE_X}px;width:{SAFE_W}px;top:{Y["subs"]}px;'
                      f'text-align:center;font:900 92px/1.06 Inter;letter-spacing:-0.5px;'
                      f'text-shadow:0 0 3px #000,0 0 3px #000,0 5px 14px rgba(0,0,0,.75)">{" ".join(spans)}</div></div>')
        c.js.append(f'tl.from("#{gid} .cl", {{scale: 0.86, opacity: 0, duration: 0.1, ease: "power2.out"}}, {g["start"]:.3f});')

    # --- tarjetas de texto
    for card in plan.get("tarjetas", []):
        t = word_time(wmap, card["en"])
        if t is None or t < hook_end:
            continue
        d = float(card.get("dur", 2.2))
        cid = c.uid("card")
        c.html.append(f'<div id="{cid}" class="clip" data-start="{t:.3f}" data-duration="{d:.3f}" data-track-index="5" '
                      f'style="position:absolute;inset:0;z-index:15"><div class="cd" style="position:absolute;left:{SAFE_X}px;'
                      f'width:{SAFE_W}px;top:{Y["tarjeta"]}px;text-align:center"><span style="display:inline-block;padding:18px 30px;'
                      f'background:{accent};color:#111;font:900 70px/1.08 Inter;text-transform:uppercase;border-radius:14px;'
                      f'box-shadow:0 10px 30px rgba(0,0,0,.35)">{esc(card["texto"])}</span></div></div>')
        c.js.append(f'tl.from("#{cid} .cd", {{y: -30, scale: 0.9, opacity: 0, duration: 0.25, ease: "back.out(1.8)"}}, {t:.3f});')
        c.js.append(f'tl.to("#{cid} .cd", {{opacity: 0, duration: 0.2, ease: "power2.in"}}, {t + d - 0.22:.3f});')
        c.events.append(t)
        c.sfx.append((t, card.get("sfx", "pop"), 0.6))

    # --- efectos
    for ef in plan.get("efectos", []):
        t = word_time(wmap, ef["en"])
        if t is None:
            continue
        eid = c.uid("fx")
        if ef["tipo"] == "lista":
            items = ef["items"]
            d = float(ef.get("dur", 1.2 + 1.1 * len(items)))
            times = [word_time(wmap, x, None) for x in ef.get("items_en", [])]
            times = [x for x in times if x is not None]
            if len(times) != len(items):
                times = [t + 0.45 + i * (d - 1.0) / max(1, len(items)) for i in range(len(items))]
            rows = "".join(
                f'<div class="it" style="display:flex;align-items:center;gap:22px;margin-top:22px">'
                f'<div class="ck" style="flex:none;width:72px;height:72px;border-radius:50%;background:{accent};color:#111;'
                f'font:900 48px/72px Inter;text-align:center">&#10003;</div>'
                f'<div style="font:800 66px/1.1 Inter;color:#fff">{esc(it)}</div></div>' for it in items)
            title = (f'<div style="font:900 52px Inter;color:{accent};text-transform:uppercase;letter-spacing:1px">'
                     f'{esc(ef["titulo"])}</div>') if ef.get("titulo") else ""
            c.html.append(f'<div id="{eid}" class="clip" data-start="{t:.3f}" data-duration="{d:.3f}" data-track-index="6" '
                          f'style="position:absolute;inset:0;z-index:16"><div class="pn" style="position:absolute;left:{SAFE_X}px;'
                          f'width:{SAFE_W}px;top:{Y["lista"]}px;padding:36px 40px;box-sizing:border-box;border-radius:28px;'
                          f'background:rgba(15,16,22,.78);backdrop-filter:blur(22px);border:1px solid rgba(255,255,255,.14)">'
                          f'{title}{rows}</div></div>')
            c.js.append(f'tl.from("#{eid} .pn", {{y: -40, opacity: 0, duration: 0.3, ease: "power3.out"}}, {t:.3f});')
            for i, ti in enumerate(times):
                c.js.append(f'tl.from("#{eid} .it:nth-child({i + 1 + (1 if title else 0)})", '
                            f'{{x: -40, opacity: 0, duration: 0.22, ease: "power2.out"}}, {ti:.3f});')
                c.js.append(f'tl.from("#{eid} .it:nth-child({i + 1 + (1 if title else 0)}) .ck", '
                            f'{{scale: 0, duration: 0.25, ease: "back.out(3)"}}, {ti + 0.08:.3f});')
                c.sfx.append((ti + 0.08, "tick", 0.55))
                c.events.append(ti)
            c.js.append(f'tl.to("#{eid} .pn", {{opacity: 0, duration: 0.2}}, {t + d - 0.22:.3f});')
        elif ef["tipo"] == "numero":
            d = float(ef.get("dur", 1.8))
            c.html.append(f'<div id="{eid}" class="clip" data-start="{t:.3f}" data-duration="{d:.3f}" data-track-index="6" '
                          f'style="position:absolute;inset:0;z-index:16"><div class="nm" style="position:absolute;left:{SAFE_X}px;'
                          f'width:{SAFE_W}px;top:{Y["numero"]}px;text-align:center;font:900 220px/1 Inter;color:{accent};'
                          f'text-shadow:0 8px 30px rgba(0,0,0,.6)">{esc(ef["texto"])}</div></div>')
            c.js.append(f'tl.from("#{eid} .nm", {{scale: 0.2, opacity: 0, duration: 0.35, ease: "back.out(2.4)"}}, {t:.3f});')
            c.js.append(f'tl.to("#{eid} .nm", {{opacity: 0, scale: 1.1, duration: 0.2}}, {t + d - 0.22:.3f});')
            c.sfx.append((t, "pop", 0.7))
        else:
            print(f"aviso: efecto '{ef['tipo']}' todavía no implementado, se omite")
            continue
        c.events.append(t)

    # --- zooms (en un wrapper del video, nunca en el <video>)
    zooms = sorted(((word_time(wmap, z["en"]), z.get("tipo", "suave")) for z in plan.get("zooms", [])
                    if word_time(wmap, z["en"]) is not None), key=lambda x: x[0])
    if hook and estilo == "stop-doing":
        zooms.insert(0, (0.05, "punch"))
    # cambio visual automático: nunca más de ~4.5 s sin un evento
    ev = sorted(set(c.events + seams + [z[0] for z in zooms] + [total]))
    auto = 0
    prev = 0.0
    for e in ev:
        while e - prev > 4.5:
            prev += 3.5
            zooms.append((prev, "auto"))
            auto += 1
        prev = e
    zooms.sort(key=lambda x: x[0])
    for i, (t, kind) in enumerate(zooms):
        nxt = zooms[i + 1][0] if i + 1 < len(zooms) else total
        end = min(nxt, t + 3.0)
        snap = next((s for s in seams if t + 1.2 <= s <= end), end)
        scale = {"punch": 1.22, "suave": 1.12, "auto": 1.06}[kind]
        if kind == "punch":
            c.js.append(f'tl.set("#camzoom", {{scale: {scale}}}, {t:.3f});')
        else:
            c.js.append(f'tl.to("#camzoom", {{scale: {scale}, duration: 0.55, ease: "power2.out"}}, {t:.3f});')
        if snap < total - 0.05:
            c.js.append(f'tl.set("#camzoom", {{scale: 1}}, {snap:.3f});')

    # --- efectos de sonido (sin dos golpes a menos de 0.35 s)
    placed = []
    for t, name, vol in sorted(c.sfx + [(word_time(wmap, s["en"]), s["nombre"], s.get("vol", 0.6))
                                        for s in plan.get("sfx", []) if word_time(wmap, s["en"]) is not None]):
        if any(abs(t - p) < 0.35 for p in placed):
            continue
        path = find_sfx(name)
        if not path:
            print(f"aviso: no encuentro el sonido '{name}'")
            continue
        dst = os.path.join(proj, "assets", "sfx", os.path.basename(path))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(path, dst)
        d = min(probe_duration(path), max(0.1, total - t))
        sid = c.uid("sfx")
        c.html.append(f'<audio id="{sid}" class="clip" src="assets/sfx/{os.path.basename(path)}" data-start="{t:.3f}" '
                      f'data-duration="{d:.3f}" data-volume="{vol}" data-track-index="8"></audio>')
        placed.append(t)

    # --- música con ducking automático cuando hay voz
    if plan.get("musica"):
        mpath = find_lib(plan["musica"], os.path.join("musica", plan["musica"]))
        if mpath:
            ext = os.path.splitext(mpath)[1]
            shutil.copy(mpath, os.path.join(proj, "assets", "music" + ext))
            pts = [{"t": 0, "v": 0.22}]
            speech = []
            for w in wmap:
                if speech and w["o_start"] - speech[-1][1] < 0.6:
                    speech[-1][1] = w["o_end"]
                else:
                    speech.append([w["o_start"], w["o_end"]])
            for a, b in speech:
                pts += [{"t": round(max(0, a - 0.15), 3), "v": 0.22}, {"t": round(a, 3), "v": 0.09},
                        {"t": round(b, 3), "v": 0.09}, {"t": round(b + 0.25, 3), "v": 0.22}]
            pts += [{"t": round(max(0, total - 1.0), 3), "v": 0.22}, {"t": round(total, 3), "v": 0.0}]
            pts = sorted({p["t"]: p for p in pts}.values(), key=lambda p: p["t"])[:512]
            auto_json = esc(json.dumps({"version": 1, "lanes": [{"target": "volume", "points": pts}]}))
            c.html.append(f'<audio id="music" class="clip" src="assets/music{ext}" data-start="0" data-duration="{total:.3f}" '
                          f'data-volume="1" data-automation="{auto_json}" data-track-index="9"></audio>')
        else:
            print(f"aviso: no encuentro la música '{plan['musica']}'")

    page = f"""<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="gsap.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: {W}px; height: {H}px; overflow: hidden; background: #000; font-family: "Inter", sans-serif; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-width="{W}" data-height="{H}">
  <div id="camzoom" style="position:absolute;inset:0;transform-origin:50% 40%">
    <video id="aroll" class="clip" src="assets/aroll.mp4" playsinline data-start="0" data-duration="{total:.3f}"
      data-has-audio="true" data-track-index="0" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"></video>
  </div>
  {chr(10).join("  " + h for h in c.html)}
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  const tl = gsap.timeline({{ paused: true }});
  {chr(10).join("  " + j for j in c.js)}
  window.__timelines["main"] = tl;
</script>
</body>
</html>
"""
    open(os.path.join(proj, "index.html"), "w").write(page)
    return {"auto_zooms": auto, "sfx": len(placed), "hook_end": round(hook_end, 2), "estilo": estilo if hook else None}


def master(raw, out):
    """Normaliza el volumen final a -14 LUFS (lo que esperan las plataformas) sin tocar el video."""
    sh(["ffmpeg", "-v", "error", "-y", "-i", raw, "-c:v", "copy", "-af",
        "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", out])


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--variant")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--quality", default="delivery", choices=["draft", "looks", "delivery"])
    args = ap.parse_args()

    folder = os.path.abspath(args.folder)
    work = os.path.join(folder, "_work")
    out_dir = os.path.join(folder, "salida")
    os.makedirs(out_dir, exist_ok=True)
    plan = json.load(open(os.path.join(folder, "plan.json")))
    words = json.load(open(os.path.join(work, "words.json")))["words"]
    cut_ids = json.load(open(os.path.join(work, "analysis.json")))["cut_ids"] + plan.get("cortar", [])
    keep = set(plan.get("no_cortar", []))
    cut_ids = [x for x in cut_ids if x not in keep]
    src = os.path.join(folder, plan.get("fuente", "camara.mp4"))
    src_dur = probe_duration(src)
    fixes = plan.get("correcciones", {})
    for w in words:
        if w["id"] in fixes:
            w["text"] = fixes[w["id"]]
    tl = Timeline(words, cut_ids)
    style = plan.get("subtitulos", {})

    hooks = plan.get("hooks") or [None]
    notes = []
    for hook in hooks:
        vid = (hook or {}).get("id", "A")
        if args.variant and vid != args.variant:
            continue
        proj = os.path.join(work, f"variante_{vid}")
        if os.path.isdir(proj):
            shutil.rmtree(proj)
        os.makedirs(os.path.join(proj, "assets"))
        shutil.copy(os.path.join(REPO, "library", "vendor", "gsap.min.js"), proj)

        segs, total = plan_segments(tl, plan, hook, src_dur)
        print(f"[{vid}] {len(segs)} tramos, {total:.1f} s (bruto {src_dur:.1f} s)")
        cut_aroll(src, segs, os.path.join(proj, "assets", "aroll.mp4"), work)
        total = probe_duration(os.path.join(proj, "assets", "aroll.mp4"))
        info = build_composition(plan, hook, segs, map_words(segs), total, proj, style)
        json.dump({"segments": [{k: v for k, v in s.items() if k != "words"} for s in segs], **info},
                  open(os.path.join(proj, "edl.json"), "w"), indent=1)

        if not args.no_render:
            subprocess.run([HF_BIN, "lint"], cwd=proj)
            out = os.path.join(out_dir, f"final_{vid}.mp4")
            raw = os.path.join(proj, "render.mp4")
            sh([HF_BIN, "render", "-q", args.quality, "-f", str(FPS), "-w", "3", "--video-bitrate", "12M",
                "-o", raw], cwd=proj)
            master(raw, out)
            print(f"[{vid}] listo: {out}")
        notes.append(f"Variante {vid}: estilo de hook '{(hook or {}).get('estilo', '-')}', "
                     f"texto '{(hook or {}).get('texto', '')}', duración {total:.1f} s, {len(segs)} tramos, "
                     f"{info['sfx']} sonidos, {info['auto_zooms']} zooms automáticos")

    first = os.path.join(out_dir, f"final_{(hooks[0] or {}).get('id', 'A')}.mp4")
    if os.path.isfile(first):  # miniatura: un cuadro del hook, con el texto ya en pantalla
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1.0", "-i", first, "-frames:v", "1",
                        os.path.join(out_dir, "miniatura.png")])
    with open(os.path.join(out_dir, "notas.txt"), "a") as f:
        f.write(f"# {plan.get('titulo', os.path.basename(folder))}\n" + "\n".join(notes) + "\n\n")


if __name__ == "__main__":
    main()
