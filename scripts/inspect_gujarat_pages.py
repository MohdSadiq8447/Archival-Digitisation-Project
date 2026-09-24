from pathlib import Path
import re
from pypdf import PdfReader

ROOT = Path("F:/1971-20260725T134344Z-1-001")
SRC = ROOT / "1971" / "Gujarat"

patterns = {
    "civic": re.compile(r"statement\s+iv|civic\s+and\s+other\s+amenit", re.I),
    "medical": re.compile(r"statement\s+v|medical.{0,20}educational|educational.{0,20}medical", re.I),
    "appendix": re.compile(r"abstract\s+of\s+amenit|taluk|taluka|tahsil|tehsil|mahal", re.I),
}

for path in sorted(SRC.glob("*.pdf")):
    reader = PdfReader(str(path))
    print(f"\n### {path.name} pages={len(reader.pages)}")
    for kind, pat in patterns.items():
        hits = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception as exc:
                text = f"[extract error {exc}]"
            compact = " ".join(text.split())
            if pat.search(compact):
                hits.append((i, compact[:260]))
        print(f"-- {kind}: {len(hits)} hits")
        for page_no, snippet in hits:
            print(f"{page_no}: {snippet}")
