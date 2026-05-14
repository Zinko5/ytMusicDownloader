#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
import re
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import (
    extract_video_id, 
    check_dependencies, 
    get_yt_dlp_command, 
    select_music_folder,
    select_playlist_from_config,
    MUSIC_BASE_DIR,
    COOKIES_FILE
)

def get_folder_ids(music_dir):
    """Extract video IDs from MP3 files using a persistent cache."""
    folder_ids = {}  # {video_id: stem}
    print(f"Escaneando carpeta {music_dir}...")
    
    cache_file = music_dir / ".metadata_cache.json"
    cache = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except: pass
        
    all_mp3s = list(music_dir.glob("*.mp3"))
    for mp3 in all_mp3s:
        rel_name = mp3.name
        mtime = str(mp3.stat().st_mtime)
        
        if rel_name in cache and cache[rel_name].get('mtime') == mtime:
            v_id = cache[rel_name].get('video_id')
            if v_id:
                folder_ids[v_id] = mp3.stem
        else:
            # Slow path for new/modified files
            v_id = extract_video_id(mp3)
            if v_id:
                folder_ids[v_id] = mp3.stem
                
    return folder_ids

def get_playlist_ids(url):
    """Extract video IDs and titles from a YouTube playlist."""
    playlist_ids = {}  # {video_id: title}
    print("Extrayendo IDs y títulos de la playlist...")
    
    cmd = get_yt_dlp_command() + ['--dump-json', '--flat-playlist', '--no-download', url]
    if COOKIES_FILE:
        cmd.extend(['--cookies', str(COOKIES_FILE)])
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in process.stdout.strip().split('\n'):
            if not line: continue
            video_data = json.loads(line)
            v_id = video_data.get('id')
            title = video_data.get('title')
            if v_id and title:
                playlist_ids[v_id] = title
    except Exception as e:
        print(f"Error obteniendo datos de la playlist: {e}")
        sys.exit(1)
        
    return playlist_ids

def main():
    parser = argparse.ArgumentParser(description="Compara una carpeta local con una playlist de YouTube Music")
    parser.add_argument("url", nargs="?", default=None, help="URL de la playlist")
    parser.add_argument("folder", nargs="?", default=None, help="Nombre de la subcarpeta en ~/musica/")
    args = parser.parse_args()
    
    if not check_dependencies(['ffprobe']):
        sys.exit(1)
    
    url = args.url
    folder = args.folder

    if not url:
        url, folder = select_playlist_from_config()
        if not url:
            url = input("\nIntroduzca la URL de la playlist: ").strip()
            if not url:
                print("No se proporcionó URL. Saliendo.")
                sys.exit(0)

    if folder is None:
        folder = select_music_folder()
        if folder is None:
            print("No se seleccionó ninguna carpeta. Saliendo.")
            sys.exit(0)

    music_dir = MUSIC_BASE_DIR / folder
    if not music_dir.is_dir():
        print(f"Error: Directory {music_dir} does not exist.")
        sys.exit(1)
        
    folder_ids = get_folder_ids(music_dir)
    playlist_ids = get_playlist_ids(url)
    
    matches = []
    in_playlist_not_folder = []
    in_folder_not_playlist = []
    
    for v_id, filename in folder_ids.items():
        if v_id in playlist_ids:
            matches.append((v_id, filename))
        else:
            in_folder_not_playlist.append(filename)
            
    for v_id, title in playlist_ids.items():
        if v_id not in folder_ids:
            in_playlist_not_folder.append(title)
            
    # Report
    print(f"\nResumen de la comparación:")
    print("-" * 25)
    print(f"Número total de coincidencias: {len(matches)}")
    print(f"Canciones en playlist pero no en carpeta: {len(in_playlist_not_folder)}")
    for title in in_playlist_not_folder:
        print(f"- {title}")
        
    print(f"\nCanciones en carpeta pero no en playlist: {len(in_folder_not_playlist)}")
    for name in in_folder_not_playlist:
        print(f"- {name}")

if __name__ == "__main__":
    main()
