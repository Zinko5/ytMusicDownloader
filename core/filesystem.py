import os
from .config import MUSIC_BASE_DIR

def get_music_folders():
    """Returns a list of subdirectories in MUSIC_BASE_DIR."""
    if not MUSIC_BASE_DIR.exists():
        return []
    return sorted([f.name for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])

def get_mp3_files(directory, recursive=True):
    """Utility to get all MP3 files in a directory."""
    if recursive:
        return list(directory.rglob("*.mp3"))
    return list(directory.glob("*.mp3"))

def get_safe_filename(directory, base_name, extension=".mp3"):
    """
    Returns a unique filename in the directory by adding (1), (2), etc.
    if the name already exists (case-insensitive check).
    """
    # 1. Direct check
    target = directory / f"{base_name}{extension}"
    
    # 2. Case-insensitive check against existing files
    # (Crucial for Linux where 'song.mp3' and 'Song.mp3' can coexist, but we don't want them to)
    existing_names_low = [f.name.lower() for f in directory.iterdir() if f.is_file()]
    
    if target.name.lower() not in existing_names_low:
        return target

    # 3. Collision detected: find a numbered version
    count = 1
    while True:
        new_name = f"{base_name} ({count}){extension}"
        if new_name.lower() not in existing_names_low:
            return directory / new_name
        count += 1
