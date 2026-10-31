# Conectar Google Drive

El sistema lee y escribe en Drive con rclone. La credencial vive en la configuración del entorno cloud, nunca en el repo ni en el chat.

## 1. Sacar el token (una vez, en tu PC)

1. Instalá rclone: https://rclone.org/downloads/ (en Windows, el `.zip`; en Mac, `brew install rclone`).
2. En una terminal:
   ```
   rclone authorize "drive"
   ```
   Se abre el navegador, entrás con tu cuenta de Google y aceptás.
3. La terminal imprime un bloque que empieza con `{"access_token":` y termina con `}`. Copialo entero (incluye un `refresh_token`, que es el que permite renovarlo solo).

## 2. Guardarlo en el entorno cloud

En Claude Code (web o app): menú del entorno cloud en la barra de título de la sesión → **Edit** → variables de entorno. Agregá:

```
RCLONE_CONFIG_GDRIVE_TYPE=drive
RCLONE_CONFIG_GDRIVE_SCOPE=drive
RCLONE_CONFIG_GDRIVE_TOKEN=<el bloque {"access_token": ...} completo, en una sola línea>
EDICION_DRIVE_ROOT=Edicion automatica
```

`EDICION_DRIVE_ROOT` es el nombre de la carpeta raíz en "Mi unidad". Si la querés en otro lado, poné la ruta (ej. `Contenido/Edicion automatica`).

Las sesiones nuevas toman las variables. Para probar: `scripts/drive.sh check`. Crea las carpetas `01_Pendientes`, `02_En_proceso`, `03_Listos` y `_Recursos` si no existen, y lista lo pendiente.

## 3. Setup script del entorno

En la misma pantalla, en **Setup script**, pegá el contenido de `scripts/setup.sh`. Así cada sesión arranca con ffmpeg, Parakeet, rclone y HyperFrames instalados. Si no lo pegás, igual funciona: la skill de edición lo corre al empezar y tarda un par de minutos más (baja un modelo de 480 MB).

## Red

Alcanza con la red por defecto (Trusted): el sistema usa GitHub, PyPI, npm y las APIs de Google. Solo hace falta ampliar la red si se quiere usar Whisper (`EDICION_ASR=whisper`), que baja modelos de huggingface.co.

## Seguridad

El token da acceso a todo tu Drive. Si preferís limitarlo, creá una cuenta de Google solo para esto, compartile la carpeta "Edicion automatica" y sacá el token con esa cuenta. Para revocarlo: https://myaccount.google.com/permissions → rclone → quitar acceso.
