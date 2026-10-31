#!/usr/bin/env bash
# Prepara un video para que Claude escriba el plan: normaliza el bruto, transcribe y analiza.
# Uso: scripts/prep.sh <carpeta_video>
# Deja en <carpeta>/_work: words.json, analysis.json, transcript.md y frames.jpg (cuadros del bruto).
set -euo pipefail
DIR="$(cd "$1" && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$DIR/_work"; mkdir -p "$WORK"

# El bruto: camara.mp4, o el primer video que haya en la carpeta
SRC="$DIR/camara.mp4"
if [ ! -f "$SRC" ]; then
  cand=$(find "$DIR" -maxdepth 1 -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.m4v' \) | head -1)
  [ -n "$cand" ] || { echo "No hay video en $DIR" >&2; exit 1; }
  echo "Usando $(basename "$cand") como camara"
  ffmpeg -v error -y -i "$cand" -c copy -movflags +faststart "$SRC" 2>/dev/null \
    || ffmpeg -v error -y -i "$cand" -c:v libx264 -crf 16 -preset fast -c:a aac -b:a 192k "$SRC"
fi

python3 "$HERE/transcribe.py" "$SRC" -o "$WORK/words.json" ${EDICION_ASR:+--engine "$EDICION_ASR"}
python3 "$HERE/analyze.py" "$WORK/words.json" -o "$WORK/analysis.json" --md "$WORK/transcript.md"

# 12 cuadros del bruto para que Claude vea encuadre, luz y dónde está la cara
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")
ffmpeg -v error -y -i "$SRC" -vf "fps=12/$dur,scale=270:-2,tile=6x2" -frames:v 1 "$WORK/frames.jpg" || true
echo "Listo: $WORK/transcript.md"
