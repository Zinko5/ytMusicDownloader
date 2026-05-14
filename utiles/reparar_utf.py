#!/usr/bin/env python3
import sys
import subprocess
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import normalize_text, extract_video_id, check_dependencies, select_music_folder, MUSIC_BASE_DIR

def process_file(file_path):
    """Re-tag a single file using ffmpeg to fix ID3 version and normalization."""
    cmd_probe = [
        'ffprobe', '-v', 'quiet', 
        '-show_entries', 'format_tags', 
        '-of', 'json', str(file_path)
    ]
    try:
        res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        tags = data.get('format', {}).get('tags', {})
    except Exception as e:
        print(f"Error leyendo metadatos de {file_path.name}: {e}")
        return False

    title_raw = tags.get('title', '')
    artist_raw = tags.get('artist', '')
    album_raw = tags.get('album', '')

    # Robust check: Exactamente un carácter invisible al inicio
    def is_ok(text):
        return text.startswith('\u200b') and not text.startswith('\u200b\u200b')

    if is_ok(title_raw) and is_ok(artist_raw) and is_ok(album_raw):
        # No mostramos el skip por consola a petición del usuario
        return True

    title = normalize_text(title_raw.lstrip('\u200b'))
    artist = normalize_text(artist_raw.lstrip('\u200b'))
    album = normalize_text(album_raw.lstrip('\u200b'))
    comment = tags.get('comment', '')

    temp_file = file_path.with_suffix('.temp_fix.mp3')
    
    cmd_fix = [
        'ffmpeg', '-i', str(file_path),
        '-map', '0', '-c', 'copy',
        '-id3v2_version', '3',
        '-metadata', f'title=\u200b{title}',
        '-metadata', f'artist=\u200b{artist}',
        '-metadata', f'album=\u200b{album}',
        '-metadata', f'comment={comment}',
        str(temp_file), '-y'
    ]

    try:
        subprocess.run(cmd_fix, capture_output=True, check=True)
        temp_file.replace(file_path)
        print(f"OK: {file_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR en {file_path.name}: {e.stderr.decode()[:200]}")
        if temp_file.exists():
            temp_file.unlink()
        return False

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']):
        sys.exit(1)

    folder = sys.argv[1] if len(sys.argv) > 1 else None
    if folder is None:
        folder = select_music_folder()
        if folder is None:
            print("No se seleccionó ninguna carpeta. Saliendo.")
            sys.exit(0)

    target_dir = MUSIC_BASE_DIR / folder
    
    if not target_dir.exists():
        print(f"Error: El directorio {target_dir} no existe.")
        sys.exit(1)

    print(f"Escaneando archivos en {target_dir}...")
    files = list(target_dir.rglob("*.mp3"))
    
    if not files:
        print("No se encontraron archivos .mp3.")
        return

    print(f"Se encontraron {len(files)} archivos. Iniciando reparación...")
    success_count = 0
    for f in files:
        if process_file(f):
            success_count += 1
            
    print(f"\nFinalizado. Se actualizaron {success_count} de {len(files)} archivos.")

if __name__ == "__main__":
    main()
