---
name: editar-video
description: >-
  Edita automáticamente videos en bruto (cámara a cámara, talking head) y los convierte en
  Reels/TikTok/Shorts listos para publicar, con 3 variantes de hook. Usala cuando haya videos en
  01_Pendientes de Google Drive, cuando el usuario pida "editá este video", "procesá los pendientes",
  "armá el reel de esta grabación", cuando corra la tarea programada de edición, o cuando haya que
  rehacer o ajustar un video ya editado.
---

# editar-video

Convierte una carpeta con el bruto (y opcionalmente el guion) en `final_A/B/C.mp4` listos para publicar.
Claude decide la edición; los scripts la ejecutan. Nunca edites el video "a mano" con ffmpeg suelto: todo pasa por `plan.json` para que sea repetible.

## 0. Preparar la sesión (siempre)

```bash
bash scripts/setup.sh          # idempotente, segundos si el entorno ya lo tiene
```

Leé antes de decidir nada: `rules/reglas_de_edicion.md`, `rules/plan.md`, `rules/estilos_hook.md`, `rules/efectos.md`, `marca/historial.md` (si existe) y `marca/voice.md`.

## 1. Traer el trabajo

- **Desde Drive** (modo normal y tarea programada):
  ```bash
  scripts/drive.sh check                 # falla con código 2 si falta configurar Drive
  scripts/drive.sh library               # librería de sonidos, música, etc.
  export EDICION_LIBRARY=~/.cache/edicion/library
  scripts/drive.sh list                  # una carpeta por video
  scripts/drive.sh claim <carpeta>       # la mueve a 02_En_proceso y la baja; imprime la ruta local
  ```
  Procesá de a una carpeta, de punta a punta, antes de tomar la siguiente.
- **Archivo local** (el usuario lo subió a la sesión): creá una carpeta `~/trabajo/<fecha_tema>/` y poné el video ahí.

## 2. Transcribir y analizar

```bash
scripts/prep.sh <carpeta>
```
Deja en `<carpeta>/_work/`: `transcript.md` (frases numeradas con ids de palabra y lo que se corta solo tachado), `analysis.json`, `words.json` y `frames.jpg` (12 cuadros del bruto).

## 3. Escribir el plan (la parte que importa)

Leé `transcript.md` completo, mirá `frames.jpg` (encuadre, dónde está la cara, luz) y, si existe, `guion.md` o `brief.txt` de la carpeta. Escribí `<carpeta>/plan.json` siguiendo `rules/plan.md`:

1. Las 3 frases más fuertes de TODA la transcripción → hooks A, B, C con estilos distintos (y distintos al último video del historial). Si el guion trae 3 tomas de hook, usalas.
2. El cuerpo: solo lo que lleva al remate. 15–45 s en total.
3. `cortar`: relleno, tomas malas, repeticiones que el automático no vio (mirá palabras repetidas como "do doing").
4. `correcciones`: nombres propios y errores del transcriptor (países, marcas, nombres).
5. Un evento visual cada 3–5 s: tarjetas, `numero`, `lista`, zooms. Con motivo, no por llenar.
6. Las marcas del guion (`[ZOOM]`, `[EFECTO: ...]`, `[SFX: ...]`, `[TEXTO: ...]`) pasan al plan ancladas a la palabra más cercana.

Si el bruto no tiene un hook usable o el audio es malo, no inventes: marcá el video con `scripts/drive.sh fail <carpeta> "<motivo>"` y seguí con el próximo.

## 4. Armar, renderizar y revisar

```bash
python3 scripts/build.py <carpeta> --variant A --quality draft    # prueba rápida de una variante
python3 scripts/qa.py <carpeta>/salida/final_A.mp4 --edl <carpeta>/_work/variante_A/edl.json
```
Mirá la hoja de contacto `salida/qa_final_A.jpg` con la herramienta de lectura de imágenes. Buscá: texto tapado o fuera de la zona segura, subtítulos desfasados, un hook que no se lee en el primer cuadro, cortes bruscos en medio de una palabra, tarjetas que se pisan con la lista. Corregí el plan y repetí hasta que esté bien.

Cuando A está bien, el render final de las tres:
```bash
python3 scripts/build.py <carpeta>                 # calidad "delivery", las 3 variantes + miniatura
for v in A B C; do python3 scripts/qa.py <carpeta>/salida/final_$v.mp4 --edl <carpeta>/_work/variante_$v/edl.json; done
```
`qa.py` sale con código 1 si hay un problema (resolución, códecs, volumen fuera de −14 LUFS, cuadros negros o congelados no buscados). No entregues con problemas abiertos.

Tiempos de referencia (4 vCPU): transcribir 60 s de bruto ≈ 10 s; renderizar 25 s de video ≈ 40–70 s por variante.

## 5. Entregar

```bash
scripts/drive.sh deliver <carpeta>
```
Sube `final_vertical.mp4` (variante A), `variante_hook_B.mp4`, `variante_hook_C.mp4`, `miniatura.png` y `notas.txt` a `03_Listos/<carpeta>/`, y archiva el bruto en `_bruto/`.

Después agregá una línea a `marca/historial.md` (fecha, carpeta, estilo de A/B/C, duración) y hacé commit de ese archivo; es lo que permite rotar estilos entre sesiones.

## Ajustes técnicos

- Los efectos visuales son HTML + GSAP renderizados con HyperFrames. Para crear un efecto nuevo, seguí `rules/efectos.md` y las skills `/hyperframes` y `/hyperframes-registry`. Respetá el contrato de HyperFrames: tiempos deterministas, transformaciones en contenedores y nunca en el `<video>`, y tratamientos de imagen con ffmpeg o `media-treatment`, no con filtros CSS.
- Para abrir el proyecto de una variante y ajustarlo a mano: `_work/variante_X/index.html`; re-render con `node_modules/.bin/hyperframes render` dentro de esa carpeta.
- Transcripción: Parakeet (inglés, local). Para otro idioma, `EDICION_ASR=whisper` (necesita acceso a huggingface.co).
- Nunca subas videos, audios ni credenciales al repo.
