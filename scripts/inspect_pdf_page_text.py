from pathlib import Path
import sys
from pypdf import PdfReader


source = Path(sys.argv[1])
pages = [int(value) for value in sys.argv[2:]]
reader = PdfReader(str(source))
for number in pages:
    text = reader.pages[number - 1].extract_text() or ""
    print(f"--- page {number} ---")
    print(" ".join(text.split())[:1200])
