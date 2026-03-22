#!/bin/bash

# Script to compare video IDs in a folder (~/musica/<folder_name>) with a YouTube Music playlist
# Reports matching IDs, songs in playlist but not in folder, and songs in folder but not in playlist

# Check if yt-dlp, ffprobe, and jq are installed
if ! command -v yt-dlp &> /dev/null || ! command -v ffprobe &> /dev/null || ! command -v jq &> /dev/null; then
    echo "Error: yt-dlp, ffmpeg (ffprobe), and jq must be installed."
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
COOKIES_FILE="$HOME/cookies.txt"  # Path to cookies file for age-restricted playlists

# Convert YouTube Music URL to YouTube URL
URL="${URL//music.youtube.com/youtube.com}"

# Check if music directory exists
if [ ! -d "$MUSIC_DIR" ]; then
    echo "Error: Directory $MUSIC_DIR does not exist."
    exit 1
fi

# Initialize arrays for comparison
declare -A folder_ids  # Video IDs in folder with filenames
declare -A playlist_ids  # Video IDs in playlist with titles
declare -a matches  # Matching video IDs
declare -a in_playlist_not_folder  # Songs in playlist but not in folder
declare -a in_folder_not_playlist  # Songs in folder but not in playlist

echo "Extrayendo IDs de video de la carpeta $MUSIC_DIR..."
# Extract video IDs from MP3 files in folder
for file in "$MUSIC_DIR"/*.mp3; do
    if [ -f "$file" ]; then
        file_id=$(ffprobe -v quiet -show_entries format_tags=comment -of json "$file" | jq -r '.format.tags.comment // ""' | grep -oE 'video_id=[^ ]*' | cut -d'=' -f2)
        if [ -n "$file_id" ]; then
            filename=$(basename "$file" .mp3)
            folder_ids["$file_id"]="$filename"
        fi
    fi
done

echo "Extrayendo IDs y títulos de la playlist..."
# Extract video IDs and titles from playlist
if [ -f "$COOKIES_FILE" ]; then
    playlist_data=$(yt-dlp --cookies "$COOKIES_FILE" --dump-json --flat-playlist --no-download "$URL" 2>/tmp/yt-dlp-verbose.log)
else
    playlist_data=$(yt-dlp --dump-json --flat-playlist --no-download "$URL" 2>/tmp/yt-dlp-verbose.log)
fi
if [ -z "$playlist_data" ]; then
    echo "Error: No videos found in playlist or invalid URL"
    cat /tmp/yt-dlp-verbose.log
    exit 1
fi

# Process each video in playlist
while IFS= read -r line; do
    video_id=$(echo "$line" | jq -r '.id')
    title=$(echo "$line" | jq -r '.title')
    if [ -n "$video_id" ] && [ -n "$title" ]; then
        playlist_ids["$video_id"]="$title"
    fi
done <<< "$playlist_data"

echo "Comparando IDs..."
# Compare IDs between folder and playlist
for id in "${!folder_ids[@]}"; do
    if [[ -n "${playlist_ids[$id]}" ]]; then
        matches+=("$id")
    else
        in_folder_not_playlist+=("${folder_ids[$id]}")
    fi
done

for id in "${!playlist_ids[@]}"; do
    if [[ -z "${folder_ids[$id]}" ]]; then
        in_playlist_not_folder+=("${playlist_ids[$id]}")
    fi
done

# Print report
echo -e "\nResumen de la comparación:"
echo "--------------------------"
echo "Número total de coincidencias: ${#matches[@]}"
if [ ${#matches[@]} -gt 0 ]; then
    echo "Coincidencias (IDs presentes en la carpeta y la playlist):"
    for id in "${matches[@]}"; do
        echo "- ${folder_ids[$id]} (ID: $id)"
    done
fi

echo -e "\nNúmero de canciones en la playlist pero no en la carpeta: ${#in_playlist_not_folder[@]}"
if [ ${#in_playlist_not_folder[@]} -gt 0 ]; then
    echo "Canciones en la playlist pero no en la carpeta:"
    for title in "${in_playlist_not_folder[@]}"; do
        echo "- $title"
    done
fi

echo -e "\nNúmero de canciones en la carpeta pero no en la playlist: ${#in_folder_not_playlist[@]}"
if [ ${#in_folder_not_playlist[@]} -gt 0 ]; then
    echo "Canciones en la carpeta pero no en la playlist:"
    for name in "${in_folder_not_playlist[@]}"; do
        echo "- $name"
    done
fi
