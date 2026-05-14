#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
import re
from pathlib import Path

# Add utiles to path
from utiles.core import (
    normalize_text, 
    clean_filename, 
    extract_video_id, 
    check_dependencies, 
    get_yt_dlp_command,
    clean_playlist_title,
    select_music_folder,
    select_playlist_from_config,
    load_playlists,
    save_playlists,
    MUSIC_BASE_DIR, 
    TEMP_DIR,
    COOKIES_FILE
)

# Local Constants
MAX_RETRIES = 3

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
        self.default_album = "Unknown Album"
        self.yt_dlp_cmd = get_yt_dlp_command()
        
    def build_cache(self):
        """Scan directory for existing MP3s using a persistent cache and multiprocessing."""
        print(f"Construyendo caché para: {self.music_dir.name}...")
        cache_file = self.music_dir / ".metadata_cache.json"
        cache = {}
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text())
            except: pass
            
        new_cache = {}
        files_to_scan = []
        
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
        
        if files_to_scan:
            from concurrent.futures import ProcessPoolExecutor
            print(f"Escaneando {len(files_to_scan)} archivos nuevos/modificados en paralelo...")
            with ProcessPoolExecutor() as executor:
                results = list(executor.map(self._scan_file_worker, files_to_scan))
                
            for filename, v_id in results:
                if v_id:
                    self.existing_ids.add(v_id)
                    mtime = str((self.music_dir / filename).stat().st_mtime)
                    new_cache[filename] = {'video_id': v_id, 'mtime': mtime}

        # Update filename counts
        base_variants = {}
        max_numbered = {}
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
            self.filename_counts[low_name] = max(n - 1, m)
                    
        try:
            cache_file.write_text(json.dumps(new_cache, indent=2))
        except: pass

    @staticmethod
    def _scan_file_worker(mp3_path):
        v_id = extract_video_id(mp3_path)
        return mp3_path.name, v_id

    def process_video(self, video_id, video_url, pre_metadata=None):
        if video_id in self.existing_ids:
            self.skipped += 1
            return
            
        print(f"\nProcesando: {video_url}")
        attempt = 1
        use_cookies = COOKIES_FILE is not None
        
        while attempt <= MAX_RETRIES:
            try:
                # 1. Fetch FULL metadata
                cmd_meta = self.yt_dlp_cmd + ['--dump-json', '--no-download', '--js-runtimes', 'node', video_url]
                if use_cookies:
                    cmd_meta.extend(['--cookies', str(COOKIES_FILE)])
                    
                meta_res = subprocess.run(cmd_meta, capture_output=True, text=True)
                if meta_res.returncode != 0:
                    raise Exception(f"Metadata fail: {meta_res.stderr}")
                metadata = json.loads(meta_res.stdout)
                
                title = normalize_text(metadata.get('title', 'Unknown Title'))
                artist = normalize_text(metadata.get('artist') or metadata.get('uploader') or 'Unknown Artist')
                album = normalize_text(metadata.get('album') or self.default_album)
                
                final_title = clean_filename(title)
                if not final_title: final_title = f"track_{video_id}"
                
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
                            print(f"Migrando ID a archivo existente: {final_title}")
                            temp_fix = target_path.with_suffix('.tmp_fix.mp3')
                            try:
                                subprocess.run(['ffmpeg', '-i', str(target_path), '-c', 'copy', '-metadata', f'comment=video_id={video_id}', str(temp_fix), '-y'], capture_output=True, check=True)
                                shutil.move(str(temp_fix), str(target_path))
                                self.existing_ids.add(video_id)
                                self.skipped += 1
                                return
                            except: pass
                            
                    count = self.filename_counts.get(low_title, 0) + 1
                    self.filename_counts[low_title] = count
                    final_title = f"{final_title}({count})"
                    target_path = self.music_dir / f"{final_title}.mp3"
                    self.duplicates.append(final_title)
                else:
                    self.filename_counts[low_title] = 0

                # 3. Download thumbnail & crop
                thumb_file = TEMP_DIR / f"{video_id}.jpg"
                thumb_square = TEMP_DIR / f"{video_id}_square.jpg"
                self._download_and_process_thumbnail(metadata, video_id, thumb_file, thumb_square)

                # 4. Download audio
                temp_output = TEMP_DIR / f"{video_id}.mp3"
                cmd_dl = self.yt_dlp_cmd + ['-x', '--audio-format', 'mp3', '--audio-quality', '0', '--embed-metadata', '--add-metadata', '--js-runtimes', 'node', '--metadata-from-title', '%(title)s', '-o', str(temp_output), video_url]
                if use_cookies: cmd_dl.extend(['--cookies', str(COOKIES_FILE)])
                subprocess.run(cmd_dl, capture_output=True, check=True)
                
                # 5. Embed metadata
                ffmpeg_cmd = ['ffmpeg', '-i', str(temp_output)]
                if thumb_square.exists():
                    ffmpeg_cmd.extend(['-i', str(thumb_square)])
                    map_args = ['-map', '0', '-map', '1']
                else:
                    map_args = ['-map', '0']
                
                ffmpeg_cmd.extend(['-id3v2_version', '3', '-c', 'copy'] + map_args + ['-metadata', f'title=\u200b{title}', '-metadata', f'artist=\u200b{artist}', '-metadata', f'album=\u200b{album}', '-metadata', f'comment=video_id={video_id}'])
                if thumb_square.exists():
                    ffmpeg_cmd.extend(['-metadata:s:v', 'title=Album cover', '-metadata:s:v', 'comment=Cover (front)'])
                
                ffmpeg_cmd.extend([str(target_path), '-y'])
                subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
                
                print(f"Descargada: {final_title}")
                self.downloaded += 1
                self.existing_ids.add(video_id)
                break
                
            except Exception as e:
                error_msg = str(e)
                is_signature_error = any(msg in error_msg for msg in ["Signature solving failed", "403", "exit status 2"])
                if use_cookies and is_signature_error:
                    print(f"Reintentando sin cookies por error de firma...")
                    use_cookies = False
                    if attempt == 1: continue
                
                print(f"Error en {video_url} (intento {attempt}): {error_msg[:100]}")
                if attempt == MAX_RETRIES:
                    self.errors.append(f"{video_url} falló")
                    self.errored += 1
                attempt += 1

    def _download_and_process_thumbnail(self, metadata, video_id, thumb_file, thumb_square):
        candidates = [
            {'url': f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg", 'preference': 1000},
            {'url': f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg", 'preference': 500}
        ]
        candidates.extend(metadata.get('thumbnails', []))
        sorted_c = sorted(candidates, key=lambda t: (t.get('preference', -1000), 1 if t.get('url', '').endswith('.jpg') else 0), reverse=True)
        
        for thumb in sorted_c:
            url = thumb.get('url')
            if "googleusercontent.com" in url:
                url = re.sub(r'=[whs]\d+.*$', '=w1200-h1200-l90-rj', url) if "=" in url else url + "=w1200-h1200-l90-rj"
            try:
                if subprocess.run(['curl', '-sLf', url, '-o', str(thumb_file)]).returncode == 0:
                    if thumb_file.stat().st_size > 10000: break
            except: pass
        
        if thumb_file.exists() and thumb_file.stat().st_size > 0:
            probe = subprocess.run(['ffprobe', '-v', 'quiet', '-show_entries', 'stream=width,height', '-of', 'json', str(thumb_file)], capture_output=True, text=True)
            dim = json.loads(probe.stdout).get('streams', [{}])[0]
            w, h = dim.get('width', 0), dim.get('height', 0)
            if w > 0 and h > 0:
                if w == h: shutil.copy(str(thumb_file), str(thumb_square))
                else:
                    subprocess.run(['ffmpeg', '-i', str(thumb_file), '-vf', "crop='min(iw,ih)':'min(iw,ih)'", str(thumb_square), '-y'], capture_output=True)

    def print_summary(self):
        print(f"\nResumen para {self.music_dir.name}: {self.downloaded} OK, {self.skipped} omitidas, {self.errored} errores.")

def run_download(url, folder_name=None):
    """Processes a single URL/folder pair."""
    yt_dlp_cmd = get_yt_dlp_command()
    print(f"\n>>> Iniciando descarga para: {folder_name or url}")
    
    # Extract metadata
    is_playlist = "list=" in url
    fetch_cmd = yt_dlp_cmd + (['--dump-single-json', '--flat-playlist'] if is_playlist else ['--dump-json']) + ['--no-download', url]
    if COOKIES_FILE:
        fetch_cmd.extend(['--cookies', str(COOKIES_FILE)])
        
    res = subprocess.run(fetch_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error al obtener información: {res.stderr}")
        return
        
    data = json.loads(res.stdout)
    extracted_title = clean_playlist_title(data.get('title'))
    final_folder = folder_name or extracted_title
    
    music_dir = MUSIC_BASE_DIR / final_folder
    music_dir.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    downloader = MusicDownloader(music_dir)
    downloader.default_album = extracted_title
    downloader.build_cache()
    
    entries = data.get('entries', []) if is_playlist else [data]
    if not entries:
        print("No se encontraron canciones.")
        return

    for entry in entries:
        v_id = entry.get('id')
        if v_id:
            v_url = f"https://youtube.com/watch?v={v_id}"
            downloader.process_video(v_id, v_url, pre_metadata=entry)
            
    downloader.print_summary()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("folder", nargs="?", default=None)
    args = parser.parse_args()
    
    if not check_dependencies(): sys.exit(1)
    
    url = args.url
    folder = args.folder
    
    if not url:
        url, folder = select_playlist_from_config()
        if not url:
            url = input("\nIntroduzca la URL de la playlist o video: ").strip()
            if not url:
                print("No se proporcionó ninguna URL. Saliendo.")
                sys.exit(0)

    if url == "__ALL__":
        playlists = load_playlists()
        print(f"\n=== PROCESANDO {len(playlists)} PLAYLISTS GUARDADAS ===\n")
        for name, pl_url in playlists.items():
            try:
                run_download(pl_url, name)
            except Exception as e:
                print(f"Error en playlist '{name}': {e}")
        print("\n=== TRABAJO POR LOTES FINALIZADO ===")
    else:
        # Check if we should save this new URL (if not from config)
        if "list=" in url and not args.url and not folder:
            # We need to fetch title first to suggest a name
            yt_dlp_cmd = get_yt_dlp_command()
            fetch_cmd = yt_dlp_cmd + ['--dump-single-json', '--flat-playlist', '--no-download', url]
            if COOKIES_FILE: fetch_cmd.extend(['--cookies', str(COOKIES_FILE)])
            res = subprocess.run(fetch_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                extracted_title = clean_playlist_title(data.get('title'))
                save_it = input(f"\n¿Desea guardar esta playlist como '{extracted_title}' para el futuro? (s/n) [s]: ").strip().lower() or 's'
                if save_it == 's':
                    all_pl = load_playlists()
                    all_pl[extracted_title] = url
                    save_playlists(all_pl)
                    folder = extracted_title

        if not folder:
            # This is a bit tricky if we already fetched it, but let's keep it simple
            pass 
            
        run_download(url, folder)
        
    shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    main()
