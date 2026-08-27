#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.utils import check_dependencies
from core.metadata import MetadataManager
from core.filesystem import get_mp3_files
from core.ui import run_folder_workflow

def gather_to_repair(directory, folder_name):
    files = get_mp3_files(directory)
    if '--force' in sys.argv:
        return files
    return [f for f in files if MetadataManager.needs_repair(f)]

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']): sys.exit(1)

    run_folder_workflow(
        gather_func=gather_to_repair,
        item_label="archivo",
        action_label="reparar UTF-8",
        process_func=lambda f: MetadataManager.update_tags(f)
    )

if __name__ == "__main__":
    main()
