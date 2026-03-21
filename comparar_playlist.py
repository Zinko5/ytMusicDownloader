#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Constants
COOKIES_FILE = Path(__file__).parent / "music.youtube.com_cookies.txt"
if not COOKIES_FILE.exists():
    COOKIES_FILE = Path.home() / "cookies.txt"

def check_dependencies():
    """Check if required external tools are installed."""
    # First check for python modules
    try:
        import yt_dlp
        global YT_DLP_CMD
        YT_DLP_CMD = [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        # Fallback to system command
        YT_DLP_CMD = ['yt-dlp']

    for tool in ['ffprobe']:
        if subprocess.run(['command', '-v', tool], shell=True, capture_output=True).returncode != 0:
            print(f"Error: {tool} must be installed.")
            sys.exit(1)
            
    # If not found via import, check if command exists
    if YT_DLP_CMD == ['yt-dlp']:
        if subprocess.run(['command', '-v', 'yt-dlp'], shell=True, capture_output=True).returncode != 0:
            print(f"Error: yt-dlp must be installed or available in your environment.")
            sys.exit(1)

def extract_video_id(mp3_file):
    """Worker function to extract video_id using ffprobe."""
    try:
        import re
        cmd = [
            'ffprobe', '-v', 'quiet', 
            '-show_entries', 'format_tags=comment', 
            '-of', 'json', str(mp3_file)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            comment = data.get('format', {}).get('tags', {}).get('comment', '')
            match = re.search(r'video_id=([^ ]*)', comment)
            if match:
                return mp3_file.name, match.group(1)
    except Exception:
        pass
    return mp3_file.name, None

def get_folder_ids(music_dir):
    """Extract video IDs from MP3 files using a persistent cache and multiprocessing."""
    folder_ids = {}  # {video_id: filename}
    if not music_dir.is_dir():
        print(f"Error: Directory {music_dir} does not exist.")
        sys.exit(1)

    print(f"Escaneando carpeta {music_dir}...")
    
    # Persistence cache
    cache_file = music_dir / ".metadata_cache.json"
    cache = {}
    if cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text())
        except: pass
        
    new_cache = {}
    files_to_scan = []
    
    # 1. Identify what needs scanning
    all_mp3s = list(music_dir.glob("*.mp3"))
    for mp3 in all_mp3s:
        rel_name = mp3.name
        mtime = str(mp3.stat().st_mtime)
        
        if rel_name in cache and cache[rel_name].get('mtime') == mtime:
            v_id = cache[rel_name].get('video_id')
            if v_id:
                folder_ids[v_id] = mp3.stem
                new_cache[rel_name] = {'video_id': v_id, 'mtime': mtime}
        else:
            files_to_scan.append(mp3)
            
    # 2. Parallel scan for missing IDs
    if files_to_scan:
        from concurrent.futures import ProcessPoolExecutor
        print(f"Extrayendo IDs de {len(files_to_scan)} archivos nuevos o modificados...")
        with ProcessPoolExecutor() as executor:
            results = list(executor.map(extract_video_id, files_to_scan))
            
        for filename, v_id in results:
            if v_id:
                folder_ids[v_id] = Path(filename).stem
                mtime = str((music_dir / filename).stat().st_mtime)
                new_cache[filename] = {'video_id': v_id, 'mtime': mtime}
    
    # Save updated cache
    if new_cache != cache:
        try:
            cache_file.write_text(json.dumps(new_cache, indent=2))
        except: pass
    
    return folder_ids

def get_playlist_ids(url, cookies_file=None):
    """Extract video IDs and titles from a YouTube playlist."""
    playlist_ids = {}  # {video_id: title}
    print("Extrayendo IDs y títulos de la playlist...")
    
    # Use original URL to preserve music-specific metadata extraction
    pass
    
    cmd = YT_DLP_CMD + ['--dump-json', '--flat-playlist', '--no-download', url]
    if COOKIES_FILE.exists():
        cmd.extend(['--cookies', str(COOKIES_FILE)])
        
    try:
        # yt-dlp returns one JSON object per line for flat-playlist dump-json
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print("Error: No se pudieron obtener datos de la playlist.")
            if stderr:
                print(stderr)
            sys.exit(1)
            
        for line in stdout.strip().split('\n'):
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
    parser.add_argument("url", help="URL de la playlist de YouTube Music")
    parser.add_argument("folder", nargs="?", default="na", help="Nombre de la subcarpeta en ~/musica/")
    
    args = parser.parse_args()
    
    check_dependencies()
    
    music_dir = Path.home() / "musica" / args.folder
    
    folder_ids = get_folder_ids(music_dir)
    playlist_ids = get_playlist_ids(args.url)
    
    matches = []
    in_playlist_not_folder = []
    in_folder_not_playlist = []
    
    # Compare
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
    if matches:
        print("Coincidencias (IDs presentes en la carpeta y la playlist):")
        for v_id, name in matches:
            print(f"- {name} (ID: {v_id})")
            
    print(f"\nNúmero de canciones en la playlist pero no en la carpeta: {len(in_playlist_not_folder)}")
    for title in in_playlist_not_folder:
        print(f"- {title}")
        
    print(f"\nNúmero de canciones en la carpeta pero no en la playlist: {len(in_folder_not_playlist)}")
    for name in in_folder_not_playlist:
        print(f"- {name}")

if __name__ == "__main__":
    main()
