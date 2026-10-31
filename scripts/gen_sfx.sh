#!/usr/bin/env bash
# Genera efectos de sonido básicos con ffmpeg (síntesis propia, sin licencias de terceros).
# Son el piso del sistema: si la librería de Drive tiene un sonido con el mismo nombre, se usa ese.
# Uso: scripts/gen_sfx.sh [carpeta_destino]   (default: library/sonidos-base)
set -euo pipefail
OUT="${1:-$(dirname "$0")/../library/sonidos-base}"
mkdir -p "$OUT"
gen() { ffmpeg -v error -y -f lavfi -i "$2" ${3:-} -ar 48000 -ac 2 "$OUT/$1.wav"; }

# whoosh: ruido rosa filtrado con entrada y salida suaves
gen whoosh "anoisesrc=color=pink:d=0.55:a=0.9" "-af highpass=f=300,lowpass=f=5000,afade=t=in:d=0.28:curve=exp,afade=t=out:st=0.3:d=0.25,volume=0.8"
# pop: blip ascendente corto, para textos que aparecen
gen pop "aevalsrc=0.8*sin(2*PI*(500+3500*t)*t)*exp(-38*t):d=0.14"
# impacto: golpe grave para el hook (blanco y negro, número)
gen impacto "aevalsrc=0.95*sin(2*PI*52*t)*exp(-3.5*t)+0.45*sin(2*PI*104*t)*exp(-7*t):d=1.3" "-af alimiter=limit=0.95"
# riser: sube antes de un giro o remate
gen riser "aevalsrc=0.35*sin(2*PI*(180+600*t*t)*t)*(t/1.6):d=1.6" "-af afade=t=out:st=1.5:d=0.1"
# tick: check de una lista
gen tick "aevalsrc=0.6*(sin(2*PI*1320*t)+0.6*sin(2*PI*1980*t))*exp(-30*t):d=0.18"
# scratch: disco rayado para el hook congelado
gen scratch "aevalsrc=0.5*sin(2*PI*(1400-1300*t/0.45)*t)*exp(-2*t):d=0.45" "-af highpass=f=200"
echo "SFX en $OUT: $(ls "$OUT" | tr '\n' ' ')"
