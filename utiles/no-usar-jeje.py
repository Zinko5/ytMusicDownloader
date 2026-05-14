#!/usr/bin/env python3
import sys
import json
import subprocess
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    select_music_folder,
    MUSIC_BASE_DIR,
    check_dependencies,
    normalize_text,
    clean_filename
)

def get_title_tag(mp3_path):
    """Extracts the title tag from an MP3 file."""
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=title', '-of', 'json', str(mp3_path)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return data.get('format', {}).get('tags', {}).get('title', '')
    except:
        return ""

def process_directory(directory, fix=False):
    """Checks or renames filenames to match their ID3 title tags."""
    print(f"\n--- Analizando: {directory.name} ---")
    mp3_files = list(directory.glob("*.mp3"))
    
    # We need to track names in the folder to handle duplicates (case-insensitive)
    existing_names_low = {} # {name_low: current_max_index}
    
    # First pass: identify current names
    for mp3 in mp3_files:
        existing_names_low[mp3.stem.lower()] = existing_names_low.get(mp3.stem.lower(), 0)
    
    changes_count = 0
    
    for mp3 in mp3_files:
        title = normalize_text(get_title_tag(mp3))
        if not title:
            continue
            
        target_stem = clean_filename(title)
        current_stem = mp3.stem
        
        # If they match exactly, skip
        if target_stem == current_stem:
            continue
            
        # If they match case-insensitively but have different case, 
        # we might want to fix it if the OS allows (Linux does).
        # But if it matches a cleaned version of itself (special chars), it's also fine.
        if target_stem.lower() == current_stem.lower():
             # Only a case change or special char fix. 
             # We still count it as a potential change if the user wants it exact.
             pass

        # Calculate final name (handling duplicates)
        final_stem = target_stem
        count = 1
        
        # We need to be careful: if we are "fixing", we must check against the NEW state of the folder.
        # But for a simple sync, let's see if the target name (case-insensitive) is taken by ANOTHER file.
        
        # Check collision
        while True:
            candidate = final_stem.lower()
            # If the candidate exists and it's NOT the current file
            collision = False
            for other in mp3_files:
                if other != mp3 and other.stem.lower() == candidate:
                    collision = True
                    break
            
            if not collision:
                break
            
            final_stem = f"{target_stem} ({count})"
            count += 1

        if final_stem != current_stem:
            changes_count += 1
            if fix:
                print(f"Renombrando: '{mp3.name}' -> '{final_stem}.mp3'")
                try:
                    mp3.rename(mp3.with_name(f"{final_stem}.mp3"))
                except Exception as e:
                    print(f"  Error: {e}")
            else:
                print(f"Diferencia:")
                print(f"  - Actual: {mp3.name}")
                print(f"  - Objetivo: {final_stem}.mp3")
                print(f"  - Título (Tag): {title}")

    if changes_count == 0:
        print("Todos los archivos coinciden con su título.")
    return changes_count

def main():
    if not check_dependencies(['ffprobe']):
        sys.exit(1)
        
    folder = select_music_folder()
    if folder is None:
        print("Operación cancelada.")
        return

    print("\nModos de operación:")
    print("1. Solo listar archivos a renombrar")
    print("2. Renombrar archivos físicamente")
    
    choice = input("\nSeleccione modo (1-2) [1]: ").strip() or "1"
    fix_mode = (choice == "2")

    print(f"\nModo: {'RENOMBRADO' if fix_mode else 'LISTADO'}")
    total_changes = 0
    
    if folder == "":
        subfolders = sorted([f for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])
        for sub in subfolders:
            total_changes += process_directory(sub, fix_mode)
    else:
        target_dir = MUSIC_BASE_DIR / folder
        total_changes += process_directory(target_dir, fix_mode)
        
    if not fix_mode:
        print(f"\nResumen: Se detectaron {total_changes} archivos para renombrar.")
    else:
        print(f"\nResumen: Se renombraron {total_changes} archivos.")

if __name__ == "__main__":
    main()
