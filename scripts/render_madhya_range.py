from pathlib import Path
import subprocess, sys
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
src=ROOT/'1971'/'Madhya Pradesh'/f'1971 {sys.argv[1]}.pdf'
first,last=int(sys.argv[2]),int(sys.argv[3])
out=Path(r'C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-ranges')/sys.argv[1].lower()
out.mkdir(parents=True,exist_ok=True)
pop=Path(r'C:\Users\USER\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe')
subprocess.run([str(pop),'-f',str(first),'-l',str(last),'-jpeg','-r','65',str(src),str(out/'p')],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
imgs=sorted(out.glob('p-*.jpg'))
thumbs=[]
for im in imgs:
    x=Image.open(im).convert('RGB'); x.thumbnail((250,340)); thumbs.append((im.name,x.copy()))
cols=5; cellw=270; cellh=375
sheet=Image.new('RGB',(cols*cellw,((len(thumbs)+cols-1)//cols)*cellh),'white'); d=ImageDraw.Draw(sheet)
for j,(label,x) in enumerate(thumbs):
    col=j%cols; row=j//cols; px=col*cellw+10; py=row*cellh+25
    d.text((px,5+row*cellh),label,fill='black'); sheet.paste(x,(px,py))
sheet.save(out/f'{sys.argv[1].lower()}-{first}-{last}.jpg',quality=88)
