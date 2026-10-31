# Efectos

## Implementados en `build.py`
| Efecto | En el plan | Qué hace |
| --- | --- | --- |
| Subtítulos palabra por palabra | automático | Grupos de 2–3 palabras, clave en acento, pop de entrada |
| Tarjeta | `tarjetas` | Cartel amarillo arriba, máx. 6 palabras, con pop |
| Lista con ticks (tick list) | `efectos: lista` | Panel de vidrio oscuro, cada ítem entra con su tick y sonido cuando lo decís |
| Número gigante | `efectos: numero` | Cifra enorme en acento con pop |
| Zoom suave / punch-in | `zooms` | Escala en un contenedor del video; vuelve a 100 % en el siguiente corte |
| Reencuadre automático | automático | Si pasan más de 4,5 s sin cambio, zoom leve |
| Blanco y negro + grano | hook `bn-dramatico` | Tratamiento con ffmpeg sobre el tramo del hook |
| Congelado | hook `congelado` | Cuadro congelado 1 s antes del hook |
| Sonidos | automático + `sfx` | whoosh, pop, impacto, riser, tick, scratch (base sintetizada; se reemplaza por la librería de Drive si hay un archivo con el mismo nombre) |
| Ducking de música | `musica` | La música baja cuando hay voz |

## Para construir (prioridad de la lista "17 video effects")
Cada uno se agrega a `build.py` como un nuevo `tipo` dentro de `efectos`. Antes de escribirlo a mano, buscar en el registro de HyperFrames (`npx hyperframes catalog --query "<efecto>" --json`, skill `/hyperframes-registry`): hay unos 450 bloques listos.

| Efecto | Idea de implementación | Firma |
| --- | --- | --- |
| graph rise | Gráfico de barras o línea que sube (registro: charts), datos en el plan | sí |
| glass text | Texto sobre panel de vidrio (ya existe la base en `lista`) | sí |
| pixel zoom | Zoom con pixelado al entrar, vía `media-treatment` | |
| punch-through cut | Zoom fuerte hacia un punto y corte al siguiente tramo | sí |
| frame pop | El video se achica a un marco con sombra y vuelve | sí |
| paper cut out | Recorte de la persona (`hyperframes remove-background`) con borde blanco | |
| phone frame | Captura de pantalla o b-roll dentro de un teléfono | sí |

Elegir 5–6 como firma visual del canal y usarlos siempre igual: eso construye identidad.

## B-roll (pendiente)
Si la carpeta del video tiene `broll/`, el plan podrá decir `{"broll": "broll/fabrica.mp4", "en": "w30", "dur": 2.5}` para tapar la cámara mientras sigue la voz. Hoy no está implementado.
