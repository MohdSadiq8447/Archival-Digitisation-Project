from __future__ import annotations

import re
import sys
from pathlib import Path

import fitz


for source in sorted((Path("1981") / sys.argv[1]).glob("*.pdf")):
    document = fitz.open(source)
    hits = []
    for index, page in enumerate(document):
        text = " ".join(page.get_text("text").split())
        value = text.upper()
        score = 0
        if re.search(r"APPENDIX\s*[-–]?\s*I\b", value):
            score += 2
        if "ABSTRACT OF EDUCATIONAL" in value or "EDUCATIONAL, MEDICAL" in value:
            score += 3
        if any(term in value for term in ("TALUK", "TAHSIL", "TEHSIL", "TALUKA", "MAHAL", "CIRCLE")):
            score += 1
        if score >= 4 and "URBAN PRIMARY CENSUS" not in value:
            hits.append((index + 1, text[:300]))
    document.close()
    print(f"\n{source.name}")
    print("\n".join(f"{page}: {text}" for page, text in hits) or "(none)")
