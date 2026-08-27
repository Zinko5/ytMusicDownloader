import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

# Try to respect the user's home directory for music
MUSIC_BASE_DIR = Path.home() / "musica"
TEMP_DIR = Path("/tmp/yt-dlp-temp")
TEMP_DIR.mkdir(exist_ok=True)

PLAYLISTS_FILE = CONFIG_DIR / "playlists.json"

def get_cookies_file():
    candidates = [
        CONFIG_DIR / "cookies.txt",
        CONFIG_DIR / "music.youtube.com_cookies.txt",
        ROOT_DIR / "music.youtube.com_cookies.txt",
        Path.home() / "cookies.txt"
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

COOKIES_FILE = get_cookies_file()

# Invisible character to force UTF-8 (Zero Width Space)
ZWP = '\u200b'
