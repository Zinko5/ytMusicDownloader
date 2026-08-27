import unicodedata
import re
import subprocess
from .config import ZWP

def normalize_text(text):
    """Normalize text to NFC and replace problematic characters."""
    if not text:
        return ""
    text = str(text)
    # Common replacements for maximum compatibility
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
    if not name:
        return "unknown"
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def is_ascii(text):
    """Checks if a string consists entirely of ASCII characters."""
    if not text:
        return True
    try:
        text.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

def prepare_tag_value(val):
    """
    Cleans, normalizes, and conditionally prepends ZWP to text tags.
    Only prepends ZWP if the string contains non-ASCII characters.
    """
    if not val:
        return ""
    # Strip any existing ZWP and normalize text
    val = normalize_text(val).lstrip(ZWP)
    if not val:
        return ""
    # Prepend ZWP only if there are non-ASCII characters to trigger Unicode parsing
    if not is_ascii(val):
        return f"{ZWP}{val}"
    return val

def check_dependencies(tools=['ffmpeg', 'ffprobe', 'curl']):
    """Check if required external tools are installed."""
    for tool in tools:
        if subprocess.run(['command', '-v', tool], shell=True, capture_output=True).returncode != 0:
            return False
    return True
