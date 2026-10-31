# El plan de edición (`plan.json`)

Es la única decisión creativa del proceso: Claude lo escribe leyendo `_work/transcript.md`, `_work/frames.jpg` y el guion, y `scripts/build.py` lo ejecuta. Todo se ancla a **ids de palabra** (`w12`) de la transcripción, así los cortes nunca desfasan efectos ni subtítulos.

## Campos

| Campo | Qué es | Obligatorio |
| --- | --- | --- |
| `titulo` | Nombre corto del video | no |
| `fuente` | Archivo del bruto (default `camara.mp4`) | no |
| `hooks` | Lista de 1 a 3 variantes: `{id, estilo, rango: [wDesde, wHasta], texto}` | sí |
| `cuerpo` | Lista ordenada de rangos `[wDesde, wHasta]` que forman el video después del hook | sí |
| `repetir_hook_en_cuerpo` | `true` si la frase del hook también debe sonar en el cuerpo (default `false`) | no |
| `cortar` | Ids extra a eliminar (relleno, tomas malas) | no |
| `no_cortar` | Ids que el corte automático marcó pero hay que conservar | no |
| `correcciones` | `{"w120": "Uruguay,"}` corrige el texto de una palabra en los subtítulos | no |
| `palabras_clave` | Palabras que van en color de acento en los subtítulos | no |
| `tarjetas` | `{en: wId, dur: s, texto, sfx?}`: cartel de máx. 6 palabras arriba | no |
| `efectos` | `lista` o `numero` (ver abajo) | no |
| `zooms` | `{en: wId, tipo: "suave" \| "punch"}` | no |
| `sfx` | `{en: wId, nombre: "whoosh", vol?: 0.6}` además de los automáticos | no |
| `musica` | Ruta dentro de la librería, ej. `musica/lofi-01.mp3` | no |
| `subtitulos` | `{color, acento}` para cambiar colores | no |

### Efectos implementados
- `{"tipo": "lista", "en": "w40", "titulo": "3 things", "items": ["A","B","C"], "items_en": ["w41","w45","w49"], "dur": 5}`: panel con ticks que aparecen cuando decís cada ítem (si no hay `items_en`, se reparten).
- `{"tipo": "numero", "en": "w50", "texto": "$3,000", "dur": 1.8}`: número gigante con pop.

### Estilos de hook implementados
`bn-dramatico`, `numero-impactante`, `stop-doing`, `pantalla-negra`, `congelado`, y `titular` (default: sirve para curiosidad, pregunta, polémica, historia y resultado primero). Detalle en `rules/estilos_hook.md`.

## Ejemplo

```json
{
  "titulo": "3 countries trust me",
  "hooks": [
    {"id": "A", "estilo": "bn-dramatico", "rango": ["w109", "w114"], "texto": "They trust me with their business"},
    {"id": "B", "estilo": "numero-impactante", "rango": ["w109", "w114"], "texto": "3 countries trust me"},
    {"id": "C", "estilo": "pantalla-negra", "rango": ["w53", "w64"]}
  ],
  "cuerpo": [["w53", "w70"], ["w71", "w99"], ["w109", "w138"]],
  "cortar": ["w115", "w116", "w117"],
  "correcciones": {"w120": "Uruguay,"},
  "tarjetas": [{"en": "w85", "dur": 2.0, "texto": "Many people trust me"}],
  "efectos": [{"tipo": "lista", "en": "w118", "titulo": "Clients in",
               "items": ["USA", "Uruguay", "Australia"], "items_en": ["w119", "w120", "w125"]}],
  "zooms": [{"en": "w88", "tipo": "suave"}, {"en": "w136", "tipo": "punch"}],
  "palabras_clave": ["trust", "operations"],
  "musica": "musica/lofi-01.mp3"
}
```

## Cómo pensar el plan
1. Leer el guion (si hay) y la transcripción entera. Marcar las 3 frases más fuertes.
2. Elegir el cuerpo: solo lo que empuja hacia el remate. Si sobra, cortar rangos enteros.
3. Elegir 3 estilos distintos para A, B, C. A es el que mejor encaja con la frase.
4. Ubicar un evento visual cada 3–5 s del video final: tarjetas en ideas clave, `numero` en cifras, `lista` en enumeraciones, zooms en frases fuertes y remates.
5. Correcciones: nombres propios y palabras que el transcriptor escribió mal.
6. Si el guion trae marcas (`[ZOOM]`, `[EFECTO: ...]`, `[SFX: ...]`, `[TEXTO: ...]`), cada una se convierte en una entrada del plan anclada a la palabra más cercana.
