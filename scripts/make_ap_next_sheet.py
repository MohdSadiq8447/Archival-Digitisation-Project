from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


RENDER_DIR = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-next-pages")
OUT = Path(r"C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\ap-contact-sheets\next-pages.png")
DISTRICTS = [
    "Adilabad", "Anantapur", "Chittoor", "Cuddapah", "East Godavari", "Guntur",
    "Hyderabad", "Karimnagar", "Khammam", "Krishna", "Kurnool", "Mahbubnagar",
    "Medak", "Nalgonda", "Nellore", "Nizamabad", "Ongole (Prakasam)", "Srikakulam",
    "Visakhapatnam", "Warangal", "West Godavari",
]

thumb_w, thumb_h = 260, 350
cell_w, cell_h = 550, 390
sheet = Image.new("RGB", (cell_w * 2, cell_h * len(DISTRICTS)), "white")
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 15)
except OSError:
    font = ImageFont.load_default()

for row, district in enumerate(DISTRICTS):
    files = sorted(RENDER_DIR.glob(f"1971 {district}*-*.png"))
    if len(files) < 2:
        raise FileNotFoundError(district)
    for col, path in enumerate(files[:2]):
        with Image.open(path) as source:
            source = source.convert("RGB")
            source.thumbnail((thumb_w, thumb_h))
            x = col * cell_w + (cell_w - source.width) // 2
            y = row * cell_h + 25
            sheet.paste(source, (x, y))
        draw.text((col * cell_w + 8, row * cell_h + 5), f"{district}  {path.stem.split('-')[-1]}", fill="black", font=font)

OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT)
