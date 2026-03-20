#!/bin/bash

# Script to download YouTube Music playlists or single songs with yt-dlp
# Handles duplicates, embeds square cover art, and provides a summary

# Check if yt-dlp, ffmpeg, curl, and jq are installed
if ! command -v yt-dlp &> /dev/null || ! command -v ffmpeg &> /dev/null || ! command -v curl &> /dev/null || ! command -v jq &> /dev/null; then
    echo "Error: yt-dlp, ffmpeg, curl, and jq must be installed."
    exit 1
fi

# Check if at least one argument (URL) is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <YouTube Music URL> [folder_name]"
    exit 1
fi

URL="$1"
FOLDER_NAME="${2:-na}"  # Default to 'na' if no folder name provided
MUSIC_DIR="$HOME/musica/$FOLDER_NAME"
TEMP_DIR="/tmp/yt-dlp-temp"
MAX_RETRIES=3

# Convert YouTube Music URL to YouTube URL
URL="${URL//music.youtube.com/youtube.com}"

# Create music directory if it doesn't exist
mkdir -p "$MUSIC_DIR" || { echo "Error: Could not create directory $MUSIC_DIR"; exit 1; }
mkdir -p "$TEMP_DIR" || { echo "Error: Could not create temporary directory $TEMP_DIR"; exit 1; }

# Initialize counters and arrays for summary
downloaded=0
skipped=0
errored=0
declare -a errors=()
declare -a duplicates=()
declare -A filename_counts  # Associative array to track case-insensitive filename counts
declare -A existing_video_ids  # Associative array to cache video IDs of existing files

echo "Construyendo caché de IDs de video y nombres de archivo existentes..."
# Build cache of existing video IDs and filename counts
for file in "$MUSIC_DIR"/*.mp3; do
    if [ -f "$file" ]; then
        # Extract video ID
        file_id=$(ffprobe -v quiet -show_entries format_tags=comment -of json "$file" | jq -r '.format.tags.comment // ""' | grep -oE 'video_id=[^ ]*' | cut -d'=' -f2)
        if [ -n "$file_id" ]; then
            existing_video_ids["$file_id"]=1
        fi
        # Extract and process filename for duplicate tracking
        filename=$(basename "$file" .mp3)
        # Check if filename has a number like "(1)"
        if [[ "$filename" =~ ^(.*)\ ([0-9]+)$ ]]; then
            base_name="${BASH_REMATCH[1]}"
            number="${BASH_REMATCH[2]}"
            lowercase_name=$(echo "$base_name" | tr '[:upper:]' '[:lower:]')
            # Update filename_counts with the highest number
            if [[ -z "${filename_counts[$lowercase_name]}" || "${filename_counts[$lowercase_name]}" -lt "$number" ]]; then
                filename_counts["$lowercase_name"]="$number"
            fi
        else
            lowercase_name=$(echo "$filename" | tr '[:upper:]' '[:lower:]')
            # Initialize or ensure at least 0 for non-numbered filenames
            if [[ -z "${filename_counts[$lowercase_name]}" ]]; then
                filename_counts["$lowercase_name"]=0
            fi
        fi
    fi
done

echo "Descargando playlist..."

# Function to validate and fix URL
validate_url() {
    local url="$1"
    if [[ "$url" =~ ^tps:// ]]; then
        url="ht$url"
        echo "Fixed malformed URL: $url" >&2
    elif [[ ! "$url" =~ ^https:// ]]; then
        url="https://$url"
        echo "Fixed missing protocol in URL: $url" >&2
    fi
    echo "$url"
}

# Function to minimally clean filename (remove only filesystem-invalid characters)
clean_filename() {
    local name="$1"
    echo "$name" | tr -d '/\\:*?"<>|' | tr -s ' ' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

# Function to process a single video
process_video() {
    local video_url="$1"
    local attempt=1

    # Validate and fix URL
    video_url=$(validate_url "$video_url")
    if [[ ! "$video_url" =~ ^https://youtube.com/watch\?v= ]]; then
        errors+=("Invalid URL ($video_url)")
        ((errored++))
        return
    fi

    local video_id
    video_id=$(echo "$video_url" | grep -oE 'v=[^&]*' | cut -d'=' -f2)
    if [ -z "$video_id" ]; then
        errors+=("Could not extract video ID ($video_url)")
        ((errored++))
        return
    fi

    # Check if video ID exists in cache
    if [[ -n "${existing_video_ids[$video_id]}" ]]; then
        echo "Omitida (ya existe): $video_id"
        ((skipped++))
        return
    fi

    while [ $attempt -le $MAX_RETRIES ]; do
        # Get metadata for the video
        metadata=$(yt-dlp --dump-json --no-download "$video_url" 2>/dev/null)
        if [ $? -ne 0 ]; then
            errors+=("Failed to fetch metadata for $video_url (attempt $attempt/$MAX_RETRIES)")
            if [ $attempt -eq $MAX_RETRIES ]; then
                ((errored++))
                return
            fi
            ((attempt++))
            sleep 2
            continue
        fi

        # Extract title and clean it minimally for final filename
        title=$(echo "$metadata" | jq -r '.title')
        if [ -z "$title" ]; then
            errors+=("Unknown title ($video_url)")
            ((errored++))
            return
        fi
        final_title=$(clean_filename "$title")
        if [ -z "$final_title" ]; then
            final_title="track_$video_id"
        fi

        # Handle duplicate filenames (case-insensitive)
        lowercase_title=$(echo "$final_title" | tr '[:upper:]' '[:lower:]')
        base_filename="$MUSIC_DIR/$final_title"
        output_file="$base_filename.mp3"
        if [[ -n "${filename_counts[$lowercase_title]}" ]]; then
            counter=$((filename_counts[$lowercase_title] + 1))
            output_file="$base_filename ($counter).mp3"
            duplicates+=("$final_title ($counter)")
            filename_counts[$lowercase_title]=$counter
        else
            # Check if the base filename or numbered versions exist
            counter=1
            while [ -f "$output_file" ]; do
                existing_id=$(ffprobe -v quiet -show_entries format_tags=comment -of json "$output_file" | jq -r '.format.tags.comment // ""' | grep -oE 'video_id=[^ ]*' | cut -d'=' -f2)
                if [ "$existing_id" != "$video_id" ]; then
                    output_file="$base_filename ($counter).mp3"
                    duplicates+=("$final_title ($counter)")
                    filename_counts[$lowercase_title]=$counter
                    ((counter++))
                else
                    echo "Omitida (ya existe): $final_title"
                    ((skipped++))
                    return
                fi
            done
            filename_counts[$lowercase_title]=0
        fi

        # Download thumbnail and convert to square 1x1
        thumbnail_url=$(echo "$metadata" | jq -r '.thumbnail')
        thumbnail_file="$TEMP_DIR/$video_id.jpg"
        curl -s "$thumbnail_url" -o "$thumbnail_file"
        if [ -f "$thumbnail_file" ]; then
            # Get dimensions and crop to square
            dimensions=$(ffprobe -v quiet -show_entries stream=width,height -of json "$thumbnail_file" | jq -r '.streams[0] | [.width, .height] | min')
            ffmpeg -i "$thumbnail_file" -vf "crop=$dimensions:$dimensions" "$TEMP_DIR/$video_id_square.jpg" -y 2>/dev/null
        fi

        # Use video ID as temporary filename to avoid special character issues
        temp_output="$TEMP_DIR/$video_id.mp3"
        yt-dlp -x --audio-format mp3 --audio-quality 0 \
            --embed-metadata \
            --add-metadata \
            --metadata-from-title "%(title)s" \
            --postprocessor-args "-metadata comment=video_id=$video_id" \
            -o "$temp_output" \
            --default-search fixup_error \
            "$video_url" 2>/dev/null

        if [ $? -eq 0 ] && [ -f "$temp_output" ]; then
            # Embed thumbnail as cover art
            if [ -f "$TEMP_DIR/$video_id_square.jpg" ]; then
                ffmpeg -i "$temp_output" -i "$TEMP_DIR/$video_id_square.jpg" \
                    -c copy -map 0 -map 1 -metadata:s:v title="Album cover" \
                    -metadata:s:v comment="Cover (front)" "$output_file" -y 2>/dev/null
            else
                mv "$temp_output" "$output_file"
            fi
            if [ -f "$output_file" ]; then
                echo "Descargada: $final_title"
                ((downloaded++))
                # Add new video ID to cache
                existing_video_ids["$video_id"]=1
                break
            else
                errors+=("$final_title (failed to move file, attempt $attempt/$MAX_RETRIES)")
                if [ $attempt -eq $MAX_RETRIES ]; then
                    ((errored++))
                    break
                fi
                ((attempt++))
                sleep 2
            fi
        else
            errors+=("$final_title (download failed, attempt $attempt/$MAX_RETRIES)")
            if [ $attempt -eq $MAX_RETRIES ]; then
                ((errored++))
                break
            fi
            ((attempt++))
            sleep 2
        fi
    done

    # Clean up temporary files
    rm -f "$TEMP_DIR/$video_id.jpg" "$TEMP_DIR/$video_id_square.jpg" "$temp_output"
}

# Check if URL is a playlist or single video
if [[ "$URL" =~ list= ]]; then
    # Get list of video URLs from playlist with verbose output and deduplicate
    video_urls=$(yt-dlp --get-id --flat-playlist --verbose "$URL" 2>/tmp/yt-dlp-verbose.log | sort -u | sed 's|^|https://youtube.com/watch?v=|')
    if [ -z "$video_urls" ]; then
        echo "Error: No videos found in playlist or invalid URL"
        cat /tmp/yt-dlp-verbose.log
        exit 1
    fi

    # Process each video in the playlist
    while IFS= read -r video_url; do
        process_video "$video_url"
    done <<< "$video_urls"
else
    # Process single video
    process_video "$URL"
fi

# Print summary
echo -e "\nResumen de la descarga:"
echo "----------------------"
echo "Canciones descargadas: $downloaded"
echo "Canciones omitidas (ya existían): $skipped"
echo "Canciones con error: $errored"
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

# Clean up temporary directory
rm -rf "$TEMP_DIR"