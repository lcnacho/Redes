#!/usr/bin/env bash
# Mueve videos entre Google Drive y la sesión, con rclone.
#
# Configuración (variables de entorno del entorno cloud, nunca en el repo):
#   RCLONE_CONFIG_GDRIVE_TYPE=drive
#   RCLONE_CONFIG_GDRIVE_SCOPE=drive
#   RCLONE_CONFIG_GDRIVE_TOKEN={"access_token":...}   <- sale de `rclone authorize "drive"` en tu PC
#   EDICION_DRIVE_ROOT="Edicion automatica"           (opcional, carpeta raíz en Drive)
#
# Uso:
#   scripts/drive.sh check                 prueba el acceso y lista lo pendiente
#   scripts/drive.sh list                  carpetas en 01_Pendientes (una por línea)
#   scripts/drive.sh library               baja _Recursos a la caché local (EDICION_LIBRARY)
#   scripts/drive.sh claim <carpeta>       la pasa a 02_En_proceso y la baja a $EDICION_WORK/<carpeta>
#   scripts/drive.sh deliver <carpeta>     sube la salida a 03_Listos/<carpeta> y archiva el bruto ahí
#   scripts/drive.sh fail <carpeta> "msg"  deja ERROR.txt en 02_En_proceso/<carpeta>
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"
REMOTE="${EDICION_REMOTE:-gdrive}"
ROOT="$REMOTE:${EDICION_DRIVE_ROOT:-Edicion automatica}"
WORK="${EDICION_WORK:-$HOME/trabajo}"
LIB="${EDICION_LIBRARY:-$HOME/.cache/edicion/library}"
RC=(rclone --retries 3 --low-level-retries 10 --stats 0)

need_config() {
  if [ -z "${RCLONE_CONFIG_GDRIVE_TOKEN:-}" ] && ! rclone listremotes 2>/dev/null | grep -q "^$REMOTE:"; then
    echo "Falta configurar Google Drive: ver docs/configurar-drive.md" >&2
    exit 2
  fi
  export RCLONE_CONFIG_GDRIVE_TYPE="${RCLONE_CONFIG_GDRIVE_TYPE:-drive}"
  export RCLONE_CONFIG_GDRIVE_SCOPE="${RCLONE_CONFIG_GDRIVE_SCOPE:-drive}"
}

cmd="${1:-}"; shift || true
need_config
case "$cmd" in
  check)
    "${RC[@]}" mkdir "$ROOT/01_Pendientes"; "${RC[@]}" mkdir "$ROOT/02_En_proceso"
    "${RC[@]}" mkdir "$ROOT/03_Listos"; "${RC[@]}" mkdir "$ROOT/_Recursos"
    echo "Acceso a Drive OK. Pendientes:"
    "${RC[@]}" lsf --dirs-only "$ROOT/01_Pendientes" | sed 's#/$##' ;;
  list)
    "${RC[@]}" lsf --dirs-only "$ROOT/01_Pendientes" | sed 's#/$##' ;;
  library)
    mkdir -p "$LIB"
    "${RC[@]}" sync "$ROOT/_Recursos" "$LIB" --exclude "*.tmp"
    echo "Librería en $LIB" ;;
  claim)
    name="$1"
    "${RC[@]}" moveto "$ROOT/01_Pendientes/$name" "$ROOT/02_En_proceso/$name"
    mkdir -p "$WORK/$name"
    "${RC[@]}" copy "$ROOT/02_En_proceso/$name" "$WORK/$name"
    echo "$WORK/$name" ;;
  deliver)
    name="$1"; local_dir="$WORK/$name"; out="$local_dir/salida"; dst="$ROOT/03_Listos/$name"
    [ -f "$out/final_A.mp4" ] || { echo "No hay salida/final_A.mp4 en $local_dir" >&2; exit 1; }
    "${RC[@]}" copyto "$out/final_A.mp4" "$dst/final_vertical.mp4"
    for f in "$out"/final_*.mp4; do
      v=$(basename "$f" .mp4 | sed 's/final_//'); [ "$v" = "A" ] && continue
      "${RC[@]}" copyto "$f" "$dst/variante_hook_$v.mp4"
    done
    for f in miniatura.png notas.txt; do [ -f "$out/$f" ] && "${RC[@]}" copyto "$out/$f" "$dst/$f"; done
    [ -f "$local_dir/plan.json" ] && "${RC[@]}" copyto "$local_dir/plan.json" "$dst/_control/plan.json"
    "${RC[@]}" copy "$out" "$dst/_control" --include "qa_*"
    "${RC[@]}" moveto "$ROOT/02_En_proceso/$name" "$dst/_bruto"
    echo "Entregado en 03_Listos/$name" ;;
  fail)
    name="$1"; msg="${2:-error sin detalle}"
    printf '%s\n%s\n' "$(date -u +%FT%TZ)" "$msg" | "${RC[@]}" rcat "$ROOT/02_En_proceso/$name/ERROR.txt"
    echo "Marcado con error: $name" ;;
  *)
    sed -n '2,20p' "$0"; exit 1 ;;
esac
