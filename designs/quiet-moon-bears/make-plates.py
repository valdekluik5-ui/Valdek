# Turns the two turnaround sheets (sheet-he.jpg, sheet-she.jpg) into the fur-colour plates the 3D bears in Quiet Moon
# are painted with (quiet-moon/bears/*.jpg): one image per view, shading removed, eyes/nose/mouth/pads/flower painted
# out with surrounding fur, background filled with the nearest fur colour. Run: python3 make-plates.py
# It prints where the bear's outline sits in each plate; those numbers go into PM in quiet-moon/index.html.
import json, os, numpy as np
from PIL import Image, ImageFilter, ImageDraw
HERE=os.path.dirname(os.path.abspath(__file__))
U=HERE+'/'
OUT=os.path.join(HERE,'..','..','quiet-moon','bears')+'/'
H=384  # plate height in pixels
SHEETS={
 'he':{'file':'sheet-he.jpg','cuts':{'front':(0,500),'side':(500,915),'back':(915,1376)},
   'holes':{'front':[(214,230,19,19),(330,230,19,19),(272,265,34,24),(272,300,48,14),(122,510,26,30),(425,510,26,30),(108,620,50,60),(432,618,50,60)],
            'side':[(636,232,13,13),(565,265,15,15)],'back':[]},
   'pads':[(108,632,30,36),(432,630,30,36)],'palms':[(122,512,14,18),(425,512,14,18)]},
 'she':{'file':'sheet-she.jpg','cuts':{'front':(0,495),'side':(520,925),'back':(935,1376)},
   'holes':{'front':[(189,256,30,26),(316,251,30,26),(255,297,36,26),(255,335,32,14),(112,520,26,30),(395,522,26,30),(90,648,50,58),(410,648,50,58)],
            'side':[(630,258,16,16),(564,292,15,16)],'back':[]},
   'pads':[(90,660,30,36),(410,660,30,36)],'palms':[(112,522,14,18),(395,522,14,18)]}}

def fill(img,hole,iters=600):
    # harmonic fill: every hole pixel becomes the average of its neighbours, repeated until smooth
    a=img.copy(); a[hole]=a[~hole].mean(0)
    for _ in range(iters):
        p=np.pad(a,((1,1),(1,1),(0,0)),mode='edge')
        avg=(p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:])/4
        a[hole]=avg[hole]
    return a

def blur(z,s):
    # separable gaussian blur in float
    r=int(s*3); x=np.arange(-r,r+1); k=np.exp(-x*x/(2*s*s)); k/=k.sum()
    z=np.apply_along_axis(lambda v:np.convolve(np.pad(v,r,mode='edge'),k,'valid'),0,z)
    return np.apply_along_axis(lambda v:np.convolve(np.pad(v,r,mode='edge'),k,'valid'),1,z)
meta={}; avg={}
for name,S in SHEETS.items():
    sh=Image.open(U+S['file']).convert('RGB'); A=np.asarray(sh).astype(np.float32)
    bg=np.median(A[5:40,5:40].reshape(-1,3),0)
    r,g,b=A[...,0],A[...,1],A[...,2]
    bear=(np.abs(A-bg).sum(2)>40)&(r-b>14)
    pink=(r-g>32)&(b-g>4)                      # the crochet flower
    pink=np.asarray(Image.fromarray((pink*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17)))>0
    # pad and palm colours for the 3D pads
    def mean_in(ells):
        m=Image.new('L',sh.size,0); d=ImageDraw.Draw(m)
        for (x,y,rx,ry) in ells: d.ellipse([x-rx,y-ry,x+rx,y+ry],fill=255)
        m=np.asarray(m)>0; return A[m].mean(0)
    avg[name]={'pad':mean_in(S['pads']).round().tolist(),'palm':mean_in(S['palms']).round().tolist()}
    meta[name]={}
    for v,(x0,x1) in S['cuts'].items():
        holes=Image.new('L',sh.size,0); d=ImageDraw.Draw(holes)
        for (x,y,rx,ry) in S['holes'][v]: d.ellipse([x-rx,y-ry,x+rx,y+ry],fill=255)
        hole=(np.asarray(holes)>0)|pink
        m=bear.copy(); m[:, :x0]=False; m[:, x1:]=False
        body=m&~pink
        ys,xs=np.nonzero(body); bx0,bx1,by0,by1=xs.min(),xs.max(),ys.min(),ys.max()
        pad=int((by1-by0)*.06); cx0,cx1,cy0,cy1=max(0,bx0-pad),min(A.shape[1],bx1+pad),max(0,by0-pad),min(A.shape[0],by1+pad)
        crop=A[cy0:cy1,cx0:cx1]; cm=m[cy0:cy1,cx0:cx1]; ch=hole[cy0:cy1,cx0:cx1]&cm
        # remove the baked-in shading: divide by a heavily blurred brightness of the fur only
        L=crop.mean(2); w=(cm&~ch).astype(np.float32)
        sig=(by1-by0)*.035
        bl=lambda z:blur(z.astype(np.float32),float(sig))
        Lb=bl(L*w)/np.maximum(bl(w),1e-3); Lm=(L*w).sum()/w.sum()
        k=np.clip((Lm/np.maximum(Lb,1))**.95,.55,2.0)[...,None]
        flat=np.clip(crop*k,0,255)
        # paint out features and the background with surrounding fur
        sc=H/crop.shape[0]; W=int(round(crop.shape[1]*sc))
        small=lambda z,res=Image.BILINEAR:np.asarray(Image.fromarray(z).resize((W,H),res))
        f=small(flat.astype(np.uint8)).astype(np.float32)
        keep=small((cm&~ch).astype(np.uint8)*255,Image.NEAREST)>127
        keep=np.asarray(Image.fromarray(keep.astype(np.uint8)*255).filter(ImageFilter.MinFilter(7)))>0  # drop the light edge pixels
        hole2=~keep; base=fill(f,hole2)
        # give the painted-out spots the same fur grain: copy fine detail from nearby fur
        det=f-np.stack([blur(f[...,i],2.0) for i in range(3)],-1)
        add=np.zeros_like(f); got=np.zeros(hole2.shape,bool)
        for dx,dy in [(34,0),(-34,0),(0,34),(0,-34),(48,30),(-48,30),(48,-30),(-48,-30),(70,0),(-70,0),(0,70)]:
            src=np.roll(np.roll(det,dy,0),dx,1); ok=np.roll(np.roll(keep,dy,0),dx,1)&hole2&~got
            add[ok]=src[ok]; got|=ok
        inside=np.asarray(Image.fromarray(cm.astype(np.uint8)*255).resize((W,H),Image.NEAREST))>127
        f=base+add*inside[...,None]
        # soften: the 3D fur draws its own strands, the plate only carries colour (sharp grain would flicker as blotches)
        f=np.stack([blur(f[...,i],2.2) for i in range(3)],-1)
        Image.fromarray(np.clip(f,0,255).astype(np.uint8)).save(f'{OUT}{name}-{v}.jpg',quality=88)
        # where the bear's outline sits inside the plate (fractions), for lining it up with the 3D model
        meta[name][v]=[round((bx0-cx0)/crop.shape[1],4),round((by0-cy0)/crop.shape[0],4),round((bx1-cx0)/crop.shape[1],4),round((by1-cy0)/crop.shape[0],4)]
print(json.dumps(meta)); print(json.dumps(avg))
