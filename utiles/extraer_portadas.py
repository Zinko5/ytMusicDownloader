#!/usr/bin/env python3
import sys
import subprocess
import json
import hashlib
from pathlib import Path

# Add parent directory to path to use existing modularity
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    normalize_text, 
    clean_filename, 
    check_dependencies, 
    MUSIC_BASE_DIR
)

def get_image_hash(file_path):
    """Extracts the cover art to a buffer and returns its SHA256 hash and the data."""
    # Command to extract the first video stream (usually the cover art in MP3s) to stdout
    # -an: no audio, -vcodec copy: copy video stream, -f image2pipe: output to pipe
    cmd = [
        'ffmpeg', '-i', str(file_path),
        '-map', '0:v:0',  # Select the first video stream
        '-f', 'image2pipe',
        '-vcodec', 'mjpeg', # Force mjpeg for consistency if possible, or just copy
        'pipe:1'
    ]
    
    try:
        # We try to extract as is first
        res = subprocess.run(cmd, capture_output=True, check=False)
        if res.returncode == 0 and res.stdout:
            img_data = res.stdout
            img_hash = hashlib.sha256(img_data).hexdigest()
            return img_hash, img_data
    except Exception:
        pass
    return None, None

def get_metadata(file_path):
    """Gets artist and album info from the file."""
    cmd = [
        'ffprobe', '-v', 'quiet', 
        '-show_entries', 'format_tags=artist,album', 
        '-of', 'json', str(file_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        tags = json.loads(res.stdout).get('format', {}).get('tags', {})
        artist = tags.get('artist', 'Artista Desconocido').replace('\u200b', '')
        album = tags.get('album', 'Álbum Desconocido').replace('\u200b', '')
        return normalize_text(artist), normalize_text(album)
    except Exception:
        return "Desconocido", "Desconocido"

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']):
        sys.exit(1)

    # Path for covers folder
    covers_dir = MUSIC_BASE_DIR / "portadas"
    covers_dir.mkdir(exist_ok=True, parents=True)

    print(f"Buscando canciones en {MUSIC_BASE_DIR}...")
    
    # Get all mp3 files, excluding the portadas directory itself
    all_files = [f for f in MUSIC_BASE_DIR.rglob("*.mp3") if covers_dir not in f.parents]
    
    if not all_files:
        print("No se encontraron archivos .mp3.")
        return

    print(f"Se encontraron {len(all_files)} canciones. Extrayendo portadas únicas...")

    seen_hashes = set()
    seen_names = set()
    
    extracted_count = 0
    skipped_count = 0
    no_cover_count = 0

    for i, mp3 in enumerate(all_files, 1):
        print(f"[{i}/{len(all_files)}] Procesando: {mp3.name}", end='\r')
        
        img_hash, img_data = get_image_hash(mp3)
        
        if not img_hash:
            no_cover_count += 1
            continue
            
        if img_hash in seen_hashes:
            skipped_count += 1
            continue
            
        # New cover hash found, now check if we already have this Artist - Album
        artist, album = get_metadata(mp3)
        base_name = clean_filename(f"{artist} - {album}")
        
        if not base_name or base_name == " - ":
            base_name = f"cover_{img_hash[:10]}"
            
        if base_name in seen_names:
            # We already have a cover for this Artist - Album with a different hash
            # Treat as visual duplicate and skip
            skipped_count += 1
            continue
            
        target_path = covers_dir / f"{base_name}.jpg"
        
        try:
            with open(target_path, 'wb') as f:
                f.write(img_data)
            seen_hashes.add(img_hash)
            seen_names.add(base_name)
            extracted_count += 1
        except Exception as e:
            print(f"\nError al guardar portada de {mp3.name}: {e}")

    print(f"\n\nProceso completado.")
    print(f"- Portadas extraídas: {extracted_count}")
    print(f"- Portadas duplicadas omitidas: {skipped_count}")
    print(f"- Canciones sin portada: {no_cover_count}")
    print(f"Las portadas se encuentran en: {covers_dir}")

if __name__ == "__main__":
    main()
