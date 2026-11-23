#!/usr/bin/env python3
"""Seamless 20 s loop for calm scenes without snow: twinkling highlights (stars, lamps,
windows) plus a few slow floating glow particles drifting upward.
Usage: glow_loop.py IMAGE OUT.mp4 CRF"""
import numpy as np, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
W,H,FPS,T=1920,1080,30,20
N=FPS*T
rng=np.random.default_rng(11)
B=np.asarray(Image.open(sys.argv[1]).convert("RGB").resize((W,H),Image.LANCZOS)).astype(np.float32)/255
lum=0.3*B[...,0]+0.59*B[...,1]+0.11*B[...,2]
m=np.clip((lum-0.72)*5,0,1)
m=np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)/255
big=np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30))).astype(np.float32)/255
m=m*np.clip(1-big*2.5,0,1)   # twinkle only small highlights (stars, windows), not the moon
ph=rng.random((H//30+2,W//30+2)).astype(np.float32)
ph=np.asarray(Image.fromarray((ph*255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(np.float32)/255*2*np.pi
cnt=45
x0=rng.random(cnt)*W; y0=rng.random(cnt)*(H+80); r=1.5+2.5*rng.random(cnt)
amp=10+25*rng.random(cnt); pp=rng.random(cnt)*2*np.pi; sw=rng.integers(1,3,cnt)
glow=np.array([1.0,0.93,0.75],np.float32)
p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
 "-c:v","libx264","-preset","slow","-crf",sys.argv[3],"-g",str(N),"-pix_fmt","yuv420p",sys.argv[2]],stdin=subprocess.PIPE)
for f in range(N):
    t=f/N
    tw=0.22*(0.5+0.5*np.sin(2*np.pi*(2*t)+ph))-0.08
    img=B*(1+m[...,None]*tw[...,None])
    lay=Image.new("L",(W,H),0); d=ImageDraw.Draw(lay)
    y=(y0-t*(H+80))%(H+80)-40          # one full rise per loop -> seamless
    x=x0+amp*np.sin(2*np.pi*sw*t+pp)
    br=0.5+0.5*np.sin(2*np.pi*2*t+pp)
    for xi,yi,ri,bi in zip(x,y,r,br):
        d.ellipse((xi-ri,yi-ri,xi+ri,yi+ri),fill=int(120+135*bi))
    a=np.asarray(lay.filter(ImageFilter.GaussianBlur(2.5))).astype(np.float32)/255*0.8
    img=img*(1-a[...,None])+glow*a[...,None]
    p.stdin.write((np.clip(img,0,1)*255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
