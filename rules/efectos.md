# Efectos

## Implementados en `build.py`
| Efecto | En el plan | Qué hace |
| --- | --- | --- |
| Subtítulos palabra por palabra | automático | Grupos de 2–3 palabras, clave en acento, pop de entrada |
| Tarjeta | `tarjetas` | Cartel amarillo arriba, máx. 6 palabras, con pop |
| Lista con ticks (tick list) | `efectos: lista` | Panel de vidrio oscuro, cada ítem entra con su tick y sonido cuando lo decís |
| Número gigante | `efectos: numero` | Cifra enorme en acento con pop |
| Zoom suave / punch-in | `zooms` | Escala en un contenedor del video; vuelve a 100 % en el siguiente corte |
| Zoom out | `zooms: out` | Arranca cerca (120 %) y se abre en 0,9 s: revela el lugar |
| Zoom lento | `zooms: lento` | Empuje continuo de 100 a 110 % hasta el próximo corte (intros, frases largas) |
| Shake | `zooms: shake` | Temblor de cámara que se apaga en 0,3 s, con `rumble` (remates, golpes) |
| Transición whip | `transiciones: whip` | La imagen sale de golpe hacia un lado y entra desde el otro, con estela blanca y sonido `whip` |
| Transición flash | `transiciones: flash` | Destello blanco sobre el corte, sonido `flash` |
| Transición zoom | `transiciones: zoom` | Zoom hacia adentro antes del corte y se abre después (zoom-through), sonido `swoosh-up` |
| Transición glitch | `transiciones: glitch` | Saltos horizontales y franjas rojo/cian, sonido `glitch-02` |
| Transición light leak | `transiciones: light-leak` | Dos manchas de luz cálida en modo screen (overlays de la librería), sonido `flash` |
| Reencuadre automático | automático | Si pasan más de 4,5 s sin cambio, zoom leve |
| Blanco y negro + grano | hook `bn-dramatico` | Tratamiento con ffmpeg sobre el tramo del hook |
| Congelado | hook `congelado` | Cuadro congelado 1 s antes del hook |
| Sonidos | automático + `sfx` | 23 sonidos en `_Recursos/sonidos/` (ver `library/README.md`); cualquiera se usa por nombre en `sfx` |
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

## Cómo elegir transiciones
- No en todos los cortes: una cada 6–10 s, en los cambios de tema o de lugar. Los cortes dentro de una misma idea van secos (jump cut).
- `whip` y `zoom` para energía; `flash` para remates y para pasar del blanco y negro a color; `glitch` para caos, error o mito; `light-leak` para momentos personales o cálidos.
- No repetir la misma transición dos veces seguidas en un video.
