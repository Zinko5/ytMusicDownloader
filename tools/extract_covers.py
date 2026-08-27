#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import MUSIC_BASE_DIR
from core.utils import check_dependencies
from core.filesystem import get_music_folders, get_mp3_files
from core.ui import menu_select_folder

def extract_cover(mp3_path):
    """Extracts album art from MP3 to a JPG file."""
    output_path = mp3_path.with_suffix('.jpg')
    if output_path.exists():
        return True # Already exists
        
    cmd = [
        'ffmpeg', '-i', str(mp3_path),
        '-an', '-vcodec', 'copy',
        str(output_path), '-y'
    ]
    try:
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0
    except:
        return False

def main():
    if not check_dependencies(['ffmpeg']): sys.exit(1)
        
    folder = menu_select_folder()
    if folder is None: return

    target_dir = MUSIC_BASE_DIR / (folder if folder != "__ALL__" else "")
    files = get_mp3_files(target_dir)
    
    print(f"\nExtrayendo portadas de {len(files)} archivos...")
    count = 0
    for f in files:
        if extract_cover(f):
            count += 1
            
    print(f"\nFinalizado. Se generaron/verificaron {count} imágenes de portada.")

if __name__ == "__main__":
    main()
