from pathlib import Path
import subprocess
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / '1971' / 'Madhya Pradesh'
OUT = Path(r'C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-front-check')
POPPLER = Path(r'C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')
OUT.mkdir(parents=True, exist_ok=True)
names = 'Betul Bhind Bilaspur Dewas Dhar Durg Guna Gwalior Hoshangabad Indore Jabalpur Jhabua Khandwa Khargone Mandla Mandsaur Satna Seoni Shahapur Surguja'.split()
for name in names:
    src = SRC / f'1971 {name}.pdf'
    stem = name.lower()
    d = OUT / stem
    d.mkdir(exist_ok=True)
    subprocess.run([str(POPPLER), '-f', '1', '-l', '8', '-jpeg', '-r', '50', str(src), str(d / 'page')], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    imgs = sorted(d.glob('page-*.jpg'))
    if not imgs:
        continue
    thumbs=[]
    for im in imgs:
        x=Image.open(im).convert('RGB'); x.thumbnail((260,350)); thumbs.append((im.name,x.copy()))
    sheet=Image.new('RGB',(4*280,2*390),'white'); draw=ImageDraw.Draw(sheet)
    for j,(label,x) in enumerate(thumbs[:8]):
        col=j%4; row=j//4; px=col*280+10; py=row*390+25
        sheet.paste(x,(px,py)); draw.text((px,5+row*390),label,fill='black')
    sheet.save(OUT / f'{stem}-contact.jpg', quality=90)
