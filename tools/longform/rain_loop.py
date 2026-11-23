#!/usr/bin/env python3
"""Seamless 20 s rain loop: thin slanted streaks in two depths plus gentle twinkle on lights.
Usage: rain_loop.py IMAGE OUT.mp4 CRF"""
import numpy as np, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter
W,H,FPS,T=1920,1080,30,20
N=FPS*T
rng=np.random.default_rng(5)
B=np.asarray(Image.open(sys.argv[1]).convert("RGB").resize((W,H),Image.LANCZOS)).astype(np.float32)/255
lum=0.3*B[...,0]+0.59*B[...,1]+0.11*B[...,2]
m=np.clip((lum-0.65)*4,0,1)*np.clip((B[...,0]-B[...,2]+0.1)*3,0,1)
m=np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))).astype(np.float32)/255
big=np.asarray(Image.fromarray((m*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(30))).astype(np.float32)/255
m=m*np.clip(1-big*2.5,0,1)
ph=rng.random((H//30+2,W//30+2)).astype(np.float32)
ph=np.asarray(Image.fromarray((ph*255).astype(np.uint8)).resize((W,H),Image.BICUBIC)).astype(np.float32)/255*2*np.pi
layers=[(900,18,0.9,12,0.22),(350,34,1.4,20,0.32)]  # count, length, width, cycles per loop, alpha
P=[dict(x0=rng.random(c)*(W+200)-100,y0=rng.random(c)*(H+100),L=L,w=w,cy=cy,al=al) for c,L,w,cy,al in layers]
p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
 "-c:v","libx264","-preset","slow","-crf",sys.argv[3],"-g",str(N),"-pix_fmt","yuv420p",sys.argv[2]],stdin=subprocess.PIPE)
for f in range(N):
    t=f/N
    tw=0.16*(0.5+0.5*np.sin(2*np.pi*(2*t)+ph))-0.06
    img=B*(1+m[...,None]*tw[...,None])
    for L in P:
        lay=Image.new("L",(W,H),0); d=ImageDraw.Draw(lay)
        y=(L["y0"]+t*L["cy"]*(H+100))%(H+100)-50
        x=L["x0"]+0.12*(y+50)
        for xi,yi in zip(x,y):
            d.line((xi,yi,xi+0.12*L["L"],yi+L["L"]),fill=255,width=max(1,int(round(L["w"]))))
        a=np.asarray(lay.filter(ImageFilter.GaussianBlur(0.6))).astype(np.float32)/255*L["al"]
        img=img*(1-a[...,None])+0.85*a[...,None]
    p.stdin.write((np.clip(img,0,1)*255).astype(np.uint8).tobytes())
p.stdin.close(); p.wait()
