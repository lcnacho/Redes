# Librería de recursos

Los archivos viven en Drive (`Edicion automatica/_Recursos/`), no en el repo. `scripts/drive.sh library` los baja a `~/.cache/edicion/library` y `build.py` los busca ahí (variable `EDICION_LIBRARY`) antes que en `library/` del repo.

```
_Recursos/
├── catalogo.json      qué hay y para qué sirve cada cosa (Claude lo lee para elegir)
├── licencias.md       de dónde salió cada archivo y su licencia
├── sonidos/           whoosh.wav, pop.wav, impacto.wav, riser.wav, tick.wav, scratch.wav, ...
├── musica/            pistas de fondo (el plan las nombra: "musica/lofi-01.mp3")
├── overlays/          luces, grano, polvo (video con alfa o en modo screen)
├── luts/              .cube para gradear
├── animaciones/       Lottie (.json)
├── fuentes/           .woff2 / .ttf
├── marca/             logo, colores
└── efectos-propios/
```

## Kit inicial (ya está en Drive)
`scripts/build_library.py` lo arma y se sube con `rclone copy`. Todo es propio o con licencia libre:

| Carpeta | Qué hay | Origen y licencia |
| --- | --- | --- |
| `sonidos/` | 23 efectos: whoosh (3), whip, swoosh-up, hit-whoosh, pop (3), click (2), impacto (2), riser (2), rumble, flash, glitch (2), tick, ding, error, scratch | Sintetizados acá, propios |
| `musica/` | `base-tranquila-provisoria.mp3` (84 bpm, lo-fi) y `base-tension-provisoria.mp3` (100 bpm) | Sintetizadas, propias. **Provisorias**: reemplazar por música de Pixabay Music |
| `overlays/` | `grano-01.mp4`, `light-leak-01.mp4`, `light-leak-02.mp4` | Generados con ffmpeg, propios |
| `luts/` | `calido.cube`, `teal-orange.cube`, `bn-contraste.cube` | Generados, propios |
| `iconos/` | 20 íconos Lucide (check, truck, ship, factory, dollar-sign...) | Lucide, ISC |
| `fuentes/` | Anton, Bebas Neue, Montserrat 800/900 | Google Fonts vía @fontsource, OFL |
| `animaciones/` | `lottie.min.js` (reproductor) | lottie-web, MIT |

Lo que falta y hay que subir a mano (desde el entorno cloud no se llega a esos sitios): música real de Pixabay Music, sonidos de Pixabay/Mixkit si se quieren más naturales, animaciones Lottie.

## Cómo se usan los sonidos
`build.py` busca `sonidos/<nombre>.(wav|mp3|ogg|m4a)` en la librería de Drive; si no está, usa la versión sintetizada de `library/sonidos-base/` (la genera `scripts/gen_sfx.sh`). Para mejorar un sonido, subí a `_Recursos/sonidos/` un archivo con el mismo nombre: no hay que tocar código.

Nombres que usa el sistema hoy: `whoosh` (transiciones), `pop` (textos), `impacto` (hooks fuertes), `riser` (antes de un giro), `tick` (listas), `scratch` (hook congelado).

## catalogo.json (formato)
```json
{
  "musica": [
    {"archivo": "musica/lofi-01.mp3", "bpm": 90, "energia": "baja", "mood": ["calmo", "negocios"], "licencia": "Pixabay"}
  ],
  "sonidos": [
    {"archivo": "sonidos/whoosh.wav", "uso": "transición", "licencia": "Mixkit"}
  ]
}
```

## Fuentes permitidas (uso comercial sin atribución)
| Tipo | Fuente | Notas |
| --- | --- | --- |
| SFX | Pixabay, Mixkit, Sonniss GDC bundles, Kenney (CC0) | Evitar BBC SFX (no comercial) y Zapsplat gratis (pide atribución) |
| Música | Pixabay Music al inicio; Epidemic Sound si se monetiza | Nunca música comercial |
| Overlays | Mixkit, FX Elements (gratis) | |
| Animaciones | LottieFiles (licencia Lottie Simple) | Revisar cada una |
| Emojis | Fluent Emoji de Microsoft (MIT) | |

Registrar cada archivo nuevo en `licencias.md`: archivo, fuente, URL, licencia, fecha.
