#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    select_music_folder,
    MUSIC_BASE_DIR,
    check_dependencies
)

def process_directory(directory):
    """Detects and resolves case-insensitive name collisions."""
    print(f"\n--- Analizando: {directory.name} ---")
    
    # Sort files to ensure deterministic results (alphabetical)
    mp3_files = sorted(list(directory.glob("*.mp3")))
    
    used_names_low = {} # {name_low: original_case_example}
    collisions_resolved = 0
    
    for mp3 in mp3_files:
        stem = mp3.stem
        stem_low = stem.lower()
        
        if stem_low in used_names_low:
            # Collision detected! (e.g. "a.mp3" and "A.mp3")
            collisions_resolved += 1
            
            # Find a new name
            count = 1
            while True:
                new_stem = f"{stem} ({count})"
                new_stem_low = new_stem.lower()
                
                # Check if this new name is also taken
                if new_stem_low not in [f.stem.lower() for f in directory.glob("*.mp3")]:
                    break
                count += 1
            
            new_name = f"{new_stem}.mp3"
            print(f"Colisión detectada: '{mp3.name}' coincide con '{used_names_low[stem_low]}'")
            print(f"  -> Renombrando a: '{new_name}'")
            
            try:
                mp3.rename(directory / new_name)
            except Exception as e:
                print(f"  Error al renombrar: {e}")
        else:
            used_names_low[stem_low] = mp3.name

    if collisions_resolved == 0:
        print("No se detectaron colisiones de nombres.")
    else:
        print(f"Se resolvieron {collisions_resolved} colisiones.")
    return collisions_resolved

def main():
    folder = select_music_folder()
    if folder is None:
        print("Operación cancelada.")
        return

    total_resolved = 0
    if folder == "":
        subfolders = sorted([f for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])
        for sub in subfolders:
            total_resolved += process_directory(sub)
    else:
        target_dir = MUSIC_BASE_DIR / folder
        total_resolved = process_directory(target_dir)
        
    print(f"\nTotal de colisiones resueltas en la biblioteca: {total_resolved}")

if __name__ == "__main__":
    main()
