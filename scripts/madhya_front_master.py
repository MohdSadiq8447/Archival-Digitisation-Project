from pathlib import Path
from PIL import Image, ImageDraw

out=Path(r'C:\Users\USER\.codex\visualizations\2026\09\07\01a07b9c-e77d-7511-9f66-aafc92441f90\madhya-front-check')
files=sorted(out.glob('*-contact.jpg'))
cols=4; cellw=560; cellh=430
master=Image.new('RGB',(cols*cellw,((len(files)+cols-1)//cols)*cellh),'white'); d=ImageDraw.Draw(master)
for j,p in enumerate(files):
    im=Image.open(p).convert('RGB'); im.thumbnail((cellw-10,cellh-35)); x=(j%cols)*cellw+5; y=(j//cols)*cellh+25
    master.paste(im,(x,y)); d.text((x,5+(j//cols)*cellh),p.stem,fill='black')
master.save(out/'madhya-front-master.jpg',quality=88)
