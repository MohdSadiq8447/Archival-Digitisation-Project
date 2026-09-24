from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path("F:/1971-20260725T134344Z-1-001")
OUT=ROOT/"output"/"pdf"/"1971_trimmed"/"Gujarat"
SCRATCH=Path("C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/gujarat-output-renders-final")
POP=Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe")
SCRATCH.mkdir(parents=True,exist_ok=True)
font=ImageFont.load_default()
by_district={}
for pdf in sorted(OUT.glob("*.pdf")):
    district=pdf.stem.removeprefix("1971_")
    for suffix in ("_civic_amenities", "_medical_educational_amenities", "_tehsil_appendix"):
        if district.endswith(suffix): district=district.removesuffix(suffix)
    by_district.setdefault(district,[]).append(pdf)
for district,pdfs in sorted(by_district.items()):
    imgs=[]
    for pdf in sorted(pdfs):
        stem=pdf.stem
        render_dir=SCRATCH/stem; render_dir.mkdir(exist_ok=True)
        info=subprocess.run([str(POP.parent/"pdfinfo.exe"),str(pdf)],capture_output=True,text=True,check=True).stdout
        pages=next(int(line.split(":",1)[1].strip()) for line in info.splitlines() if line.startswith("Pages:"))
        for page in range(1,pages+1):
            prefix=render_dir/f"p{page:02d}"; png=Path(str(prefix)+".png")
            if not png.exists(): subprocess.run([str(POP),"-f",str(page),"-l",str(page),"-r","90","-png","-singlefile",str(pdf),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            im=Image.open(png).convert("RGB"); im.thumbnail((460,650)); can=Image.new("RGB",(480,690),"white"); can.paste(im,((480-im.width)//2,28)); ImageDraw.Draw(can).text((8,8),f"{pdf.name} page {page}",fill="black",font=font); imgs.append(can)
    cols=3; rows=(len(imgs)+cols-1)//cols; sheet=Image.new("RGB",(cols*480,rows*690),"#ddd")
    for i,im in enumerate(imgs): sheet.paste(im,((i%cols)*480,(i//cols)*690))
    sheet.save(SCRATCH/f"{district}_outputs_contact.png")
print(f"Rendered {sum(len(v) for v in by_district.values())} PDFs into {len(by_district)} district contact sheets.")
