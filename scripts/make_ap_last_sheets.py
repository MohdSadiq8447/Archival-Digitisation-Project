from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


RENDER_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-output-rendered-v2")
SHEET_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-contact-sheets-v2")
DISTRICTS = [
    "Adilabad", "Anantapur", "Chittoor", "Cuddapah", "East Godavari", "Guntur",
    "Hyderabad", "Karimnagar", "Khammam", "Krishna", "Kurnool", "Mahbubnagar",
    "Medak", "Nalgonda", "Nellore", "Nizamabad", "Ongole (Prakasam)", "Srikakulam",
    "Visakhapatnam", "Warangal", "West Godavari",
]
TABLES = {
    "civic-last": "civic_amenities",
    "medical-last": "medical_educational_amenities",
    "appendix-last": "tehsil_appendix",
}


def make_sheet(label: str, suffix: str) -> None:
    thumb_w, thumb_h = 250, 330
    cell_w, cell_h = 300, 370
    cols = 3
    rows = (len(DISTRICTS) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        font = ImageFont.load_default()
    for index, district in enumerate(DISTRICTS):
        stem = f"1971_{district}_{suffix}"
        candidates = sorted(RENDER_DIR.glob(stem + "-*.png"))
        if not candidates:
            raise FileNotFoundError(stem)
        with Image.open(candidates[-1]) as source:
            source = source.convert("RGB")
            source.thumbnail((thumb_w, thumb_h))
            x = (index % cols) * cell_w + (cell_w - source.width) // 2
            y = (index // cols) * cell_h + 28
            sheet.paste(source, (x, y))
        tx = (index % cols) * cell_w + 8
        ty = (index // cols) * cell_h + 6
        draw.text((tx, ty), district, fill="black", font=font)
    SHEET_DIR.mkdir(parents=True, exist_ok=True)
    sheet.save(SHEET_DIR / f"{label}.png")


for label, suffix in TABLES.items():
    make_sheet(label, suffix)
