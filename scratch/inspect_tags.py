import sys
import subprocess
import json
import unicodedata

def inspect(file_path):
    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format_tags=title', '-of', 'json', file_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(res.stdout)
    title = data.get('format', {}).get('tags', {}).get('title', '')
    
    print(f"Title: {title}")
    print(f"Bytes (UTF-8): {title.encode('utf-8')}")
    print(f"Normalization: {unicodedata.name(title[2]) if len(title)>2 else '?'}")
    for i, c in enumerate(title):
        try:
            print(f"Char {i}: {c} (U+{ord(c):04X}) - {unicodedata.name(c)}")
        except:
            print(f"Char {i}: {c} (U+{ord(c):04X})")

if __name__ == "__main__":
    inspect(sys.argv[1])
