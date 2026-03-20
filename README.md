# 🎵 ytMusicDownloader

[![Bash](https://img.shields.io/badge/Language-Bash-4EAA25.svg)](https://www.gnu.org/software/bash/)
[![yt--dlp](https://img.shields.io/badge/Dependency-yt--dlp-FF0000.svg)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/Dependency-FFmpeg-007800.svg)](https://ffmpeg.org/)

Una colección de potentes scripts en Bash para descargar, organizar y sincronizar música desde **YouTube Music** con un enfoque en la calidad de los metadatos y la gestión inteligente de archivos.

## ✨ Características Principales

- **Descarga Inteligente**: Soporte para listas de reproducción completas o canciones individuales.
- **Metadatos Enriquecidos**: Incrusta automáticamente título, artista y un comentario con el `video_id` persistente.
- **Portadas Cuadradas (1:1)**: A diferencia de otros descargadores, este script descarga la miniatura, la recorta a formato cuadrado (álbum) usando FFmpeg y la incrusta en el MP3.
- **Gestión de Duplicados**:
  - Evita re-descargar canciones comparando el ID del video incrustado en los archivos locales.
  - Manejo inteligente de nombres de archivo idénticos (añade numeración automática como `(1)`, `(2)` sin conflictos).
- **Sincronización y Comparación**: Herramienta para comparar tu biblioteca local con cualquier playlist online para detectar archivos faltantes.

---

## 🛠️ Requisitos

Asegúrate de tener instaladas las siguientes herramientas en tu sistema Linux:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: El motor de descarga.
- **FFmpeg**: Para la conversión de audio y procesamiento de imágenes.
- **curl**: Para la descarga de miniaturas.
- **jq**: Para el procesamiento de metadatos en formato JSON.

```bash
# Ejemplo de instalación en Debian/Ubuntu
sudo apt update && sudo apt install ffmpeg curl jq
# Para yt-dlp se recomienda seguir las instrucciones oficiales de su repo
```

---

## 🚀 Instalación y Configuración

1. **Clona el repositorio**:
   ```bash
   git clone git@github.com:Zinko5/ytMusicDownloader.git
   cd ytMusicDownloader
   ```

2. **Otorga permisos de ejecución**:
   ```bash
   chmod +x descargarPlaylist.sh compararPlaylist.sh
   ```

---

## 📖 Modo de Uso

### 1. Descargando Música
El script principal descarga el audio en máxima calidad (320kbps/V0) y organiza los archivos en carpetas dentro de `~/musica/`.

**Sintaxis:**
```bash
./descargarPlaylist.sh "<URL_YOUTUBE_MUSIC>" "[nombre_carpeta]"
```

- **URL**: Puede ser una playlist o una canción individual.
- **Nombre de carpeta** (opcional): Nombre del subdirectorio en `~/musica/`. Por defecto usa `na`.

**Ejemplo:**
```bash
./descargarPlaylist.sh "https://music.youtube.com/playlist?list=XXX" "MisFavoritos"
```

### 2. Comparando Biblioteca Local
Si quieres saber qué canciones te faltan de una playlist o qué canciones tienes de más, usa el script de comparación.

**Sintaxis:**
```bash
./compararPlaylist.sh "<URL_YOUTUBE_MUSIC>" "[nombre_carpeta]"
```

**Ejemplo:**
```bash
./compararPlaylist.sh "https://music.youtube.com/playlist?list=XXX" "MisFavoritos"
```

---

## 📁 Estructura del Proyecto

- `descargarPlaylist.sh`: Script de descarga avanzado con procesamiento de imágenes 1:1.
- `compararPlaylist.sh`: Herramienta de auditoría de biblioteca.
- `.gitignore`: Configurado para ignorar archivos temporales y descargas accidentales.
- `README.md`: Esta documentación.

## 📝 Notas Técnicas
- El script utiliza un **comentario de metadatos** especial (`video_id=...`) para rastrear el origen de cada archivo. Esto permite mover o renombrar los archivos sin que el script crea que debe descargarlos de nuevo.
- Las portadas se procesan en `/tmp/` para no dejar residuos en tu carpeta de música.

---
*Desarrollado para amantes de la música que prefieren tener su colección organizada offline.* 🎧
