# 🎵 ytMusicDownloader

[![Python](https://img.shields.io/badge/Language-Python-3776AB.svg)](https://www.python.org/)
[![yt-dlp](https://img.shields.io/badge/Dependency-yt--dlp-FF0000.svg)](https://github.com/yt-dlp/yt-dlp)
[![FFmpeg](https://img.shields.io/badge/Dependency-FFmpeg-007800.svg)](https://ffmpeg.org/)

Una colección de herramientas en **Python** para descargar, organizar y sincronizar música desde **YouTube Music** con un enfoque en la calidad de los metadatos y la gestión inteligente de archivos.

> [!NOTE]
> Este repositorio ha sido migrado de Bash a Python para ofrecer un mejor rendimiento (multiprocesamiento) y una gestión de errores más robusta. Los scripts originales en Bash se mantienen en la carpeta `bash/` de forma secundaria.

## ✨ Características Principales

- **Descarga Inteligente (Python)**: Soporte para listas de reproducción completas o canciones individuales usando multiprocesamiento para escanear la biblioteca de forma ultrarrápida.
- **Metadatos Enriquecidos**: Incrusta automáticamente título, artista y un comentario con el `video_id` persistente para evitar duplicados.
- **Portadas Cuadradas (1:1)**: Descarga la mejor miniatura disponible (maxresdefault), la recorta a formato cuadrado (álbum) y la incrusta en el MP3.
- **Gestión de Duplicados**: 
  - Compara el ID del video incrustado en los metadatos, permitiendo renombrar archivos sin perder el rastreo.
  - Manejo inteligente de colisiones de nombres (añade numeración automática sin conflictos).
- **Compatibilidad Extrema (ID3v2.3)**: Asegura que las etiquetas se vean perfectas en reproductores Android/Musicolet.
- **Sincronización Avanzada**: Herramienta de auditoría para comparar tu carpeta local con cualquier playlist online.

## 🛠️ Requisitos

Asegúrate de tener instaladas las siguientes herramientas:

- **Python 3.8+** (Recomendado)
- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: El motor de descarga.
- **FFmpeg**: Para el procesamiento de audio e imágenes.
- **Node.js**: Requerido por `yt-dlp` para resolver desafíos de bot-protection.

```bash
# Instalación de dependencias (Debian/Ubuntu)
sudo apt update && sudo apt install ffmpeg curl nodejs
pip install yt-dlp
```

## 🚀 Modo de Uso

### 1. Descargando Música (Recomendado)
El programa principal descarga el audio en máxima calidad y organiza los archivos en `~/musica/`.

```bash
python3 descargar_playlist.py "<URL_YOUTUBE_MUSIC>" "[nombre_carpeta]"
```
- **URL**: Playlist o canción individual.
- **Carpeta** (opcional): Nombre del subdirectorio. Por defecto usa `na`.

### 2. Comparando Biblioteca Local
Compara qué canciones te faltan de una playlist o cuáles tienes de más.

```bash
python3 comparar_playlist.py "<URL_YOUTUBE_MUSIC>" "[nombre_carpeta]"
```

---

## 📁 Estructura del Proyecto

- `descargar_playlist.py`: Script principal de descarga (Python).
- `comparar_playlist.py`: Herramienta de auditoría (Python).
- `bash/`: Contiene los scripts originales en Bash (`descargarPlaylist.sh`, `compararPlaylist.sh`) como alternativa secundaria.
- `music.youtube.com_cookies.txt`: Archivo opcional de cookies para acceder a playlists privadas.

## 📝 Notas Técnicas
- **Caché de Metadatos**: Los scripts de Python generan un `.metadata_cache.json` en cada carpeta de música para acelerar exponencialmente las comparaciones futuras.
- **Uso de Cookies**: Coloca tu `cookies.txt` o `music.youtube.com_cookies.txt` en la raíz del proyecto para acceder a contenido privado.
- **Portadas**: Se procesan en `/tmp/` para mantener limpio el sistema.

---
*Desarrollado para amantes de la música que prefieren tener su colección organizada offline.* 🎧
