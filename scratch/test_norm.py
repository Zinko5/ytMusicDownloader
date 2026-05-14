import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from utiles.core import normalize_text

test_str = "Te Quiero (…)"
normalized = normalize_text(test_str)
print(f"Original: {test_str}")
print(f"Normalized: {normalized}")
print(f"Match: {normalized == 'Te Quiero (...)'}")
for i, c in enumerate(normalized):
    print(f"  {i}: {c} (U+{ord(c):04X})")
