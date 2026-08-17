import json
import openpyxl
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

DROPOBOX_LINKS = {
    "Census_1971.xlsx": "https://www.dropbox.com/scl/fi/ouep88b5q9ln5xstly03w/Census_1971.xlsx?rlkey=fnn3qthzf23tkbfz6cvf4remz&st=q1lskr26&dl=1",
    "Census_1981.xlsx": "https://www.dropbox.com/scl/fi/77jgh5ahsk3c0olfhcwcm/Census_1981.xlsx?rlkey=mlgfb6uwkz1qq5twzqyv7vmey&st=mtr29ode&dl=1"
}


def process_excel(filepath, year):
    wb = openpyxl.load_workbook(filepath)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        state, district, availability, language = row
        if not state or not district:
            continue
        rows.append({
            "state": str(state).strip(),
            "district": str(district).strip(),
            "available": str(availability).strip() if availability else "No",
            "language": str(language).strip() if language else "Unknown",
            "year": year
        })
    return rows


def compute_stats(rows):
    total = len(rows)
    available = sum(1 for r in rows if r["available"] == "Yes")
    not_available = sum(1 for r in rows if r["available"] != "Yes")
    english = sum(1 for r in rows if r["language"] == "Yes")
    hindi = sum(1 for r in rows if r["language"] == "No")
    no_pdf = sum(1 for r in rows if r["language"] == "No PDF")
    unknown = sum(1 for r in rows if r["language"] not in ("Yes", "No", "No PDF"))

    states_list = sorted(set(r["state"] for r in rows))
    state_stats = []
    for st in states_list:
        st_rows = [r for r in rows if r["state"] == st]
        st_total = len(st_rows)
        st_avail = sum(1 for r in st_rows if r["available"] == "Yes")
        st_english = sum(1 for r in st_rows if r["language"] == "Yes")
        st_hindi = sum(1 for r in st_rows if r["language"] == "No")
        st_no_pdf = sum(1 for r in st_rows if r["language"] == "No PDF")
        state_stats.append({
            "state": st,
            "total": st_total,
            "available": st_avail,
            "not_available": st_total - st_avail,
            "english": st_english,
            "hindi": st_hindi,
            "no_pdf": st_no_pdf,
            "availability_pct": round(st_avail / st_total * 100, 1) if st_total else 0
        })

    return {
        "total": total,
        "available": available,
        "not_available": not_available,
        "availability_pct": round(available / total * 100, 1) if total else 0,
        "english": english,
        "hindi": hindi,
        "no_pdf": no_pdf,
        "unknown": unknown,
        "states_count": len(states_list),
        "state_stats": state_stats
    }


def main():
    all_rows = []

    for fname, url in DROPOBOX_LINKS.items():
        year = int(fname.split("_")[1].split(".")[0])
        path = DATA_DIR / fname

        if path.exists():
            rows = process_excel(path, year)
            all_rows.extend(rows)
            print(f"Processed {fname}: {len(rows)} districts")
        else:
            print(f"WARNING: {fname} not found at {path}")

    with open(ROOT / "data.json", "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    stats_1971 = compute_stats([r for r in all_rows if r["year"] == 1971])
    stats_1981 = compute_stats([r for r in all_rows if r["year"] == 1981])

    with open(ROOT / "stats.json", "w", encoding="utf-8") as f:
        json.dump({"1971": stats_1971, "1981": stats_1981}, f, ensure_ascii=False, indent=2)

    print(f"\nTotal districts: {len(all_rows)}")
    print(f"1971: {stats_1971['total']} districts | Available: {stats_1971['available']} ({stats_1971['availability_pct']}%) | English: {stats_1971['english']} | Hindi: {stats_1971['hindi']}")
    print(f"1981: {stats_1981['total']} districts | Available: {stats_1981['available']} ({stats_1981['availability_pct']}%) | English: {stats_1981['english']} | Hindi: {stats_1981['hindi']}")


if __name__ == "__main__":
    main()
