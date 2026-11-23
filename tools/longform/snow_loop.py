import numpy as np, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
W,H,FPS,T=1920,1080,30,20
N=FPS*T
rng=np.random.default_rng(7)
base=Image.open(sys.argv[1]).convert("RGB").resize((W,H),Image.LANCZOS)
B=np.asarray(base).astype(np.float32)/255
r,g,b=B[...,0],B[...,1],B[...,2]
lum=0.3*r+0.59*g+0.11*b
warm=np.clip((r-b-0.25)*3,0,1)*np.clip((lum-0.55)*4,0,1)
warm=np.asarray(Image.fromarray((warm*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))).astype(np.float32)/255
# smooth random phase field so neighbouring lights flicker together
ph=rng.random((H//40+2,W//40+2)).astype(np.float32)
ph=np.asarray(Image.fromarray((ph*255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(np.float32)/255*2*np.pi
spark=(rng.random((H,W))<0.02).astype(np.float32)  # tiny sparkle points (tree lights)
layers=[  # count, radius, speed cycles per loop (integer => seamless), blur, alpha
 (700,1.3,1,0.6,0.55),(320,2.2,2,1.0,0.75),(70,4.0,3,2.2,0.85)]
parts=[]
for cnt,rad,cyc,bl,al in layers:
    parts.append(dict(x0=rng.random(cnt)*W,y0=rng.random(cnt)*(H+60)-30,ph=rng.random(cnt)*2*np.pi,
      amp=rng.random(cnt)*12+4,sw=rng.integers(1,3,cnt),rad=rad*(0.7+0.6*rng.random(cnt)),cyc=cyc,bl=bl,al=al))
p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
 "-c:v","libx264","-preset","slow","-crf",sys.argv[3],"-g",str(N),"-keyint_min",str(N),"-pix_fmt","yuv420p",sys.argv[2]],stdin=subprocess.PIPE)
for f in range(N):
    t=f/N
    tw=0.10*np.sin(2*np.pi*(2*t)+ph)+0.04*np.sin(2*np.pi*(5*t)+2*ph)
    sp=spark*warm*np.clip(np.sin(2*np.pi*(3*t)+ph*3),0,1)**4*0.6
    img=B*(1+warm[...,None]*tw[...,None])+sp[...,None]
    for L in parts:
        lay=Image.new("L",(W,H),0); d=ImageDraw.Draw(lay)
        y=(L["y0"]+t*L["cyc"]*(H+60))%(H+60)-30
        x=(L["x0"]+L["amp"]*np.sin(2*np.pi*L["sw"]*t+L["ph"]))%W
        for xi,yi,ri in zip(x,y,L["rad"]):
            d.ellipse((xi-ri,yi-ri,xi+ri,yi+ri),fill=255)
        if L["bl"]: lay=lay.filter(ImageFilter.GaussianBlur(L["bl"]))
        a=np.asarray(lay).astype(np.float32)/255*L["al"]
        img=img*(1-a[...,None])+0.97*a[...,None]
    p.stdin.write((np.clip(img,0,1)*255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
