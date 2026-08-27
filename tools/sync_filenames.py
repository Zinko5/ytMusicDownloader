#!/usr/bin/env python3
import sys
import re
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from core.config import ZWP
from core.utils import check_dependencies, normalize_text, clean_filename
from core.metadata import MetadataManager
from core.filesystem import get_mp3_files
from core.ui import run_folder_workflow

def get_clean_base(filename_stem, current_title_tag):
    """
    Intelligently determines if a trailing (N) is a duplication marker or part of the title,
    taking into account characters that are invalid in filenames but valid in titles.
    Uses symmetrical cleaning for more robust comparison.
    """
    # Clean both sides symmetrically to ignore punctuation differences
    stem_clean = clean_filename(filename_stem).lower()
    title_clean = clean_filename(current_title_tag).lower()
    
    # 1. Compare cleaned versions. 
    if stem_clean == title_clean:
        return filename_stem, False # Effectively the same

    # 2. Check for duplication suffix pattern: " (digits)"
    match = re.search(r'\s*\((\d+)\)$', filename_stem)
    if not match:
        return filename_stem, True # Real mismatch

    suffix = match.group(0)
    number = match.group(1)
    base = filename_stem[:match.start()].strip()

    # 3. If it's a 4-digit number, it's a year. 
    if len(number) == 4:
        return filename_stem, True

    # 4. Symmetrical check for the base (stripping duplication marker)
    if clean_filename(base).lower() == title_clean:
        return base, False

    # 5. Mismatch: suggest the base without the suffix
    return base, True

def gather_mismatches(directory, folder_name):
    files = get_mp3_files(directory)
    mismatches = []
    for f in files:
        tags = MetadataManager.get_tags(f)
        current_title = normalize_text(tags.get('title', '').lstrip(ZWP))
        filename_stem = normalize_text(f.stem).lstrip(ZWP)
        
        base_name, is_mismatch = get_clean_base(filename_stem, current_title)
        if is_mismatch:
            mismatches.append({
                'path': f,
                'target_title': base_name
            })
    return mismatches

def main():
    if not check_dependencies(['ffmpeg', 'ffprobe']): sys.exit(1)

    run_folder_workflow(
        gather_func=gather_mismatches,
        item_label="archivo",
        action_label="sincronizar tags con nombre de archivo",
        process_func=lambda item: MetadataManager.update_tags(item['path'], title=item['target_title'])
    )

if __name__ == "__main__":
    main()
