#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    normalize_text, 
    extract_video_id, 
    check_dependencies, 
    get_yt_dlp_command, 
    clean_playlist_title,
    select_music_folder,
    select_playlist_from_config,
    load_playlists,
    MUSIC_BASE_DIR,
    COOKIES_FILE
)

def get_playlist_metadata(url):
    """Fetches playlist title and video IDs."""
    print(f"Obteniendo información de la playlist: {url}")
    cmd = get_yt_dlp_command() + ['--dump-single-json', '--flat-playlist', '--no-download', url]
    if COOKIES_FILE:
        cmd.extend(['--cookies', str(COOKIES_FILE)])
        
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error al obtener playlist: {res.stderr}")
        return None, []
    
    data = json.loads(res.stdout)
    title = clean_playlist_title(data.get('title'))
    video_ids = [entry.get('id') for entry in data.get('entries', []) if entry.get('id')]
    return title, set(video_ids)

def fix_album_tags(target_dir, playlist_url):
    """Scans directory and fixes 'Unknown Album' tags if they belong to the playlist."""
    album_name, playlist_ids = get_playlist_metadata(playlist_url)
    if not album_name:
        return
    album_name = album_name.lstrip('\u200b')

    print(f"Álbum objetivo: {album_name}")
    print(f"Escaneando archivos en {target_dir}...")
    
    mp3_files = list(target_dir.rglob("*.mp3"))
    fixed_count = 0
    
    for mp3 in mp3_files:
        # Check current album
        cmd_probe = ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags', '-of', 'json', str(mp3)]
        try:
            res = subprocess.run(cmd_probe, capture_output=True, text=True, check=True)
            tags = json.loads(res.stdout).get('format', {}).get('tags', {})
            current_album = tags.get('album', '').lstrip('\u200b')
            
            # Only fix if it's unknown or empty
            if current_album in ['', 'Unknown Album']:
                v_id = extract_video_id(mp3)
                if v_id and v_id in playlist_ids:
                    print(f"Reparando: {mp3.name} -> {album_name}")
                    temp_file = mp3.with_suffix('.tmp_album.mp3')
                    
                    # Update album tag
                    cmd_fix = [
                        'ffmpeg', '-i', str(mp3),
                        '-map', '0', '-c', 'copy',
                        '-id3v2_version', '3',
                        '-metadata', f'album=\u200b{album_name}',
                        str(temp_file), '-y'
                    ]
                    subprocess.run(cmd_fix, capture_output=True, check=True)
                    temp_file.replace(mp3)
                    fixed_count += 1
        except Exception as e:
            print(f"Error procesando {mp3.name}: {e}")

    print(f"Finalizado {target_dir.name}. Se actualizaron {fixed_count} archivos.")
    return fixed_count

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']):
        sys.exit(1)

    url = sys.argv[1] if len(sys.argv) > 1 else None
    folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not url:
        url, folder = select_playlist_from_config()
        if not url:
            url = input("Introduzca la URL de la playlist: ").strip()
            if not url:
                print("No se proporcionó URL. Saliendo.")
                sys.exit(0)

    if url == "__ALL__":
        playlists = load_playlists()
        print(f"\n=== PROCESANDO {len(playlists)} PLAYLISTS GUARDADAS ===\n")
        total_fixed = 0
        for name, pl_url in playlists.items():
            target_dir = MUSIC_BASE_DIR / name
            if target_dir.exists():
                total_fixed += fix_album_tags(target_dir, pl_url)
            else:
                print(f"Saltando '{name}': El directorio no existe.")
        print(f"\n=== TRABAJO POR LOTES FINALIZADO. Total actualizados: {total_fixed} ===")
    else:
        if folder is None:
            folder = select_music_folder()
            if folder is None:
                print("No se seleccionó carpeta. Saliendo.")
                sys.exit(0)
                
        target_dir = MUSIC_BASE_DIR / folder
        if not target_dir.exists():
            print(f"Error: El directorio {target_dir} no existe.")
            sys.exit(1)
            
        fix_album_tags(target_dir, url)

if __name__ == "__main__":
    main()
