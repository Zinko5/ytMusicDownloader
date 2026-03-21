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
COOKIES_FILE = Path(__file__).parent / "music.youtube.com_cookies.txt"
if not COOKIES_FILE.exists():
    COOKIES_FILE = Path.home() / "cookies.txt"

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
        """Scan directory for existing MP3s using a persistent cache and multiprocessing."""
        print("Construyendo caché de IDs de video y nombres de archivo existentes...")
        cache_file = self.music_dir / ".metadata_cache.json"
        cache = {}
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text())
            except: pass
            
        new_cache = {}
        files_to_scan = []
        
        # 1. Check what is already in cache
        all_mp3s = list(self.music_dir.glob("*.mp3"))
        for mp3 in all_mp3s:
            rel_name = mp3.name
            mtime = str(mp3.stat().st_mtime)
            
            if rel_name in cache and cache[rel_name].get('mtime') == mtime:
                v_id = cache[rel_name].get('video_id')
                if v_id:
                    self.existing_ids.add(v_id)
                    new_cache[rel_name] = {'video_id': v_id, 'mtime': mtime}
            else:
                files_to_scan.append(mp3)
        
        # 2. Multiprocessing scan for missing ones
        if files_to_scan:
            from concurrent.futures import ProcessPoolExecutor
            print(f"Escaneando {len(files_to_scan)} archivos nuevos/modificados en paralelo...")
            # We reuse the helper function if it was global, but here we'll use a wrapper or define it
            with ProcessPoolExecutor() as executor:
                # Need a wrapper because extract_video_id is at module level or needs to be
                results = list(executor.map(self._scan_file_worker, files_to_scan))
                
            for filename, v_id in results:
                if v_id:
                    self.existing_ids.add(v_id)
                    mtime = str((self.music_dir / filename).stat().st_mtime)
                    new_cache[filename] = {'video_id': v_id, 'mtime': mtime}

        # 3. Update filename counts (always do this to ensure counter logic works)
        base_variants = {} # {low_name: count}
        max_numbered = {}  # {low_name: max_val}
        
        for mp3 in all_mp3s:
            stem = mp3.stem
            match = re.search(r'^(.*)\s*\((\d+)\)$', stem)
            if match:
                base_name, counter = match.groups()
                low_name = base_name.lower()
                val = int(counter)
                if val > max_numbered.get(low_name, -1):
                    max_numbered[low_name] = val
            else:
                low_name = stem.lower()
                base_variants[low_name] = base_variants.get(low_name, 0) + 1
        
        for low_name in set(base_variants.keys()) | set(max_numbered.keys()):
            n = base_variants.get(low_name, 0)
            m = max_numbered.get(low_name, -1)
            # The next counter should be higher than the highest (N) found
            # and also account for multiple base variants (e.g. bote and Bote)
            self.filename_counts[low_name] = max(n - 1, m)
                    
        # Save updated cache
        try:
            cache_file.write_text(json.dumps(new_cache, indent=2))
        except: pass

    @staticmethod
    def _scan_file_worker(mp3_path):
        """Hidden worker for ProcessPoolExecutor."""
        v_id = extract_video_id(mp3_path)
        return mp3_path.name, v_id

    def process_video(self, video_id, video_url, pre_metadata=None):
        """Process a single video, optionally using pre-fetched metadata."""
        if video_id in self.existing_ids:
            # Simple skip, no heavy processing
            self.skipped += 1
            return
            
        print(f"\nProcesando: {video_url}")
        
        attempt = 1
        use_cookies = COOKIES_FILE.exists()
        
        while attempt <= MAX_RETRIES:
            try:
                # 1. Fetch FULL metadata for the download
                print(f"Obteniendo metadatos completos para mejor calidad... [{'con cookies' if use_cookies else 'sin cookies'}]")
                cmd_meta = YT_DLP_CMD + [
                    '--dump-json', '--no-download', 
                    '--js-runtimes', 'node',
                    video_url
                ]
                if use_cookies:
                    cmd_meta.extend(['--cookies', str(COOKIES_FILE)])
                    
                meta_res = subprocess.run(cmd_meta, capture_output=True, text=True)
                if meta_res.returncode != 0:
                    raise Exception(f"Metadata fail: {meta_res.stderr}")
                metadata = json.loads(meta_res.stdout)
                title = metadata.get('title', 'Unknown Title')
                final_title = clean_filename(title)
                if not final_title: final_title = f"track_{video_id}"
                
                # 2. handle duplicates / existing files
                low_title = final_title.lower()
                target_path = self.music_dir / f"{final_title}.mp3"
                
                if target_path.exists() or low_title in self.filename_counts:
                    existing_v_id = None
                    if target_path.exists():
                        existing_v_id = extract_video_id(target_path)
                        if existing_v_id == video_id:
                            self.skipped += 1
                            return
                        elif not existing_v_id:
                            # MIGRATION: Filename matches but has no ID tag. 
                            # Assume it's the same song and "fix" the file.
                            print(f"Migrando ID a archivo existente: {final_title}")
                            temp_fix = target_path.with_suffix('.tmp_fix.mp3')
                            try:
                                # Use ffmpeg to add ID to comment tag in copy mode (no re-encoding)
                                subprocess.run([
                                    'ffmpeg', '-i', str(target_path), '-c', 'copy', 
                                    '-metadata', f'comment=video_id={video_id}', 
                                    str(temp_fix), '-y'
                                ], capture_output=True, check=True)
                                shutil.move(str(temp_fix), str(target_path))
                                self.existing_ids.add(video_id)
                                self.skipped += 1
                                return
                            except Exception as e:
                                print(f"Error etiquetando archivo existente: {e}")
                                # Fallback to numbered download if tagging fails
                                pass
                            
                    # If we reach here, it's a different video or a case-variant collision
                    count = self.filename_counts.get(low_title, 0) + 1
                    self.filename_counts[low_title] = count
                    final_title = f"{final_title}({count})"
                    target_path = self.music_dir / f"{final_title}.mp3"
                    self.duplicates.append(final_title)
                else:
                    # First time seeing this name (in any case variant)
                    self.filename_counts[low_title] = 0

                # 3. Download thumbnail & crop
                thumbnails = metadata.get('thumbnails', [])
                thumb_file = TEMP_DIR / f"{video_id}.jpg"
                thumb_square = TEMP_DIR / f"{video_id}_square.jpg"

                # Sort thumbnails by preference (highest first)
                # We also check candidate URLs that might not be in the metadata
                candidates = []
                # 1. Official constructed candidates (often better than what's listed)
                candidates.append({'url': f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", 'preference': 1000})
                candidates.append({'url': f"https://i.ytimg.com/vi_webp/{video_id}/maxresdefault.webp", 'preference': 999})
                candidates.append({'url': f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg", 'preference': 500})
                
                # 2. Metadata thumbnails
                for t in thumbnails:
                    candidates.append(t)
                
                # Sort: Constructed first, then by preference, prefer JPG
                sorted_candidates = sorted(
                    candidates, 
                    key=lambda t: (t.get('preference', -1000), 1 if t.get('url', '').endswith('.jpg') else 0), 
                    reverse=True
                )
                
                thumb_url = None
                for thumb in sorted_candidates:
                    t_url = thumb.get('url')
                    # Force high resolution if it's a googleusercontent URL
                    if "googleusercontent.com" in t_url:
                        if "=" in t_url:
                            t_url = re.sub(r'=[whs]\d+.*$', '=w1200-h1200-l90-rj', t_url)
                        else:
                            t_url += "=w1200-h1200-l90-rj"
                    
                    # Try to download and verify
                    try:
                        # Use -L for redirects and -f to fail on 404
                        res = subprocess.run(['curl', '-sLf', t_url, '-o', str(thumb_file)], capture_output=True)
                        if res.returncode != 0: continue
                        
                        # Size check: Placeholders are tiny (<10KB). HQ is usually > 20KB.
                        if thumb_file.stat().st_size > 10000:
                            thumb_url = t_url
                            print(f"Miniatura válida: {thumb_file.stat().st_size // 1024}KB -> {thumb_url}")
                            break
                    except Exception:
                        continue
                
                if not thumb_url and thumb_file.exists() and thumb_file.stat().st_size > 0:
                    pass # Keep whatever we got if nothing better
                elif not thumb_url:
                    # Last resort fallback from metadata
                    thumb_url = metadata.get('thumbnail')
                    if thumb_url:
                        subprocess.run(['curl', '-sLf', thumb_url, '-o', str(thumb_file)], check=False)
                
                if thumb_file.exists() and thumb_file.stat().st_size > 0:
                    # Get dimensions
                    probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'stream=width,height', '-of', 'json', str(thumb_file)]
                    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
                    dim_data = json.loads(probe_res.stdout)
                    
                    if 'streams' in dim_data and len(dim_data['streams']) > 0:
                        w = dim_data['streams'][0]['width']
                        h = dim_data['streams'][0]['height']
                        
                        if w == h:
                            shutil.copy(str(thumb_file), str(thumb_square))
                        else:
                            # Advanced cropdetect: high threshold to catch colored bars
                            # We also use a two-step detection if needed
                            crop_cmd = ['ffmpeg', '-i', str(thumb_file), '-vf', 'cropdetect=limit=110:round=2', '-t', '1', '-f', 'null', '-']
                            crop_res = subprocess.run(crop_cmd, capture_output=True, text=True)
                            match = re.search(r'crop=(\d+:\d+:\d+:\d+)', crop_res.stderr)
                            
                            cw, ch, cx, cy = w, h, 0, 0
                            if match:
                                cw, ch, cx, cy = map(int, match.group(1).split(':'))
                            
                            # Validation: If the detected area is still not close to a square 
                            # and we know it's a standard YT ratio, apply a "Deep Crop" fallback.
                            if abs(cw - ch) > (max(cw, ch) * 0.1): # If more than 10% diff
                                # Special case for 640x480 (standard windowboxed)
                                if w == 640 and h == 480:
                                    # Standard album art in 640x480 is 360x360 at (140, 60)
                                    print("Aplicando recorte especial para 4:3 (sddefault)")
                                    cw, ch, cx, cy = 360, 360, 140, 60
                                elif h > 0 and abs(w/h - 1.77) < 0.1: # 16:9
                                    # Standard album art in 16:9 is a centered square of height x height
                                    print("Aplicando recorte especial para 16:9 (center square)")
                                    cw, ch, cx, cy = h, h, (w - h) // 2, 0
                            
                            # Final squaring based on detected (or fallback) content
                            c_min = min(cw, ch)
                            fx = cx + (cw - c_min) // 2
                            fy = cy + (ch - c_min) // 2
                            
                            print(f"Resultado final de recorte: {c_min}x{c_min} en ({fx},{fy}) - Original {w}x{h}")
                            subprocess.run(['ffmpeg', '-i', str(thumb_file), '-vf', f'crop={c_min}:{c_min}:{fx}:{fy}', '-q:v', '2', str(thumb_square), '-y'], capture_output=True)
                    else:
                        # Failback if ffprobe fails
                        shutil.copy(str(thumb_file), str(thumb_square))

                # 4. Download audio
                temp_output = TEMP_DIR / f"{video_id}.mp3"
                cmd_dl = YT_DLP_CMD + [
                    '-x', '--audio-format', 'mp3', '--audio-quality', '0',
                    '--embed-metadata', '--add-metadata',
                    '--js-runtimes', 'node',
                    '--metadata-from-title', '%(title)s',
                    '-o', str(temp_output),
                    video_url
                ]
                if use_cookies:
                    cmd_dl.extend(['--cookies', str(COOKIES_FILE)])
                
                subprocess.run(cmd_dl, capture_output=True, check=True)
                
                # 5. Embed thumbnail
                if (TEMP_DIR / f"{video_id}_square.jpg").exists():
                    subprocess.run([
                        'ffmpeg', '-i', str(temp_output), '-i', str(TEMP_DIR / f"{video_id}_square.jpg"),
                        '-id3v2_version', '3',
                        '-c', 'copy', '-map', '0', '-map', '1', 
                        '-metadata', f'comment=video_id={video_id}',
                        '-metadata:s:v', 'title=Album cover',
                        '-metadata:s:v', 'comment=Cover (front)', str(target_path), '-y'
                    ], capture_output=True, check=True)
                else:
                    shutil.move(str(temp_output), str(target_path))
                
                print(f"Descargada: {final_title}")
                self.downloaded += 1
                self.existing_ids.add(video_id)
                break
                
            except Exception as e:
                error_msg = str(e)
                # Check for signature/cookie related errors anywhere or process exit code 2/1
                is_signature_error = any(msg in error_msg for msg in ["Signature solving failed", "Requested format is not available", "403", "exit status 2"])
                
                if use_cookies and is_signature_error:
                    print(f"Atención: Error detectado con cookies ({error_msg[:50]}...). Reintentando sin cookies...")
                    use_cookies = False
                    # Don't increment attempt if we're just switching strategy
                    if attempt == 1:
                        # Clear temp if it was created
                        try:
                            if 'temp_output' in locals() and temp_output.exists(): 
                                temp_output.unlink(missing_ok=True)
                        except: pass
                        continue
                
                print(f"Error en intento {attempt}/{MAX_RETRIES} para {video_url}: {error_msg}")
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
        print("Obteniendo información de la playlist...")
        # Fetch ALL metadata for the playlist in one call (optimized)
        cmd = YT_DLP_CMD + [
            '--dump-json', '--flat-playlist', 
            '--js-runtimes', 'node',
            url
        ]
        if COOKIES_FILE.exists():
            cmd.extend(['--cookies', str(COOKIES_FILE)])
            
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error: No se pudo obtener la playlist. {res.stderr}")
            sys.exit(1)
            
        # Parse multiple JSON objects (one per line)
        entries = []
        for line in res.stdout.strip().split('\n'):
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except: continue
        
        if not entries:
            print("No se encontraron canciones en la playlist.")
            sys.exit(0)
            
        print(f"Playlist con {len(entries)} canciones encontrada.")
        
        # Count what exists before processing to give a cleaner UI
        total_existing = sum(1 for e in entries if e.get('id') in downloader.existing_ids)
        if total_existing > 0:
            print(f"Omitiendo {total_existing} canciones que ya están en la biblioteca...")
        
        for entry in entries:
            video_id = entry.get('id')
            if video_id:
                v_url = f"https://youtube.com/watch?v={video_id}"
                # Pass entry metadata as pre_metadata to avoid extra calls
                downloader.process_video(video_id, v_url, pre_metadata=entry)
    else:
        # For single video, we need to extract ID first
        match = re.search(r'[?&]v=([^&]+)', url)
        v_id = match.group(1) if match else None
        downloader.process_video(v_id, url)
        
    downloader.print_summary()
    # Cleanup temp
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
