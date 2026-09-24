from pathlib import Path
import re
root = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\kerala-locate")
for name in ("Malappuram", "Palghat", "Quilon", "Kottayam", "Kozhikode", "Trichur", "Trivandrum", "Alleppey", "Cannanore"):
    p = root / f"1971_{name}.txt"
    pages = [re.sub(r"\s+", " ", x.replace("\u00ad", " ")).strip() for x in p.read_text(encoding="utf-8", errors="replace").split("\f")]
    print(f"=== {name} ===")
    for i in range(20, 29):
        t = pages[i-1]
        print(f"p{i} len={len(t)} terms={{civic:{t.lower().find('civic')}, med:{t.lower().find('medical,')}, amen:{t.lower().find('amenities')}, cult:{t.lower().find('cultural facilities')}}}")
