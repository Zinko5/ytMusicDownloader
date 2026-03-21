#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Constants
MUSIC_BASE_DIR = Path.home() / "musica"
TEMP_DIR = Path("/tmp/yt-dlp-temp")
MAX_RETRIES = 3

def check_dependencies():
    """Check if required external tools are installed."""
    # First check for python modules
    try:
        import yt_dlp
        global YT_DLP_CMD
        YT_DLP_CMD = [sys.executable, '-m', 'yt_dlp']
    except ImportError:
        # Fallback to system command
        YT_DLP_CMD = ['yt-dlp']
        
    for tool in ['ffmpeg', 'ffprobe', 'curl']:
        if subprocess.run(['command', '-v', tool], shell=True, capture_output=True).returncode != 0:
            print(f"Error: {tool} must be installed.")
            sys.exit(1)
            
    # If not found via import, check if command exists
    if YT_DLP_CMD == ['yt-dlp']:
        if subprocess.run(['command', '-v', 'yt-dlp'], shell=True, capture_output=True).returncode != 0:
            print(f"Error: yt-dlp must be installed or available in your environment.")
            sys.exit(1)

def clean_filename(name):
    """Minimally clean filename (remove invalid characters)."""
    # Remove only filesystem-invalid characters
    name = re.sub(r'[/\\:*?"<>|]', '', name)
    # Trim whitespace and internal multiple spaces
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

class MusicDownloader:
    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.downloaded = 0
        self.skipped = 0
        self.errored = 0
        self.errors = []
        self.duplicates = []
        self.existing_ids = set()
        self.filename_counts = {}  # {lowercase_name: max_counter}
        
    def build_cache(self):
        """Scan directory for existing MP3s to cache IDs and filename counts."""
        print("Construyendo caché de IDs de video y nombres de archivo existentes...")
        for mp3 in self.music_dir.glob("*.mp3"):
            # ID Cache
            v_id = extract_video_id(mp3)
            if v_id:
                self.existing_ids.add(v_id)
            
            # Filename count cache (for duplicates)
            stem = mp3.stem
            match = re.search(r'^(.*) \((\d+)\)$', stem)
            if match:
                base_name, counter = match.groups()
                low_name = base_name.lower()
                val = int(counter)
                if val > self.filename_counts.get(low_name, 0):
                    self.filename_counts[low_name] = val
            else:
                low_name = stem.lower()
                if low_name not in self.filename_counts:
                    self.filename_counts[low_name] = 0

    def process_video(self, video_url):
        print(f"\nProcesando: {video_url}")
        
        # Extract ID from URL for initial check
        match = re.search(r'[?&]v=([^&]+)', video_url)
        if not match:
            self.errors.append(f"Invalid URL ({video_url})")
            self.errored += 1
            return
        video_id = match.group(1)
        
        if video_id in self.existing_ids:
            print(f"Omitida (ya existe por ID): {video_id}")
            self.skipped += 1
            return

        attempt = 1
        while attempt <= MAX_RETRIES:
            try:
                # 1. Fetch metadata
                cmd_meta = YT_DLP_CMD + ['--dump-json', '--no-download', video_url]
                cookies_file = Path.home() / "cookies.txt"
                if cookies_file.exists():
                    cmd_meta.extend(['--cookies', str(cookies_file)])
                    
                meta_res = subprocess.run(cmd_meta, capture_output=True, text=True)
                if meta_res.returncode != 0:
                    raise Exception(f"Metadata fail: {meta_res.stderr}")
                
                metadata = json.loads(meta_res.stdout)
                title = metadata.get('title', 'Unknown Title')
                final_title = clean_filename(title)
                if not final_title: final_title = f"track_{video_id}"
                
                # 2. Handle duplicates
                low_title = final_title.lower()
                target_filename = f"{final_title}.mp3"
                target_path = self.music_dir / target_filename
                
                # Check if this filename is already taken
                if target_path.exists():
                    existing_v_id = extract_video_id(target_path)
                    if existing_v_id == video_id:
                        print(f"Omitida (ya existe): {final_title}")
                        self.skipped += 1
                        return
                    else:
                        # Diff video, same filename -> append counter
                        count = self.filename_counts.get(low_title, 0) + 1
                        self.filename_counts[low_title] = count
                        final_title_numbered = f"{final_title} ({count})"
                        target_filename = f"{final_title_numbered}.mp3"
                        target_path = self.music_dir / target_filename
                        self.duplicates.append(final_title_numbered)
                else:
                    self.filename_counts[low_title] = 0

                # 3. Download thumbnail & crop
                thumbnails = metadata.get('thumbnails', [])
                thumb_url = None
                
                # Logic to find the best square thumbnail or highest res one
                # Filter for square-ish thumbnails first (width == height)
                square_thumbs = [t for t in thumbnails if t.get('width') == t.get('height') and t.get('width', 0) > 0]
                if square_thumbs:
                    # Pick the one with the highest width
                    best_square = max(square_thumbs, key=lambda t: t.get('width', 0))
                    thumb_url = best_square.get('url')
                    print(f"Usando miniatura cuadrada oficial: {best_square.get('width')}x{best_square.get('height')}")
                else:
                    # Fallback to the largest thumbnail available
                    if thumbnails:
                        best_thumb = max(thumbnails, key=lambda t: t.get('width', 0) * t.get('height', 0))
                        thumb_url = best_thumb.get('url')
                    else:
                        thumb_url = metadata.get('thumbnail')

                thumb_file = TEMP_DIR / f"{video_id}.jpg"
                thumb_square = TEMP_DIR / f"{video_id}_square.jpg"

                if thumb_url:
                    # Download thumbnail
                    subprocess.run(['curl', '-s', thumb_url, '-o', str(thumb_file)], check=True)
                    
                    # Get dimensions
                    probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'stream=width,height', '-of', 'json', str(thumb_file)]
                    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
                    dim_data = json.loads(probe_res.stdout)
                    
                    if 'streams' in dim_data and len(dim_data['streams']) > 0:
                        w = dim_data['streams'][0]['width']
                        h = dim_data['streams'][0]['height']
                        
                        # If it's already a square, just copy it
                        if w == h:
                            shutil.copy(str(thumb_file), str(thumb_square))
                        else:
                            # Use cropdetect to find the actual content (removes black/colored bars)
                            # We use a threshold of 60 to catch near-black or colored padding
                            crop_cmd = ['ffmpeg', '-i', str(thumb_file), '-vf', 'cropdetect=limit=60:round=2', '-t', '1', '-f', 'null', '-']
                            crop_res = subprocess.run(crop_cmd, capture_output=True, text=True)
                            match = re.search(r'crop=(\d+:\d+:\d+:\d+)', crop_res.stderr)
                            
                            if match:
                                crop_params = match.group(1)
                                cw, ch, cx, cy = map(int, crop_params.split(':'))
                                # We found the content, now make it a square within that content
                                c_min = min(cw, ch)
                                fx = cx + (cw - c_min) // 2
                                fy = cy + (ch - c_min) // 2
                                print(f"Bordes detectados. Recortando de {w}x{h} a {c_min}x{c_min}")
                                subprocess.run(['ffmpeg', '-i', str(thumb_file), '-vf', f'crop={c_min}:{c_min}:{fx}:{fy}', str(thumb_square), '-y'], capture_output=True)
                            else:
                                # Fallback to standard center crop
                                min_dim = min(w, h)
                                subprocess.run(['ffmpeg', '-i', str(thumb_file), '-vf', f'crop={min_dim}:{min_dim}:(iw-{min_dim})/2:(ih-{min_dim})/2', str(thumb_square), '-y'], capture_output=True)
                    else:
                        # Failback if ffprobe fails
                        shutil.copy(str(thumb_file), str(thumb_square))

                # 4. Download audio
                temp_output = TEMP_DIR / f"{video_id}.mp3"
                cmd_dl = YT_DLP_CMD + [
                    '-x', '--audio-format', 'mp3', '--audio-quality', '0',
                    '--embed-metadata', '--add-metadata',
                    '--metadata-from-title', '%(title)s',
                    '--postprocessor-args', f'-metadata comment=video_id={video_id}',
                    '-o', str(temp_output),
                    video_url
                ]
                if cookies_file.exists():
                    cmd_dl.extend(['--cookies', str(cookies_file)])
                
                subprocess.run(cmd_dl, capture_output=True, check=True)
                
                # 5. Embed thumbnail
                if (TEMP_DIR / f"{video_id}_square.jpg").exists():
                    subprocess.run([
                        'ffmpeg', '-i', str(temp_output), '-i', str(TEMP_DIR / f"{video_id}_square.jpg"),
                        '-c', 'copy', '-map', '0', '-map', '1', '-metadata:s:v', 'title=Album cover',
                        '-metadata:s:v', 'comment=Cover (front)', str(target_path), '-y'
                    ], capture_output=True, check=True)
                else:
                    shutil.move(str(temp_output), str(target_path))
                
                print(f"Descargada: {final_title}")
                self.downloaded += 1
                self.existing_ids.add(video_id)
                break
                
            except Exception as e:
                print(f"Error en intento {attempt}/{MAX_RETRIES} para {video_url}: {e}")
                if attempt == MAX_RETRIES:
                    self.errors.append(f"{video_url} (falló después de {MAX_RETRIES} intentos)")
                    self.errored += 1
                attempt += 1

    def print_summary(self):
        print("\nResumen de la descarga:")
        print("-" * 25)
        print(f"Canciones descargadas: {self.downloaded}")
        print(f"Canciones omitidas (ya existían): {self.skipped}")
        print(f"Canciones con error: {self.errored}")
        if self.errors:
            print("Canciones con errores:")
            for e in self.errors:
                print(f"- {e}")
        if self.duplicates:
            print("Canciones con nombres duplicados (se añadieron con enumeración):")
            for d in self.duplicates:
                print(f"- {d}")
        else:
            print("Canciones con nombres duplicados: Ninguna")

def main():
    parser = argparse.ArgumentParser(description="Descarga música de YouTube Music con metadatos y portadas 1:1")
    parser.add_argument("url", help="URL de la playlist o canción")
    parser.add_argument("folder", nargs="?", default="na", help="Nombre de la subcarpeta en ~/musica/")
    args = parser.parse_args()
    
    check_dependencies()
    
    music_dir = MUSIC_BASE_DIR / args.folder
    music_dir.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    downloader = MusicDownloader(music_dir)
    downloader.build_cache()
    
    url = args.url
    
    if "list=" in url:
        print("Obteniendo URLs de la playlist...")
        cmd = YT_DLP_CMD + ['--get-id', '--flat-playlist', url]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error: No se pudo obtener la playlist. {res.stderr}")
            sys.exit(1)
        ids = res.stdout.strip().split('\n')
        # Deduplicate and form full URLs
        video_urls = [f"https://youtube.com/watch?v={v_id}" for v_id in sorted(set(ids)) if v_id]
        if not video_urls:
            print("No se encontraron canciones en la playlist.")
            sys.exit(0)
        for v_url in video_urls:
            downloader.process_video(v_url)
    else:
        downloader.process_video(url)
        
    downloader.print_summary()
    # Cleanup temp
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
