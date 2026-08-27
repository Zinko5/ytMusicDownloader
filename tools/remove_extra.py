#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import MUSIC_BASE_DIR
from core.utils import check_dependencies
from core.youtube import get_playlist_metadata, extract_video_id_from_file, load_playlists
from core.filesystem import get_mp3_files
from core.ui import run_with_preview, menu_select_playlist, menu_select_folder

def main():
    if not check_dependencies(['ffprobe']): sys.exit(1)
        
    url, choice = menu_select_playlist()
    if not choice: return
    
    # If URL is ALL, we want to collect IDs from ALL playlists
    all_playlist_ids = set()
    if url == "__ALL__":
        print("Obteniendo IDs de TODAS las playlists guardadas...")
        playlists = load_playlists()
        for pl_url in playlists.values():
            _, pl_ids = get_playlist_metadata(pl_url)
            all_playlist_ids.update(pl_ids)
        folder = menu_select_folder() # Ask which folder to purge
    else:
        _, pl_ids = get_playlist_metadata(url)
        all_playlist_ids = pl_ids
        folder = choice

    if not folder: return
    
    music_dir = MUSIC_BASE_DIR / (folder if folder != "__ALL__" else "")
    if not music_dir.is_dir():
        print(f"Error: {music_dir} no existe.")
        return
        
    print(f"Escaneando {music_dir}...")
    files = get_mp3_files(music_dir)
    
    # A file is "extra" if it has a video_id but that ID is not in our set
    to_delete = []
    for f in files:
        v_id = extract_video_id_from_file(f)
        if v_id and v_id not in all_playlist_ids:
            to_delete.append(f)
            
    run_with_preview(
        items=to_delete,
        process_func=lambda f: f.unlink() or True,
        item_label="archivo",
        action_label="ELIMINAR (no están en la(s) playlist(s))"
    )

if __name__ == "__main__":
    main()
