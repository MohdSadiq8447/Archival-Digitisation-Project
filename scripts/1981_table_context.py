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
    return " ".join(value.replace("\x00", " ").split())


def first_page(pages: list[tuple[int, str]], pattern: str, exclude: str | None = None) -> int | None:
    regex = re.compile(pattern, re.I)
    for number, text in pages:
        if number < 80:
            continue
        if exclude and re.search(exclude, text, re.I):
            continue
        if regex.search(text):
            return number
    return None


for item in inventory:
    if item["state"] != state or not item["eligible"]:
        continue
    source = ROOT / item["source"]
    doc = fitz.open(source)
    pages = [(number, compact(doc[number - 1].get_text("text"))) for number in range(1, len(doc) + 1)]
    civic = first_page(pages, r"STATEMENT IV|CIVIC AND OTHER", r"IV[- ]?A")
    medical = first_page(pages, r"STATEMENT V|MEDICAL.{0,80}EDUCATIONAL", r"STATEMENT VI")
    appendix = first_page(pages, r"APPENDIX I.{0,140}(ABSTRACT|AMENITIES)|TAHSILWISE ABSTRACT|TEHSILWISE ABSTRACT")
    print(f"\n{item['district']} ({len(doc)} pages)")
    for label, start, stop in (("CIVIC", civic, r"STATEMENT IV[- ]?A"), ("MED", medical, r"STATEMENT VI"), ("APPX", appendix, r"APPENDIX II|APPENDIX 2")):
        if not start:
            print(f"  {label}: NONE")
            continue
        boundary = None
        for number, text in pages:
            if number > start and re.search(stop, text, re.I):
                boundary = number
                break
        end = (boundary - 1) if boundary else min(start + 12, len(doc))
        lo = max(1, start - 1)
        hi = min(len(doc), end + 1)
        print(f"  {label}: candidate={start}-{end} boundary={boundary}")
        for number in range(lo, hi + 1):
            text = dict(pages)[number]
            print(f"    {number}: {text[:180]}")
    doc.close()
