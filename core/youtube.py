import json
import subprocess
import re
import sys
from .config import COOKIES_FILE, PLAYLISTS_FILE
from .metadata import MetadataManager

def get_yt_dlp_command():
    try:
        import yt_dlp
        return [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        return ['yt-dlp']

def extract_video_id_from_file(mp3_file):
    tags = MetadataManager.get_tags(mp3_file)
    comment = tags.get('comment', '')
    match = re.search(r'video_id=([^ ]*)', comment)
    return match.group(1) if match else None

def get_playlist_metadata(url):
    cmd = get_yt_dlp_command() + ['--dump-single-json', '--flat-playlist', '--no-download', url]
    if COOKIES_FILE:
        cmd.extend(['--cookies', str(COOKIES_FILE)])
        
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return None, []
    
    data = json.loads(res.stdout)
    title = data.get('title', 'Unknown Playlist')
    if title.startswith("Musicolet - "):
        title = title[len("Musicolet - "):]
        
    video_ids = [entry.get('id') for entry in data.get('entries', []) if entry.get('id')]
    return title, set(video_ids)

def load_playlists():
    if not PLAYLISTS_FILE.exists():
        return {}
    try:
        with open(PLAYLISTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_playlists(playlists):
    try:
        with open(PLAYLISTS_FILE, 'w') as f:
            json.dump(playlists, f, indent=2)
    except Exception as e:
        print(f"Error guardando playlists: {e}")

def clean_playlist_title(title):
    if not title:
        return "Unknown Album"
    if title.startswith("Musicolet - "):
        return title[len("Musicolet - "):]
    return title

