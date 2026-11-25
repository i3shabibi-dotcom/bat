#!/usr/bin/env bash
# Requires vo/01_hook.mp3 ... vo/08_cta.mp3 (ElevenLabs voice "Abdulaziz AL-Shabibi")
set -euo pipefail
cd "$(dirname "$0")"
python3 build_timeline.py
python3 sfx.py
node render.js video
python3 - <<'PY'
import json,subprocess
tl=json.load(open('timeline.json'))
ins=[];f=[]
for i,s in enumerate(tl['scenes']):
    ins+=['-i',s['file']]; f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,adelay={int(s['start']*1000)}[v{i}]")
n=len(tl['scenes'])
f.append(''.join(f'[v{i}]' for i in range(n))+f"amix=inputs={n}:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=9[vo]")
f.append(f"[{n}:a]volume=0.55[fx]")
f.append("[vo][fx]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]")
subprocess.check_call(['ffmpeg','-y','-v','error',*ins,'-i','out/sfx.wav','-i','out/video_silent.mp4','-filter_complex',';'.join(f),
  '-map',f'{n+1}:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-t',str(tl['total']),'out/iPhone20_final.mp4'])
print('final ok, total',tl['total'])
PY
ffprobe -v error -show_entries stream=width,height:format=duration -of compact out/iPhone20_final.mp4
