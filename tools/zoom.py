"""Magnified view of a scan region with absolute-coordinate ticks every 50 px.
usage: zoom.py <x0> <y0> <x1> <y1> <out.jpg> [scale=2]"""
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
S='/private/tmp/claude-503/-Users-sebhirsch-Documents-Misc/bd4160dd-3d21-4dde-a89f-169a63fb38aa/scratchpad'
x0,y0,x1,y1=map(int,sys.argv[1:5]); out=sys.argv[5]; sc=float(sys.argv[6]) if len(sys.argv)>6 else 2
im=np.load(f'{S}/img.npy', mmap_mode='r')
I=Image.fromarray(np.ascontiguousarray(im[y0:y1,x0:x1])).convert('RGB'); I=I.resize((int(I.width*sc),int(I.height*sc)),Image.LANCZOS)
d=ImageDraw.Draw(I); f=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',13)
for gx in range((x0//50+1)*50,x1,50):
    X=(gx-x0)*sc; d.line([(X,0),(X,10)],fill=(0,0,255),width=2); d.text((X+2,11),str(gx),fill=(0,0,255),font=f)
for gy in range((y0//50+1)*50,y1,50):
    Y=(gy-y0)*sc; d.line([(0,Y),(10,Y)],fill=(0,0,255),width=2); d.text((12,Y-7),str(gy),fill=(0,0,255),font=f)
I.save(out,quality=90); print(out)
