#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    select_music_folder,
    MUSIC_BASE_DIR,
    check_dependencies
)

def get_album_tag(mp3_path):
    """Extracts the album tag from an MP3 file."""
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=album', '-of', 'json', str(mp3_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        album = data.get('format', {}).get('tags', {}).get('album', '')
        return album.lstrip('\u200b')
    except:
        return ""

def process_directory(directory, folder_name):
    """Lists files in a directory with generic or missing album tags."""
    print(f"\n--- Analizando: {folder_name} ---")
    mp3_files = list(directory.glob("*.mp3"))
    found = []
    
    # Generic terms to look for
    unknown_terms = ['', 'unknown', 'unknown album', 'none', 'nan', 'na']
    folder_low = folder_name.lower()
    
    for mp3 in mp3_files:
        album = get_album_tag(mp3).strip()
        album_low = album.lower()
        
        # Check if album is generic or matches folder
        is_generic = (
            not album or 
            album_low in unknown_terms or 
            album_low == folder_low or
            album_low == f"musicolet - {folder_low}"
        )
        
        if is_generic:
            reason = "Vacio" if not album else f"'{album}'"
            found.append((mp3.name, reason))
            
    if found:
        print(f"Se encontraron {len(found)} canciones con álbum genérico:")
        for name, reason in found:
            print(f"  - {name} [Álbum: {reason}]")
    else:
        print("No se encontraron canciones con álbum genérico.")
    return len(found)

def main():
    if not check_dependencies(['ffprobe']):
        sys.exit(1)
        
    folder = select_music_folder()
    if folder is None:
        print("Operación cancelada.")
        return

    total_found = 0
    if folder == "":
        # Process all subdirectories
        print("Analizando TODA la biblioteca...")
        subfolders = sorted([f for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])
        for sub in subfolders:
            total_found += process_directory(sub, sub.name)
    else:
        # Process single directory
        target_dir = MUSIC_BASE_DIR / folder
        total_found = process_directory(target_dir, folder)
        
    print(f"\nResumen total: {total_found} canciones detectadas con álbum genérico.")

if __name__ == "__main__":
    main()
