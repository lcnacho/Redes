# Reglas de edición

Las sigue Claude al escribir cada `plan.json`. Las aplica `scripts/build.py` donde se puede automatizar; el resto depende de las decisiones del plan.
Contenido en inglés. Nicho: negocios y emprendimiento desde China. Referencia de estilo: @jackbloomfield.

## Formato de salida
- 1080×1920, 9:16, H.264 + AAC, 30 fps, 12 Mbps objetivo. Volumen final −14 LUFS, pico −1,5 dBTP. *(automático)*
- Todo texto importante dentro del recuadro central de 856 px de ancho (x 112–968) y entre y 168 y 1330. *(automático: hook arriba ~y 330, subtítulos ~y 1110)*
- Exportar maestro limpio, sin marca de agua. Se sube por separado a cada plataforma.

## Hook (0–3 s)
1. Leer toda la transcripción y marcar las 3 frases más fuertes como candidatas. La mejor casi nunca es la primera que se dice.
2. Hacer 3 variantes de hook (A, B, C) con estilos distintos del catálogo (`rules/estilos_hook.md`). A es la apuesta principal.
3. Cero saludos, nombre o intro antes del hook.
4. Texto del hook en pantalla: menos de 10 palabras. Tarjetas: máximo 6 palabras.
5. Si el guion trae 3 tomas de hook grabadas, usar esas como rangos de A, B y C.
6. No repetir el mismo estilo de hook en dos videos seguidos (mirar `marca/historial.md`).

## Estructura
hook (0–3 s) → contexto (3–8 s, una frase de por qué importa) → cuerpo (un cambio visual cada 3–5 s) → remate (lo que prometió el hook) → cierre en loop (la última frase empalma con la primera cuando el contenido lo permite).

## Cortes
- Pausas de más de 0,3 s, muletillas (um, uh) y reinicios ("you want you want") se cortan solos. *(automático: analyze.py)*
- Claude revisa la transcripción y agrega a `cortar` lo que el automático no ve: tomas repetidas largas, frases que no suman, "like you know" de relleno, el final de una idea que se repite.
- Duración: la más corta que cumpla el hook. Shorts de 15–45 s. Recortar sin piedad antes que rellenar.

## Ritmo y efectos
- Nunca más de 5 s sin un cambio visual (corte, zoom, texto o efecto). *(automático: si hay un hueco de más de 4,5 s, build.py mete un reencuadre suave)*
- Zoom suave (112 %) en frases clave; punch-in (122 %) en remates. Nunca dos zooms seguidos.
- Cada efecto de sonido atado a un texto, una transición o un remate. Sin dos golpes a menos de 0,35 s. *(automático)*
- Tarjetas: una cada 6–8 s como máximo en un video de menos de un minuto.
- Números, listas y conceptos clave aparecen escritos (efectos `numero` y `lista`).
- Cuidado con el exceso: un efecto sin motivo cansa. Si no está atado a lo que se dice, no va.

## Subtítulos
- Palabra por palabra en grupos de 2–3, centrados, Inter Black 92 px, blancos con sombra. *(automático)*
- Palabra clave en color de acento (amarillo #FFD400 por defecto). Números y montos siempre en acento. Las palabras de `palabras_clave` también.
- Corregir errores de transcripción con `correcciones` (nombres propios, marcas, países).

## Música
- De fondo, con ducking automático: baja cuando hay voz y sube en las pausas. *(automático)*
- Solo música de la librería con licencia comercial sin atribución (ver `library/README.md`). Nunca música comercial.

## Registro
- `salida/notas.txt` guarda estilo de hook, texto, duración y cortes de cada variante. *(automático)*
- Agregar una línea a `marca/historial.md` por video entregado: fecha, carpeta, estilo de hook de cada variante, palabras clave.
- Cuando haya métricas en la hoja (retención a 3 s, % visto, envíos), usar más los estilos que mejor retienen.
