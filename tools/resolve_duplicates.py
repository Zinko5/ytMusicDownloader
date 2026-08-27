#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import MUSIC_BASE_DIR
from core.filesystem import get_safe_filename, get_mp3_files

def process_directory(directory):
    print(f"\n--- Analizando colisiones: {directory.name} ---")
    
    # We scan files and move them to a temp name first if they collide, 
    # then to their safe name to avoid clobbering.
    mp3_files = sorted(get_mp3_files(directory, recursive=False))
    
    # Track which names (lowercase) we've already "officially" accepted in this run
    seen_names_low = set()
    resolved = 0
    
    for mp3 in mp3_files:
        stem = mp3.stem
        low_name = mp3.name.lower()
        
        if low_name in seen_names_low:
            # This is a collision (e.g., we already saw 'Song.mp3' and now we see 'song.mp3')
            resolved += 1
            # Use the core logic to get a truly unique name
            new_path = get_safe_filename(directory, stem)
            print(f"Colisión detectada: '{mp3.name}' -> '{new_path.name}'")
            try:
                mp3.rename(new_path)
                seen_names_low.add(new_path.name.lower())
            except Exception as e:
                print(f"  Error: {e}")
        else:
            seen_names_low.add(low_name)
            
    return resolved

def main():
    from core.ui import menu_select_folder # Late import to avoid circular if any
    folder = menu_select_folder()
    if folder is None: return
    
    target_dir = MUSIC_BASE_DIR / (folder if folder != "__ALL__" else "")
    if folder == "__ALL__":
        total = 0
        for sub in sorted([f for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()]):
            total += process_directory(sub)
        print(f"\nTotal de colisiones resueltas: {total}")
    else:
        process_directory(target_dir)

if __name__ == "__main__":
    main()
