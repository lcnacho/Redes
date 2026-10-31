# Sistema de edición automática de video

Convierte videos grabados en bruto en Reels, TikToks y Shorts editados (1080×1920), con 3 variantes de hook, sin que la PC de Nacho esté prendida. Corre en sesiones cloud de Claude Code; lo permanente vive en este repo (código, reglas, skills) y en Google Drive (videos y librería de recursos).

Contenido en inglés o español (el transcriptor detecta el idioma), nicho negocios y emprendimiento desde China. Referencia de estilo: @jackbloomfield.

## Skills
- `/editar-video`: el flujo completo, de Drive a Drive. Empezá siempre por acá para editar.
- `/guion-reel`: guiones con 3 hooks y marcas para el editor (usa `/ig-reel`, `/ig-human`, `/ig-viral`).
- `/hyperframes`, `/hyperframes-cli`, `/hyperframes-registry`, `/media-use`: skills oficiales de HyperFrames (HTML → video) para crear efectos nuevos.

## Estructura
```
scripts/setup.sh       instala todo (ffmpeg, sherpa-onnx + Parakeet, rclone, yt-dlp, HyperFrames)
scripts/drive.sh       Drive: check, list, library, claim, deliver, fail
scripts/prep.sh        normaliza el bruto, transcribe (transcribe.py) y analiza cortes (analyze.py)
scripts/build.py       plan.json → corte con ffmpeg + composición HyperFrames → render → master −14 LUFS
scripts/qa.py          control de calidad + hoja de contacto para revisar
scripts/gen_sfx.sh     efectos de sonido base sintetizados (sin licencias de terceros)
rules/                 reglas de edición, formato del plan, estilos de hook, efectos
marca/                 voz de Nacho (voice.md), historial de videos, swipe file
library/               README de la librería de Drive, vendor/gsap.min.js
docs/                  configurar Drive, disparo automático
```

## Flujo
Drive `01_Pendientes/<fecha_tema>/` → `drive.sh claim` → `prep.sh` → Claude escribe `plan.json` → `build.py` → `qa.py` (y mirar la hoja de contacto) → `drive.sh deliver` → `03_Listos/<fecha_tema>/`.

## Reglas para trabajar en este repo
- Al empezar una sesión: `bash scripts/setup.sh`.
- Nunca subir al repo videos, audios, renders, la librería de Drive ni credenciales. Drive se configura con variables de entorno (`docs/configurar-drive.md`).
- Las decisiones de edición van en `plan.json`, no en comandos sueltos: así todo se puede repetir y ajustar.
- Un efecto nuevo se agrega a `build.py` como un `tipo` de `efectos`, se documenta en `rules/efectos.md` y se prueba renderizando antes de usarlo en un video real.
- HyperFrames está fijado en `package.json`. GSAP se sirve local (`library/vendor/gsap.min.js`), no desde un CDN.
- Límites del entorno: 4 vCPU, 16 GB RAM, 30 GB disco, cada sesión arranca de cero. Procesar los videos de a uno y borrar `_work/` de los ya entregados si falta disco.
