#!/bin/bash

# Check if at least the URL is provided
if [ -z "$1" ]; then
    echo "Uso: $0 <URL> [nombre_carpeta]"
    exit 1
fi

# Set variables
URL="$1"
FOLDER_NAME="${2:-na}"  # Default to 'na' if no folder name is provided
MUSIC_DIR="$HOME/musica/$FOLDER_NAME"
YT_URL=$(echo "$URL" | sed 's/music.youtube.com/youtube.com/')  # Convert YouTube Music URL to YouTube URL

# Create output directory if it doesn't exist
mkdir -p "$MUSIC_DIR"

# Initialize counters and arrays
downloaded=0
skipped=0
errors=()
duplicates=()

echo "Descargando playlist..."

# Check if the URL is a playlist or a single video
if [[ "$YT_URL" =~ "playlist?list=" ]]; then
    # Get playlist entries using yt-dlp and jq
    entries=$(yt-dlp --flat-playlist --dump-json "$YT_URL" | jq -r '. | "\(.id) \(.title)"')
    if [ -z "$entries" ]; then
        echo "Error: No se pudo obtener la lista de reproducción."
        exit 1
    fi
else
    # Treat as a single video
    video_id=$(echo "$YT_URL" | grep -oP 'v=\K[^&]+')
    title=$(yt-dlp --get-title "$YT_URL" 2>/dev/null | sed 's/[^[:alnum:]\ ]//g' | sed 's/\ \+/_/g' | tr '_' ' ')
    if [ -z "$video_id" ] || [ -z "$title" ]; then
        echo "Error: No se pudo obtener información del video."
        exit 1
    fi
    entries="$video_id $title"
fi

# Process each entry
while IFS= read -r line; do
    video_id=$(echo "$line" | awk '{print $1}')
    title=$(echo "$line" | cut -d' ' -f2- | sed 's/[^[:alnum:]\ ]//g' | sed 's/\ \+/_/g' | tr '_' ' ')  # Clean title for filename
    output_file="$MUSIC_DIR/$title.mp3"
    url_file="$MUSIC_DIR/$title.url"
    video_url="https://www.youtube.com/watch?v=$video_id"

    # Check for existing song
    if [ -f "$url_file" ] && grep -q "$video_id" "$url_file"; then
        echo "Omitida (ya existe): $title"
        ((skipped++))
        continue
    fi

    # Check for duplicate song names
    counter=1
    base_title="$title"
    while [ -f "$output_file" ] && ! grep -q "$video_id" "$url_file" 2>/dev/null; do
        title="$base_title ($counter)"
        output_file="$MUSIC_DIR/$title.mp3"
        url_file="$MUSIC_DIR/$title.url"
        duplicates+=("$title")
        ((counter++))
    done

    # Download the song
    if yt-dlp -x --audio-format mp3 --audio-quality 0 --embed-metadata --embed-thumbnail \
        --convert-thumbnails jpg --ppa "EmbedThumbnail+ffmpeg:-c:v mjpeg -vf crop=\"'if(gt(iw,ih),ih,iw)':'if(gt(iw,ih),ih,iw)'\"" \
        -o "$output_file" --download-archive "$MUSIC_DIR/archive.txt" "$video_url"; then
        echo "Descargada: $title"
        ((downloaded++))
        # Save video ID to .url file
        echo "$video_id" > "$url_file"
    else
        echo "Error al descargar: $title"
        errors+=("$title")
    fi
done <<< "$entries"

# Print summary
echo -e "\nResumen de la descarga:"
echo "----------------------"
echo "Canciones descargadas: $downloaded"
echo "Canciones omitidas (ya existían): $skipped"
echo "Canciones con error: ${#errors[@]}"
if [ ${#errors[@]} -gt 0 ]; then
    echo "Canciones con errores:"
    for error in "${errors[@]}"; do
        echo "- $error"
    done
fi
echo "Canciones con nombres duplicados (se añadieron con enumeración):"
if [ ${#duplicates[@]} -gt 0 ]; then
    for dup in "${duplicates[@]}"; do
        echo "- $dup"
    done
else
    echo "- Ninguna"
fi