import subprocess, json, sys
D="/mnt/user-data/uploads/000 Stap 3 LW Actief/NLWL72600914 -933 Kael Hope - Peaceful Christmas Piano/"
order=["First Snowfall","Candles In The Window","Silent Street","Fireside","Winter Lights","Christmas Morning","Frosted Glass","Wrapping Paper","Midnight Mass","Home For The Holidays",
"Winter Lights (Alternate Version)","First Snowfall (Alternate Version)","Fireside (Alternate Version)","Frosted Glass (Alternate Version)","Candles In The Window (Alternate Version)","Wrapping Paper (Alternate Version)","Silent Street (Alternate Version)","Christmas Morning (Alternate Version)","Home For The Holidays (Alternate Version)","Midnight Mass (Alternate Version)"]
XF=3.0
def dur(f): return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",f]))
files=[D+t+"_01.wav" for t in order]
ds=[dur(f) for f in files]
t=0; chapters=[]
for i,(n,d) in enumerate(zip(order,ds)):
    chapters.append((t,n)); t+=d-(XF if i<len(ds)-1 else 0)
total=t
inp=[]
for f in files: inp+=["-i",f]
fc=""; prev="[0:a]"
for i in range(1,len(files)):
    out=f"[x{i}]"; fc+=f"{prev}[{i}:a]acrossfade=d={XF}:c1=tri:c2=tri{out};"; prev=out
fc+=f"{prev}afade=t=in:d=2,afade=t=out:st={total-4}:d=4,aresample=48000[a]"
subprocess.check_call(["ffmpeg","-y","-loglevel","error",*inp,"-filter_complex",fc,"-map","[a]","-c:a","aac","-b:a","192k","pass1.m4a"])
json.dump({"total":total,"chapters":chapters},open("chapters.json","w"),indent=1)
print(total)
