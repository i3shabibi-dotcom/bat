import json,re,subprocess,sys,os
sc=json.load(open('scenes.json'))
GAP=0.12; LEAD=0.0
SPOKEN={'2027':18,'6.4':18,'7':5,'OLED':5}
def dur(p): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',p]))
def speech_bounds(p):
    out=subprocess.run(['ffmpeg','-i',p,'-af','silencedetect=noise=-40dB:d=0.08','-f','null','-'],capture_output=True,text=True).stderr
    D=dur(p); st=re.findall(r'silence_start: ([\d.]+)',out); en=re.findall(r'silence_end: ([\d.]+)',out)
    s0=float(en[0]) if st and float(st[0])<0.02 and en else 0.0
    s1=float(st[-1]) if st and float(st[-1])>D-1.5 and float(st[-1])>s0 else D
    return D,s0,s1
t=0; out=[]
for i,s in enumerate(sc):
    f=f'vo/{i+1:02d}_{s["id"]}.mp3'
    if os.path.exists(f): D,s0,s1=speech_bounds(f)
    else:
        n=len(s['tts'].split()); D=n/2.45+0.35; s0=0.1; s1=D-0.2
    words=s['cap'].split()
    wts=[SPOKEN.get(w.strip('،.؟…:'),len(re.sub(r'[ً-ْ]','',w)))+1.5 for w in words]
    tot=sum(wts); cur=t+s0; W=[]
    for w,wt in zip(words,wts):
        W.append({'w':w,'t':round(cur,3)}); cur+=(s1-s0)*wt/tot
    # chunk ~ up to 4 words / break after punctuation
    chunks=[];c=[]
    for w in W:
        c.append(w)
        if len(c)>=4 or re.search(r'[،.؟…:]$',w['w']): chunks.append(c);c=[]
    if c: chunks.append(c)
    CH=[]
    for k,c in enumerate(chunks):
        t0=c[0]['t']; t1=chunks[k+1][0]['t'] if k+1<len(chunks) else t+D+GAP
        CH.append({'t0':t0,'t1':t1,'words':c})
    e={'id':s['id'],'start':round(t,3),'end':round(t+D,3),'file':f,'chunks':CH}
    if 'split' in s:
        idx=next(j for j,w in enumerate(W) if w['w'].startswith(s['split']))
        e['splitT']=round(W[idx]['t']-t,3)
    out.append(e); t+=D+GAP
total=round(t-GAP+0.6,3)
json.dump({'scenes':out,'total':total},open('timeline.json','w'),ensure_ascii=False,indent=1)
print('total',total,[ (o['id'],round(o['end']-o['start'],2)) for o in out])
