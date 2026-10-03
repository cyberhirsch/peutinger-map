"""Contact sheets for checking proposed positions.
usage: render_points.py <scratch> <in.json> <out_prefix>
in.json: [{"num":..,"name":..,"x":..,"y":..}, ...]  -> <out_prefix>_NN.jpg (3x3 tiles each)"""
import sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
S,inp,pre=sys.argv[1],sys.argv[2],sys.argv[3]
im=np.load(f'{S}/img.npy'); H,W=im.shape[:2]
pts=json.load(open(inp))
f=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',15)
TW,TH=420,280; out=[]
for si in range(0,len(pts),9):
    sheet=Image.new('RGB',(TW*3,(TH+22)*3),'white'); d=ImageDraw.Draw(sheet)
    for j,p in enumerate(pts[si:si+9]):
        x,y=int(p['x']),int(p['y']); a,b=max(0,x-TW//2),max(0,y-TH//2)
        t=Image.fromarray(im[b:b+TH,a:a+TW]).convert('RGB'); td=ImageDraw.Draw(t)
        px,py=x-a,y-b; td.ellipse([px-7,py-7,px+7,py+7],outline=(230,0,200),width=3); td.line([(px-14,py),(px-8,py)],fill=(230,0,200),width=2)
        ox,oy=(j%3)*TW,(j//3)*(TH+22)
        sheet.paste(t,(ox,oy+22)); d.text((ox+4,oy+3),f"#{p['num']}: {p['name']}",fill=(0,0,0),font=f)
    fn=f'{pre}_{si//9:02d}.jpg'; sheet.save(fn,quality=88); out.append(fn)
print(json.dumps(out))
