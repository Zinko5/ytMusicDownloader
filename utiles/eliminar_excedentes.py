#!/usr/bin/env python3
import sys
import os
import argparse
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
import json
import subprocess

def get_playlist_ids(url):
    """Extract video IDs from a YouTube playlist."""
    playlist_ids = set()
    print("Obteniendo IDs de la playlist...")
    
    cmd = get_yt_dlp_command() + ['--dump-json', '--flat-playlist', '--no-download', url]
    if COOKIES_FILE:
        cmd.extend(['--cookies', str(COOKIES_FILE)])
        
    try:
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        for line in process.stdout.strip().split('\n'):
            if not line: continue
            video_data = json.loads(line)
            v_id = video_data.get('id')
            if v_id:
                playlist_ids.add(v_id)
    except Exception as e:
        print(f"Error obteniendo datos de la playlist: {e}")
        sys.exit(1)
        
    return playlist_ids

def main():
    parser = argparse.ArgumentParser(description="Elimina archivos locales que no están en la playlist de YouTube")
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("folder", nargs="?", default=None)
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
            print("No se seleccionó carpeta. Saliendo.")
            sys.exit(0)
            
    music_dir = MUSIC_BASE_DIR / folder
    if not music_dir.is_dir():
        print(f"Error: El directorio {music_dir} no existe.")
        sys.exit(1)
        
    playlist_ids = get_playlist_ids(url)
    print(f"Playlist obtenida: {len(playlist_ids)} canciones.")
    
    print(f"Escaneando carpeta local: {music_dir}...")
    local_files = list(music_dir.glob("*.mp3"))
    to_delete = []
    
    for mp3 in local_files:
        v_id = extract_video_id(mp3)
        # Only consider files that HAVE a video_id but it's not in the playlist
        # If it doesn't have a video_id, we might want to skip it to be safe
        if v_id and v_id not in playlist_ids:
            to_delete.append(mp3)
            
    if not to_delete:
        print("\n✅ No se encontraron archivos para eliminar. La carpeta está sincronizada.")
        return
        
    print(f"\n⚠️  Se encontraron {len(to_delete)} archivos que NO están en la playlist:")
    for f in to_delete:
        print(f"- {f.name}")
        
    confirm = input("\n¿ESTÁ SEGURO DE QUE DESEA ELIMINAR ESTOS ARCHIVOS? (s/N): ").strip().lower()
    if confirm == 's':
        deleted_count = 0
        for f in to_delete:
            try:
                f.unlink()
                print(f"Eliminado: {f.name}")
                deleted_count += 1
            except Exception as e:
                print(f"Error eliminando {f.name}: {e}")
        
        print(f"\nFinalizado. Se eliminaron {deleted_count} archivos.")
        
        # Update cache if it exists
        cache_file = music_dir / ".metadata_cache.json"
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text())
                new_cache = {k: v for k, v in cache.items() if k in [f.name for f in music_dir.glob("*.mp3")]}
                cache_file.write_text(json.dumps(new_cache, indent=2))
                print("Caché de metadatos actualizada.")
            except: pass
    else:
        print("Operación cancelada.")

if __name__ == "__main__":
    main()
