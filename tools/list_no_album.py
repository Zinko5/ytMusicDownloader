#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import ZWP
from core.utils import check_dependencies
from core.metadata import MetadataManager
from core.filesystem import get_mp3_files
from core.ui import run_folder_workflow

def is_real_album(album_tag, folder_name):
    clean_album = album_tag.lstrip(ZWP).strip()
    if not clean_album: return False
    placeholders = ['unknown', 'unknown album', 'desconocido', 'n/a']
    if clean_album.lower() in placeholders: return False
    if clean_album.lower() == folder_name.lower(): return False
    return True

def gather_no_album(directory, folder_name):
    files = get_mp3_files(directory)
    results = []
    for f in files:
        tags = MetadataManager.get_tags(f)
        album = tags.get('album', '')
        if not is_real_album(album, folder_name):
            results.append({
                'path': f,
                'display_info': f"'{album.lstrip(ZWP)}'" if album else "VACÍO"
            })
    return results

def main():
    if not check_dependencies(['ffprobe']): sys.exit(1)

    run_folder_workflow(
        gather_func=gather_no_album,
        item_label="canción sin álbum real",
        action_label="listar canciones",
        process_func=lambda item: print(f"  - {item['path'].name} [Actual: {item['display_info']}]") or True
    )

if __name__ == "__main__":
    main()
