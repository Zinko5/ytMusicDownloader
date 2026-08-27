import subprocess
import json
from pathlib import Path
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, TALB, COMM, Encoding, ID3NoHeaderError
from .config import ZWP
from .utils import normalize_text, prepare_tag_value

class MetadataManager:
    @staticmethod
    def is_correctly_prefixed(text):
        """Checks if the text has exactly one ZWP at the beginning."""
        if not text:
            return True # Empty is considered OK
        return text.startswith(ZWP) and not text.startswith(ZWP + ZWP)

    @staticmethod
    def get_tags(file_path):
        """Extracts title, artist, album, and comment tags from an MP3 file using mutagen."""
        try:
            audio = ID3(file_path)
            tags = {}
            if 'TIT2' in audio:
                tags['title'] = str(audio['TIT2'].text[0])
            if 'TPE1' in audio:
                tags['artist'] = str(audio['TPE1'].text[0])
            if 'TALB' in audio:
                tags['album'] = str(audio['TALB'].text[0])
            for key, val in audio.items():
                if key.startswith('COMM'):
                    tags['comment'] = str(val.text[0])
                    break
            return tags
        except Exception:
            return {}

    @staticmethod
    def update_tags(file_path, title=None, artist=None, album=None, comment=None):
        """
        Updates MP3 tags using mutagen.
        Forces UTF-16 encoding to ensure maximum compatibility with Windows Explorer and Android players.
        """
        try:
            audio = MP3(str(file_path), ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass

            tags = audio.tags

            # Helper to clean and prepare values
            def get_final_val(new_val, current_frame_id):
                if new_val is not None:
                    return prepare_tag_value(new_val)
                current_frame = tags.get(current_frame_id)
                current_text = str(current_frame.text[0]) if current_frame and current_frame.text else ''
                return prepare_tag_value(current_text)

            final_title = get_final_val(title, 'TIT2')
            final_artist = get_final_val(artist, 'TPE1')
            final_album = get_final_val(album, 'TALB')

            # Update text frames in UTF-16
            tags.add(TIT2(encoding=Encoding.UTF16, text=[final_title]))
            tags.add(TPE1(encoding=Encoding.UTF16, text=[final_artist]))
            tags.add(TALB(encoding=Encoding.UTF16, text=[final_album]))

            # Handle comment (video_id)
            final_comment = comment
            if final_comment is None:
                # Find current comment
                for key in list(tags.keys()):
                    if key.startswith('COMM'):
                        final_comment = str(tags[key].text[0])
                        break
            if final_comment:
                tags.add(COMM(encoding=Encoding.UTF16, lang='eng', desc='', text=[final_comment]))

            audio.save(v2_version=3)
            return True
        except Exception as e:
            print(f"Error al actualizar etiquetas en {file_path}: {e}")
            return False

    @staticmethod
    def needs_repair(file_path):
        """
        Checks if a file's metadata needs repairing.
        A file needs repair if:
        1. Any text frame containing non-ASCII characters is not encoded in UTF-16 (encoding != 1).
        2. Any of the text values differ from their prepared/expected value.
        """
        try:
            audio = ID3(file_path)
            for frame in audio.values():
                if isinstance(frame, (TIT2, TPE1, TALB, COMM)):
                    text_val = str(frame.text[0]) if frame.text else ''
                    if text_val and any(ord(c) > 127 for c in text_val) and frame.encoding != 1:
                        return True
        except Exception:
            pass

        tags = MetadataManager.get_tags(file_path)
        title = tags.get('title', '')
        artist = tags.get('artist', '')
        album = tags.get('album', '')
        
        for field in [title, artist, album]:
            if field:
                expected = prepare_tag_value(field)
                if field != expected:
                    return True
        return False
