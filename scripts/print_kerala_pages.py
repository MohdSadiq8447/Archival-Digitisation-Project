from pathlib import Path
import re
import sys

name = sys.argv[1]
first = int(sys.argv[2])
last = int(sys.argv[3])
p = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate") / f"1971_{name}.txt"
pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
for i in range(first, last + 1):
    print(f"--- p{i} ---\n{pages[i-1][:3000]}")
