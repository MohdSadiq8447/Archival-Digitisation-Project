from pathlib import Path
import subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path("F:/1971-20260725T134344Z-1-001")
SRC=ROOT/"1971"/"Gujarat"
OUT=Path("C:/Users/USER/.codex/visualizations/2026/09/07/01a07b9c-e77d-7511-9f66-aafc92441f90/gujarat-extra")
POP=Path("C:/Users/USER/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe")
cases={"Amreli":list(range(42,52)),"Jamnagar":list(range(44,54)),"Sabar_Kantha":list(range(50,60)),"Surendranagar":list(range(42,52)),"Junagadh":list(range(1,12))}
OUT.mkdir(parents=True,exist_ok=True)
font=ImageFont.load_default()
for stem,pages in cases.items():
    district=stem.replace("_"," ")
    src=SRC/f"1971 {district}.pdf"
    d=OUT/stem; d.mkdir(exist_ok=True)
    imgs=[]
    for page in pages:
        prefix=d/f"p{page:03d}"; png=Path(str(prefix)+".png")
        if not png.exists(): subprocess.run([str(POP),"-f",str(page),"-l",str(page),"-r","90","-png","-singlefile",str(src),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        im=Image.open(png).convert("RGB"); im.thumbnail((460,650)); can=Image.new("RGB",(480,690),"white"); can.paste(im,((480-im.width)//2,28)); ImageDraw.Draw(can).text((8,8),f"{district} source page {page}",fill="black",font=font); imgs.append(can)
    cols=3; rows=(len(imgs)+cols-1)//cols; sheet=Image.new("RGB",(cols*480,rows*690),"#ddd")
    for i,im in enumerate(imgs): sheet.paste(im,((i%cols)*480,(i//cols)*690))
    sheet.save(OUT/f"{stem}_contact.png")
