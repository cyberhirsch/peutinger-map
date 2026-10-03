"""Render numbered review crops for one Talbert segment.
usage: render_review.py <scratch> <segment 1-11> [stations.json]"""
import sys, json, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
S=sys.argv[1]; seg=int(sys.argv[2]); fn=sys.argv[3] if len(sys.argv)>3 else 'stations2.json'
sys.path.insert(0,S); from grid import EDGES
im=np.load(f'{S}/img.npy')
st=json.load(open(f'{S}/{fn}'))
x0,x1=EDGES[seg-1],EDGES[seg]
mine=[s for s in st if x0<=s['x']<x1]
mine.sort(key=lambda s:(s['x'],s['y']))
for i,s in enumerate(mine,1): s['num']=i
out=f'{S}/review/seg{seg:02d}'; os.makedirs(out,exist_ok=True)
try: font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf',15); small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',12)
except Exception: font=small=ImageFont.load_default()
CW,CH,OV=760,520,80
crops=[]; ci=0
for cy in range(330,1620,CH-OV):
    for cx in range(x0-40,x1+40,CW-OV):
        a,b=max(cx,0),cy; c,d=min(cx+CW,im.shape[1]),min(cy+CH,im.shape[0])
        I=Image.fromarray(im[b:d,a:c]).convert('RGB'); dr=ImageDraw.Draw(I)
        for gx in range((a//100+1)*100,c,100):
            dr.line([(gx-a,0),(gx-a,8)],fill=(0,0,255),width=2); dr.text((gx-a+2,9),str(gx),fill=(0,0,255),font=small)
            dr.line([(gx-a,d-b-8),(gx-a,d-b)],fill=(0,0,255),width=2)
        for gy in range((b//100+1)*100,d,100):
            dr.line([(0,gy-b),(8,gy-b)],fill=(0,0,255),width=2); dr.text((10,gy-b-7),str(gy),fill=(0,0,255),font=small)
            dr.line([(c-a-8,gy-b),(c-a,gy-b)],fill=(0,0,255),width=2)
        inside=[s for s in mine if a<=s['x']<c and b<=s['y']<d]
        for s in inside:
            px,py=s['x']-a,s['y']-b
            col=(230,0,200) if s['c'] in ('interp','grid') else (0,170,0)
            dr.ellipse([px-5,py-5,px+5,py+5],outline=col,width=3)
            dr.text((px+6,py-18),str(s['num']),fill=col,font=font,stroke_width=2,stroke_fill=(255,255,255))
        name=f'crop{ci:02d}_x{a}-{c}_y{b}-{d}.jpg'; I.save(f'{out}/{name}',quality=88)
        crops.append(dict(file=f'{out}/{name}',x=[a,c],y=[b,d],nums=[s['num'] for s in inside])); ci+=1
legend=[dict(num=s['num'],id=s['id'],name=s['n'],modern=s.get('m',''),method=s['c'],x=s['x'],y=s['y'],grid=s.get('grid',[])) for s in mine]
json.dump(dict(segment=seg,x_range=[x0,x1],crops=crops,places=legend),open(f'{out}/legend.json','w'),ensure_ascii=False,indent=0)
print(out,len(crops),'crops',len(mine),'places')
