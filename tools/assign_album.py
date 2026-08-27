#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import MUSIC_BASE_DIR, ZWP
from core.utils import check_dependencies
from core.metadata import MetadataManager
from core.youtube import get_playlist_metadata, extract_video_id_from_file, load_playlists
from core.filesystem import get_music_folders, get_mp3_files
from core.ui import confirm_action, menu_select_playlist

def process_playlist(folder_name, url):
    target_dir = MUSIC_BASE_DIR / folder_name
    album_name, playlist_ids = get_playlist_metadata(url)
    if not album_name:
        print(f"Error obteniendo metadatos de playlist para {folder_name}")
        return

    print(f"\n--- Analizando: {folder_name} ---")
    files = get_mp3_files(target_dir)
    
    to_fix = []
    for f in files:
        tags = MetadataManager.get_tags(f)
        if tags.get('album', '').lstrip(ZWP) in ['', 'Unknown Album']:
            v_id = extract_video_id_from_file(f)
            if v_id and v_id in playlist_ids:
                to_fix.append(f)

    if not to_fix:
        print("No se encontraron canciones sin álbum que pertenezcan a esta playlist.")
        return

    print(f"Se encontraron {len(to_fix)} canciones para asignar al álbum '{album_name}'")
    if confirm_action("¿Desea aplicarlos? (s/N): "):
        success = 0
        for f in to_fix:
            if MetadataManager.update_tags(f, album=album_name):
                print(f"  OK: {f.name}")
                success += 1
        print(f"Finalizado: {success} actualizados.")

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']): sys.exit(1)

    url, choice = menu_select_playlist()
    
    if choice == "__ALL__":
        playlists = load_playlists()
        for name, pl_url in playlists.items():
            process_playlist(name, pl_url)
    elif choice:
        process_playlist(choice, url)

if __name__ == "__main__":
    main()
