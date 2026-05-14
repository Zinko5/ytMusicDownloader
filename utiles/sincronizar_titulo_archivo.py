#!/usr/bin/env python3
import sys
import json
import subprocess
import argparse
import re
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
        title = data.get('format', {}).get('tags', {}).get('title', '')
        return title.lstrip('\u200b')
    except:
        return ""

def process_directory(directory, fix=False):
    """Checks or fixes title tags to match filenames."""
    print(f"\n--- Analizando: {directory.name} ---")
    mp3_files = list(directory.glob("*.mp3"))
    mismatch_count = 0
    
    for mp3 in mp3_files:
        current_title = normalize_text(get_title_tag(mp3))
        filename_stem = normalize_text(mp3.stem).lstrip('\u200b')
        
        # 1. First check: Is the filename a direct cleaned version of the tag?
        cleaned_tag_title = clean_filename(current_title)
        
        if cleaned_tag_title == filename_stem:
            is_generic = False
            filename_base = filename_stem
        else:
            # 2. Second check: Is it a mismatch because of duplicate numbering? (Song (1).mp3)
            filename_base = re.sub(r'\s*\(\d+\)$', '', filename_stem)
            if cleaned_tag_title == filename_base:
                is_generic = False
            else:
                is_generic = True
        
        if is_generic:
            mismatch_count += 1
            if fix:
                print(f"Corrigiendo: '{current_title}' -> '{filename_base}'")
                temp_file = mp3.with_suffix('.tmp_title.mp3')
                cmd_fix = [
                    'ffmpeg', '-i', str(mp3),
                    '-map', '0', '-c', 'copy',
                    '-id3v2_version', '3',
                    '-metadata', f'title=\u200b{filename_base}',
                    str(temp_file), '-y'
                ]
                try:
                    subprocess.run(cmd_fix, capture_output=True, check=True)
                    temp_file.replace(mp3)
                except Exception as e:
                    print(f"  Error corrigiendo {mp3.name}: {e}")
            else:
                print(f"Diferencia en: {mp3.name}")
                print(f"  - Tag Actual: '{current_title}'")
                print(f"  - Tag Limpio: '{cleaned_tag_title}'")
                print(f"  - Archivo   : '{filename_base}'")
                
    if mismatch_count == 0:
        print("Todo sincronizado.")
    return mismatch_count

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']):
        sys.exit(1)
        
    folder = select_music_folder()
    if folder is None:
        print("Operación cancelada.")
        return

    print("\nModos de operación:")
    print("1. Solo listar discrepancias")
    print("2. Corregir títulos automáticamente")
    
    choice = input("\nSeleccione modo (1-2) [1]: ").strip() or "1"
    fix_mode = (choice == "2")

    print(f"\nModo: {'CORRECCIÓN' if fix_mode else 'LISTADO'}")
    total_mismatches = 0
    
    if folder == "":
        # Process all subdirectories
        subfolders = sorted([f for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])
        for sub in subfolders:
            total_mismatches += process_directory(sub, fix_mode)
    else:
        # Process single directory
        target_dir = MUSIC_BASE_DIR / folder
        total_mismatches += process_directory(target_dir, fix_mode)
        
    if not fix_mode:
        print(f"\nResumen total: Se encontraron {total_mismatches} discrepancias.")
    else:
        print(f"\nResumen total: Se corrigieron {total_mismatches} títulos.")

if __name__ == "__main__":
    main()
