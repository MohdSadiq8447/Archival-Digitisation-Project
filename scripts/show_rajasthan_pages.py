from pathlib import Path
import re

CACHE_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\rajasthan-locate")
requests = {
    "Churu": (80, 90),
    "Jhunjhunun": (84, 92),
    "Kota": (149, 157),
    "Jaisalmer": (66, 73),
    "Bhilwara": (120, 126),
    "Bundi": (72, 78),
}
for district, (start, end) in requests.items():
    path = CACHE_DIR / f"1971_{district}.txt"
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"=== {district} ===")
    for num in range(start, end + 1):
        lines = [re.sub(r"\s+", " ", line).strip() for line in pages[num-1].splitlines() if line.strip()]
        print(f"p{num}: " + " | ".join(lines[:12]))
