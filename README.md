# ytMusicDownloader

Conjunto de scripts para descargar listas de reproducción y canciones individuales de YouTube Music utilizando `yt-dlp`.

## Scripts incluidos:

- **descargarPlaylist.sh**: La versión más completa que maneja duplicados y recorta las portadas a formato cuadrado.
- **stableDescargarPlaylist.sh**: Una versión más básica y estable que utiliza un archivo de registro para evitar repetir descargas.
- **ver1Descargar.sh**: El prototipo inicial de los scripts anteriores.
- **compararPlaylist.sh**: Un script para comparar y procesar listas.

## Requisitos:

- `yt-dlp`
- `ffmpeg`
- `curl`
- `jq`
