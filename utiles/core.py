import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path

# Path Constants
ROOT_DIR = Path(__file__).parent.parent
CONFIG_DIR = ROOT_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

MUSIC_BASE_DIR = Path.home() / "musica"
TEMP_DIR = Path("/tmp/yt-dlp-temp")
PLAYLISTS_FILE = CONFIG_DIR / "playlists.json"

# Cookie discovery
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

def normalize_text(text):
    """Normalize text to NFC and replace problematic characters for better player compatibility."""
    if not text:
        return ""
    text = str(text)
    # Common replacements for maximum compatibility (especially for ID3v2.3)
    replacements = {
        '…': '...',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        '—': '-',
        '–': '-',
        'º': 'o'
    }
    for char, rep in replacements.items():
        text = text.replace(char, rep)
        
    return unicodedata.normalize('NFC', text)

def clean_filename(name):
    """Minimally clean filename (remove invalid characters)."""
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def extract_video_id(mp3_file):
    """Extract video_id from an MP3's comment tag using ffprobe."""
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
            match = re.search(r'video_id=([^ ]*)', comment)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def get_yt_dlp_command():
    """Returns the command list to run yt-dlp (module or system)."""
    try:
        import yt_dlp
        import sys
        return [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        return ['yt-dlp']

def check_dependencies(tools=['ffmpeg', 'ffprobe', 'curl']):
    """Check if required external tools are installed."""
    for tool in tools:
        if subprocess.run(['command', '-v', tool], shell=True, capture_output=True).returncode != 0:
            print(f"Error: {tool} must be installed.")
            return False
    return True

def clean_playlist_title(title):
    """Strips 'Musicolet - ' from playlist title if present."""
    if not title:
        return "Unknown Album"
    if title.startswith("Musicolet - "):
        return title[len("Musicolet - "):]
    return title

def select_music_folder():
    """Lists subdirectories in MUSIC_BASE_DIR and asks user to select one."""
    if not MUSIC_BASE_DIR.exists():
        print(f"Error: {MUSIC_BASE_DIR} no existe.")
        return None
        
    folders = sorted([f.name for f in MUSIC_BASE_DIR.iterdir() if f.is_dir()])
    if not folders:
        print(f"No se encontraron carpetas en {MUSIC_BASE_DIR}.")
        return None
        
    print("\nSeleccione una carpeta:")
    print("0. [TODAS LAS CARPETAS (RECURSIVO)]")
    for i, folder in enumerate(folders, 1):
        print(f"{i}. {folder}")
    
    while True:
        try:
            choice = input(f"\nSeleccione el número (0-{len(folders)}): ")
            if not choice.strip():
                return None
            idx = int(choice)
            if idx == 0:
                return "" # Root of MUSIC_BASE_DIR
            if 1 <= idx <= len(folders):
                return folders[idx-1]
            else:
                print(f"Número fuera de rango.")
        except ValueError:
            print("Entrada no válida. Por favor, introduzca un número.")

def load_playlists():
    """Loads saved playlists from config file."""
    if not PLAYLISTS_FILE.exists():
        return {}
    try:
        with open(PLAYLISTS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_playlists(playlists):
    """Saves playlists to config file."""
    try:
        with open(PLAYLISTS_FILE, 'w') as f:
            json.dump(playlists, f, indent=2)
    except Exception as e:
        print(f"Error guardando playlists: {e}")

def select_playlist_from_config():
    """Lists saved playlists and allows selection."""
    playlists = load_playlists()
    if not playlists:
        return None, None
        
    print("\nPlaylists guardadas:")
    print("0. [TODAS LAS PLAYLISTS GUARDADAS]")
    keys = sorted(playlists.keys())
    for i, name in enumerate(keys, 1):
        print(f"{i}. {name}")
    
    while True:
        try:
            choice = input(f"\nSeleccione el número (0-{len(keys)}) o Enter para omitir: ")
            if not choice.strip():
                return None, None
            idx = int(choice)
            if idx == 0:
                return "__ALL__", None
            if 1 <= idx <= len(keys):
                name = keys[idx-1]
                return playlists[name], name
            else:
                print("Número fuera de rango.")
        except ValueError:
            print("Entrada no válida.")
