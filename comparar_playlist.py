#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

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

def get_folder_ids(music_dir):
    """Extract video IDs from MP3 files in the specified directory."""
    folder_ids = {}  # {video_id: filename}
    if not music_dir.is_dir():
        print(f"Error: Directory {music_dir} does not exist.")
        sys.exit(1)

    print(f"Extrayendo IDs de video de la carpeta {music_dir}...")
    for mp3_file in music_dir.glob("*.mp3"):
        try:
            cmd = [
                'ffprobe', '-v', 'quiet', 
                '-show_entries', 'format_tags=comment', 
                '-of', 'json', str(mp3_file)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                comment = data.get('format', {}).get('tags', {}).get('comment', '')
                # Extract video_id=...
                import re
                match = re.search(r'video_id=([^ ]*)', comment)
                if match:
                    video_id = match.group(1)
                    folder_ids[video_id] = mp3_file.stem
        except Exception as e:
            print(f"Error procesando {mp3_file.name}: {e}")
    
    return folder_ids

def get_playlist_ids(url, cookies_file=None):
    """Extract video IDs and titles from a YouTube playlist."""
    playlist_ids = {}  # {video_id: title}
    print("Extrayendo IDs y títulos de la playlist...")
    
    # Convert music.youtube.com to youtube.com
    url = url.replace("music.youtube.com", "youtube.com")
    
    cmd = YT_DLP_CMD + ['--dump-json', '--flat-playlist', '--no-download', url]
    if cookies_file and cookies_file.exists():
        cmd.extend(['--cookies', str(cookies_file)])
        
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
    cookies_file = Path.home() / "cookies.txt"
    
    folder_ids = get_folder_ids(music_dir)
    playlist_ids = get_playlist_ids(args.url, cookies_file)
    
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
