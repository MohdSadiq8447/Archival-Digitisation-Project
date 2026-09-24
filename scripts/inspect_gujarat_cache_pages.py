from pathlib import Path
import re

CACHE = Path(r"C:\\Users\\USER\\.codex\\visualizations\\2026\\09\\07\\01a07b9c-e77d-7511-9f66-aafc92441f90\\gujarat-locate")
patterns = {
    "civic": re.compile(r"statement\s+iv|civic\s+and\s+other\s+amenit", re.I),
    "medical": re.compile(r"statement\s+v|medical.{0,30}educational|educational.{0,30}medical", re.I),
    "appendix": re.compile(r"abstract\s+of\s+amenit|taluk|taluka|tahsil|tehsil|mahal", re.I),
}
for path in sorted(CACHE.glob("*.txt")):
    pages = path.read_text(encoding="utf-8", errors="replace").split("\f")
    print(f"\n### {path.stem} pages={len(pages)}")
    for kind, pat in patterns.items():
        hits = []
        for i, page in enumerate(pages, start=1):
            compact = " ".join(page.split())
            if pat.search(compact):
                hits.append((i, compact[:260]))
        print(f"-- {kind}: {len(hits)} hits")
        for page_no, snippet in hits:
            print(f"{page_no}: {snippet}")
