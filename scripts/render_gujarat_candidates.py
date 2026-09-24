from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("F:/1971-20260725T134344Z-1-001")
SRC = ROOT / "1971" / "Gujarat"
OUT = Path("C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/gujarat-candidates")
POPPLER = Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin")
OUT.mkdir(parents=True, exist_ok=True)

ranges = {
    "Ahmadabad": [54,55,56,57,58,59,120,121,122,123],
    "Amreli": [98,99,100,101,102,128,129,130,131],
    "Banas Kantha": [54,55,56,57,58,192,193,194,195],
    "Bharuch": [54,55,56,57,58,166,167,168,169],
    "Bhavnagar": [51,52,53,54,55,150,151,152,153],
    "Gandhinagar": [36,37,38,39,40,48,49,50,51],
    "Jamnagar": [102,103,104,105,106,138,139,140,141],
    "Kheda": [51,52,53,54,55,56,57,134,135,136,137],
    "Kutch": [52,53,54,55,56,168,169,170,171],
    "Mahesana": [53,54,55,56,57,160,161,162,163],
    "Panch Mahals": [64,65,66,67,68,240,241,242,243],
    "Rajkot": [56,57,58,59,60,166,167,168,169],
    "Sabar Kantha": [114,115,116,117,118,190,191,192,193],
    "Surat": [62,63,64,65,66,208,209,210,211],
    "Surendranagar": [98,99,100,101,102,130,131,132,133],
    "The Dangs": [52,53,54,55],
    "Vadodara": [55,56,57,58,59,209,210,211,212],
    "Valsad": [51,52,53,54,55,140,141,142,143],
}

font = ImageFont.load_default()
for district, pages in ranges.items():
    src = SRC / f"1971 {district}.pdf"
    stem = district.replace(" ", "_")
    d = OUT / stem
    d.mkdir(exist_ok=True)
    imgs=[]
    for page in pages:
        prefix = d / f"p{page:03d}"
        png = Path(str(prefix) + ".png")
        if not png.exists():
            subprocess.run([str(POPPLER / "pdftoppm.exe"), "-f", str(page), "-l", str(page), "-r", "90", "-png", "-singlefile", str(src), str(prefix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        im = Image.open(png).convert("RGB")
        im.thumbnail((460, 650))
        canvas = Image.new("RGB", (480, 690), "white")
        canvas.paste(im, ((480-im.width)//2, 28))
        ImageDraw.Draw(canvas).text((8, 8), f"{district} source page {page}", fill="black", font=font)
        imgs.append(canvas)
    cols=3
    rows=(len(imgs)+cols-1)//cols
    sheet=Image.new("RGB", (cols*480, rows*690), "#dddddd")
    for i,im in enumerate(imgs): sheet.paste(im, ((i%cols)*480, (i//cols)*690))
    sheet.save(OUT / f"{stem}_contact.png")
