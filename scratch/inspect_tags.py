#!/usr/bin/env python3
from pathlib import Path

f = Path("/home/zinko/musica/Otros/En El Fondo Está Bien.mp3")
if f.exists():
    data = f.read_bytes()
    idx = 0
    matches = []
    while True:
        idx = data.find(b"ID3", idx)
        if idx == -1:
            break
        matches.append(idx)
        idx += 3
    print("Occurrences of 'ID3' (offsets):", matches)
else:
    print("File not found")
