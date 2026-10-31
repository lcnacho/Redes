# Disparo automático

Objetivo: subís la carpeta del video a `01_Pendientes` desde el celular y, sin tocar nada más, aparece editado en `03_Listos`.

## Opción 1 (recomendada para empezar): tarea programada cada hora

Una tarea programada de Claude Code abre una sesión nueva en este repo cada hora y procesa lo pendiente. Si no hay nada, termina enseguida.

Prompt de la tarea:

```
Usá la skill /editar-video en modo automático: corré scripts/setup.sh, scripts/drive.sh check y
scripts/drive.sh list. Si no hay carpetas pendientes, terminá sin hacer nada más. Si hay, procesalas
de a una de punta a punta (claim, prep, plan, build, qa revisando la hoja de contacto, deliver).
Si una falla, marcala con drive.sh fail y seguí con la siguiente. Al final hacé commit y push de
marca/historial.md a la rama principal y resumí qué se entregó.
```

Requisitos antes de crearla: Drive configurado (`docs/configurar-drive.md`) y una primera prueba manual exitosa con un bruto real. Claude puede crear la tarea desde una sesión cuando se lo pidas.

## Opción 2 (más adelante): disparo al subir

Un Google Apps Script vigila `01_Pendientes` y, cuando aparece una carpeta nueva, dispara la tarea al momento en vez de esperar a la hora. Queda para después de que la opción 1 funcione: hay que confirmar cómo exponer el disparo de la tarea por API y guardar esa credencial en el script de Google.

## Costos y límites

Cada video usa una sesión de Claude con lectura de transcripción, varias imágenes de control y renders. Con Claude Pro conviene empezar con pocos videos por día y mirar el consumo. Si la tarea corre cada hora y casi siempre no hay nada, el costo de esas ejecuciones vacías es bajo pero no cero; se puede bajar a cada 3 horas.
