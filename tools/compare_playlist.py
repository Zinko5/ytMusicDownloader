#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import MUSIC_BASE_DIR
from core.utils import check_dependencies
from core.youtube import get_playlist_metadata, extract_video_id_from_file, load_playlists
from core.filesystem import get_mp3_files
from core.ui import menu_select_playlist, menu_select_folder

def compare(url, folder):
    music_dir = MUSIC_BASE_DIR / (folder if folder != "__ALL__" else "")
    if not music_dir.is_dir():
        print(f"Error: {music_dir} no existe.")
        return

    print(f"\n--- Comparando con: {folder if folder != '__ALL__' else 'Toda la biblioteca'} ---")
    
    # Cache local IDs
    files = get_mp3_files(music_dir)
    folder_ids = {} # {id: name}
    for mp3 in files:
        v_id = extract_video_id_from_file(mp3)
        if v_id: folder_ids[v_id] = mp3.stem
            
    pl_title, playlist_ids = get_playlist_metadata(url)
    if not pl_title:
        print("Error al obtener datos de la playlist.")
        return
        
    print(f"Playlist: {pl_title} ({len(playlist_ids)} canciones)")
    
    matches = [v for v in playlist_ids if v in folder_ids]
    missing = [v for v in playlist_ids if v not in folder_ids]
    extra = [folder_ids[v] for v in folder_ids if v not in playlist_ids]
    
    print(f"  - Coincidencias: {len(matches)}")
    print(f"  - Faltan localmente: {len(missing)}")
    if extra and folder != "__ALL__": # Only show extra if comparing to a specific folder
        print(f"  - Sobran en carpeta: {len(extra)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("folder", nargs="?", default=None)
    args = parser.parse_args()
    
    if not check_dependencies(['ffprobe']): sys.exit(1)
    
    url = args.url
    folder = args.folder

    if not url:
        url, choice_name = menu_select_playlist()
        if not url: sys.exit(0)
    else:
        choice_name = "manual"

    if folder is None:
        folder = menu_select_folder()
        if folder is None: sys.exit(0)

    if url == "__ALL__":
        playlists = load_playlists()
        for name, pl_url in playlists.items():
            compare(pl_url, name if folder == "__ALL__" else folder)
    else:
        compare(url, folder)

if __name__ == "__main__":
    main()
