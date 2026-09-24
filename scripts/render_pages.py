import sys
from pathlib import Path

import fitz

source = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
pages = [int(value) for value in sys.argv[3:]]
out_dir.mkdir(parents=True, exist_ok=True)
doc = fitz.open(str(source))
for number in pages:
    pix = doc[number - 1].get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
    pix.save(str(out_dir / f"page-{number}.png"))
print(out_dir)
