#!/usr/bin/env python3
"""Analiza la transcripción y marca qué cortar: muletillas, repeticiones y pausas.

Uso:
  python3 scripts/analyze.py words.json -o analysis.json --md transcript.md

analysis.json:
  cut_ids     palabras a eliminar (muletillas y la primera toma de una repetición)
  reasons     id -> motivo
  pauses      huecos entre palabras > --gap segundos [{after, before, dur}]
  sentences   frases con su rango de ids y tiempos (lo que lee Claude para decidir)
transcript.md: la transcripción numerada por frase, legible para Claude.
"""
import argparse
import json
import re

# muletillas en inglés y español ("este" y "o sea" no: también son palabras con sentido)
FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "eh", "ehh", "em", "emm", "hmm", "mm", "mmm", "mhm"}
END_PUNCT = re.compile(r"[.!?]$")


def norm(t):
    return re.sub(r"[^\w$%']", "", t.lower())


def find_repeats(words, cut):
    """Detecta reinicios: la misma secuencia de 1 a 4 palabras dicha dos veces seguidas.
    Se corta la primera; la segunda suele ser la toma buena."""
    toks = [norm(w["text"]) for w in words]
    reasons = {}
    i = 0
    while i < len(words):
        hit = False
        for n in (4, 3, 2, 1):
            a, b = toks[i:i + n], toks[i + n:i + 2 * n]
            if len(b) < n or a != b or not all(a):
                continue
            # una palabra repetida solo cuenta si es corta o no es un recurso retórico ("very very")
            if n == 1 and a[0] in {"very", "really", "no", "yeah", "so"}:
                continue
            if words[i + n]["start"] - words[i + n - 1]["end"] > 2.0:
                continue
            for k in range(i, i + n):
                cut.add(words[k]["id"])
                reasons[words[k]["id"]] = f"repetición ({n} palabra/s)"
            i += n
            hit = True
            break
        if not hit:
            i += 1
    return reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--md", help="transcripción legible para Claude")
    ap.add_argument("--gap", type=float, default=0.3, help="pausa mínima a cortar (s)")
    args = ap.parse_args()

    data = json.load(open(args.words))
    words = data["words"]
    cut, reasons = set(), {}

    for w in words:
        if norm(w["text"]) in FILLERS:
            cut.add(w["id"])
            reasons[w["id"]] = "muletilla"
    reasons.update(find_repeats(words, cut))

    pauses = []
    for a, b in zip(words, words[1:]):
        gap = b["start"] - a["end"]
        if gap > args.gap:
            pauses.append({"after": a["id"], "before": b["id"], "dur": round(gap, 2)})

    sentences, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if END_PUNCT.search(w["text"]) or nxt is None or nxt["start"] - w["end"] > 0.8:
            sentences.append({
                "id": f"s{len(sentences)}", "from": cur[0]["id"], "to": cur[-1]["id"],
                "start": cur[0]["start"], "end": cur[-1]["end"],
                "text": " ".join(x["text"] for x in cur)})
            cur = []

    json.dump({"cut_ids": sorted(cut, key=lambda x: int(x[1:])), "reasons": reasons,
               "pauses": pauses, "sentences": sentences},
              open(args.out, "w"), ensure_ascii=False, indent=1)

    if args.md:
        idx = {w["id"]: i for i, w in enumerate(words)}
        lines = [f"# Transcripción ({data['duration']} s, {len(words)} palabras)", "",
                 "Formato: `sN [inicio–fin] (wDesde–wHasta) texto`. ~~tachado~~ = se corta solo.", ""]
        for s in sentences:
            seg = words[idx[s["from"]]:idx[s["to"]] + 1]
            txt = " ".join(f"~~{w['text']}~~" if w["id"] in cut else w["text"] for w in seg)
            lines.append(f"- {s['id']} [{s['start']:.2f}–{s['end']:.2f}] ({s['from']}–{s['to']}) {txt}")
        open(args.md, "w").write("\n".join(lines) + "\n")

    print(f"{len(sentences)} frases, {len(cut)} palabras a cortar, {len(pauses)} pausas > {args.gap}s")


if __name__ == "__main__":
    main()
