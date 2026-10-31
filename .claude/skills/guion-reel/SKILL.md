---
name: guion-reel
description: >-
  Escribe el guion de un Reel/TikTok/Short en inglés listo para grabar y para el editor automático:
  3 hooks puntuados (uno por estilo del catálogo), el guion hablado, el texto en pantalla y las marcas
  para el editor ([ZOOM], [EFECTO: ...], [SFX: ...], [TEXTO: ...]). Usala cuando el usuario pida un
  guion, "hacé un reel sobre X", ideas para grabar, o antes de grabar un video que va a pasar por
  la edición automática.
---

# guion-reel

Envuelve la skill `/ig-reel` (MIT, de Jake Schincariol) y la adapta al sistema: los guiones salen con
3 hooks que el editor puede usar como variantes A, B y C, y con marcas que se convierten en `plan.json`.

## Proceso

1. Leé `marca/voice.md` (cómo habla Nacho), `marca/swipe.md` si existe (lo que está funcionando, de `/ig-viral`),
   `marca/historial.md` (estilos de hook usados hace poco) y `rules/estilos_hook.md`.
2. Seguí el loop de `/ig-reel` (`.claude/skills/ig-reel/SKILL.md`) con estos cambios:
   - Los 3 hooks usan **estilos distintos** de `rules/estilos_hook.md`, y al menos uno distinto del último video.
   - Puntualos con `python3 .claude/skills/ig-reel/hookscore.py hooks.txt`. Menos de 50 = no hay hook todavía.
   - Medí el guion con `python3 .claude/skills/ig-reel/beats.py guion.txt --target 30 --wpm 160` y corregí cada aviso.
   - Pasalo por `/ig-human` antes de mostrarlo.
3. Contenido en **inglés**, con frases cortas que Nacho pueda decir naturalmente (no es nativo: evitá giros difíciles de pronunciar).
4. Nunca inventes cifras, clientes ni resultados. Si falta un número, dejá `{{número real}}` y avisá.

## Formato de salida (`guion.md`, va en la carpeta del video en Drive)

```markdown
# <tema>
duración objetivo: 30 s · estilo de A: bn-dramatico · B: numero-impactante · C: titular

## Hooks (grabar las 3 tomas al principio)
A [bn-dramatico] (86) "I lost $3,000 because nobody told me this."   pantalla: "NOBODY TOLD ME THIS"
B [numero-impactante] (74) "3 suppliers. 2 were fake."                 pantalla: "3 SUPPLIERS. 2 FAKE"
C [titular] (61) "Before you pay a factory in China, watch this." pantalla: "BEFORE YOU PAY A FACTORY"

## Guion
Context line that says why it matters. [TEXTO: Why it matters]
First point, one idea. [ZOOM]
Here are the three checks: [EFECTO: lista "3 checks" | business license | factory visit | sample]
...
Payoff line. [ZOOM: punch] [SFX: impacto]
Loop line that echoes the hook.
```

Marcas que entiende el editor:
| Marca | Se convierte en |
| --- | --- |
| `[ZOOM]` / `[ZOOM: punch]` | `zooms` suave / punch en esa frase |
| `[TEXTO: ...]` | `tarjetas` (máx. 6 palabras) |
| `[EFECTO: lista "título" \| a \| b \| c]` | `efectos: lista` |
| `[EFECTO: numero $3,000]` | `efectos: numero` |
| `[SFX: whoosh]` | `sfx` |

Al final, guardá el guion: si hay Drive, en la carpeta del video dentro de `01_Pendientes/<fecha_tema>/guion.md` (crearla con `rclone mkdir`); si no, mostralo en la conversación.
