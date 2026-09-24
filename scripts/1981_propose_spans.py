from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
state = sys.argv[1]
inventory = json.loads((ROOT / "output" / "audit" / "1981_inventory.json").read_text(encoding="utf-8"))


def compact(value: str) -> str:
    return " ".join(value.replace("\x00", " ").split()).upper()


def find_first(pages: list[str], pattern: str, exclude: str | None = None) -> int | None:
    regex = re.compile(pattern, re.I)
    for index, text in enumerate(pages, 1):
        if index < 80 or not regex.search(text):
            continue
        if exclude and re.search(exclude, text, re.I):
            continue
        return index
    return None


def boundary(pages: list[str], start: int, pattern: str) -> int | None:
    regex = re.compile(pattern, re.I)
    for index in range(start + 1, len(pages) + 1):
        if regex.search(pages[index - 1]):
            return index
    return None


def span(start: int | None, end: int | None) -> str:
    return "NONE" if start is None else f"[{start}-{end}]"


for item in inventory:
    if item["state"] != state or not item["eligible"]:
        continue
    doc = fitz.open(ROOT / item["source"])
    pages = [compact(page.get_text("text")) for page in doc]
    c = find_first(pages, r"STATEMENT\s*IV|CIVIC\s+AND\s+OTHER", r"IV\s*[-.]?\s*A")
    m = find_first(pages, r"STATEMENT\s*V|MEDICAL.{0,100}EDUCATIONAL", r"STATEMENT\s*VI")
    a = find_first(pages, r"APPENDIX\s*(I|1).{0,160}(ABSTRACT|AMENITIES)|TAHSILWISE\s+ABSTRACT|TEHSILWISE\s+ABSTRACT")
    if c and re.search(r"CIVIC|ROAD", pages[c - 2], re.I) and re.search(r"POPUL|ROAD", pages[c - 2], re.I) and not re.search(r"STATEMENT\s*III", pages[c - 2], re.I):
        c -= 1
    if m and re.search(r"MEDICAL|EDUCATIONAL", pages[m - 2], re.I) and not re.search(r"IV\s*[-.]?\s*A", pages[m - 2], re.I):
        m -= 1
    if a and re.search(r"EDUCATIONAL|MEDICAL|TAHSIL|TEHSIL|PRIMARY", pages[a - 2], re.I) and not re.search(r"APPENDIX\s*II", pages[a - 2], re.I):
        a -= 1
    cb = boundary(pages, c, r"IV\s*[-.]?\s*[A3]|CIVIC\s+AND\s+OTHER.{0,60}SLUM|AREA\s+OF\s+SLUM|PAVED\s+ROADS|NOTIFIED\s+SLUM") if c else None
    if not cb and c:
        cb = boundary(pages, c, r"STATEMENT\s*V|MEDICAL.{0,100}EDUCATIONAL")
    mb = boundary(pages, m, r"STATEMENT\s*VI|TRADE.{0,40}COMMERCE|COMMERCE.{0,40}INDUSTRY|TRADE.{0,40}INDUSTRY") if m else None
    if not mb and m:
        mb = boundary(pages, m, r"APPENDIX")
    ab = boundary(pages, a, r"APPENDIX\s*(II|2|III|3)|LAND.{0,30}UTIL|LIST\s+OF\s+VILLAGES|TOWNS\s+SHOWING") if a else None
    print(json.dumps({"district": item["district"], "civic": [c, cb - 1 if cb else None] if c else None, "medical": [m, mb - 1 if mb else None] if m else None, "appendix": [a, ab - 1 if ab else None] if a else None}, ensure_ascii=False))
    doc.close()
