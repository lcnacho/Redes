#!/usr/bin/env bash
# Instala todo lo que necesita el sistema de edición. Idempotente: si algo ya está, lo saltea.
#
# Dos usos:
#  1. Como "Setup script" del entorno cloud (copiar este archivo entero en la configuración del
#     entorno). Así cada sesión arranca con todo instalado.
#  2. Desde el repo: `bash scripts/setup.sh` al inicio de una sesión, por si el entorno no lo tiene.
#     Lo corre la skill de edición antes de procesar.
#
# Solo usa hosts que la red "Trusted/Limited" permite: PyPI, npm y GitHub (releases).
# No necesita huggingface.co: la transcripción usa Parakeet, que se baja de GitHub.
set -euo pipefail

MODELS="${EDICION_MODELS:-$HOME/.cache/edicion/models}"
BIN="$HOME/.local/bin"
RCLONE_VERSION="v1.71.2"
SHERPA_REL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
mkdir -p "$MODELS" "$BIN"
export PATH="$BIN:$PATH"
log() { echo "[setup] $*"; }

# 1. ffmpeg
if ! command -v ffmpeg >/dev/null; then
  log "instalando ffmpeg"
  (sudo -n true 2>/dev/null && SUDO=sudo || SUDO="")
  $SUDO apt-get update -qq && $SUDO apt-get install -y -qq ffmpeg
fi

# 2. Python: transcripción y descargas
python3 -c "import sherpa_onnx, numpy" 2>/dev/null || {
  log "instalando sherpa-onnx"; pip install -q --break-system-packages sherpa-onnx numpy 2>/dev/null || pip install -q sherpa-onnx numpy; }
command -v yt-dlp >/dev/null || {
  log "instalando yt-dlp"; pip install -q --break-system-packages yt-dlp 2>/dev/null || pip install -q yt-dlp; }

# 3. Modelos (Parakeet para transcribir, Silero para detectar voz)
if [ ! -f "$MODELS/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8/encoder.int8.onnx" ]; then
  log "bajando Parakeet (480 MB)"
  curl -sSL --retry 3 "$SHERPA_REL/sherpa-onnx-nemo-parakeet-tdt-0.6b-v2-int8.tar.bz2" | tar xj -C "$MODELS"
fi
[ -f "$MODELS/silero_vad.onnx" ] || curl -sSL --retry 3 -o "$MODELS/silero_vad.onnx" "$SHERPA_REL/silero_vad.onnx"

# 4. rclone (Google Drive)
if ! command -v rclone >/dev/null; then
  log "instalando rclone $RCLONE_VERSION"
  tmp=$(mktemp -d)
  curl -sSL --retry 3 -o "$tmp/r.zip" "https://github.com/rclone/rclone/releases/download/$RCLONE_VERSION/rclone-$RCLONE_VERSION-linux-amd64.zip"
  (cd "$tmp" && unzip -q r.zip && cp rclone-*/rclone "$BIN/")
  rm -rf "$tmp"
fi

# 5. Node + HyperFrames (dentro del repo, versión fija en package.json)
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || true)"
if [ -n "$REPO" ] && [ -f "$REPO/package.json" ]; then
  if [ ! -x "$REPO/node_modules/.bin/hyperframes" ]; then
    log "instalando HyperFrames"; (cd "$REPO" && npm install --no-audit --no-fund --silent)
  fi
  "$REPO/node_modules/.bin/hyperframes" telemetry disable >/dev/null 2>&1 || true
  "$REPO/node_modules/.bin/hyperframes" browser ensure >/dev/null 2>&1 || log "aviso: no pude preparar Chrome para HyperFrames"
  # 6. Efectos de sonido base
  [ -f "$REPO/library/sonidos-base/whoosh.wav" ] || bash "$REPO/scripts/gen_sfx.sh" >/dev/null
fi

log "listo: ffmpeg $(ffmpeg -version | head -1 | cut -d' ' -f3), rclone $(rclone version 2>/dev/null | head -1 | cut -d' ' -f2), modelos en $MODELS"
